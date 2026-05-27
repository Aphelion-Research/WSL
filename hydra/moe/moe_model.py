"""Full HYDRA-MoE system: router + experts + calibrator."""

import pickle
from pathlib import Path

import numpy as np
import torch
from sklearn.preprocessing import StandardScaler
from loguru import logger

from hydra.moe.router import HydraRouter
from hydra.moe.experts import HydraExpert, ExpertFactory
from hydra.moe.calibration import ProbabilityCalibrator
from hydra.moe.feature_groups import get_router_feature_indices, EXPERT_NAMES


class HydraMoE:
    """Full jointly-trained Mixture-of-Experts model for XAU/USD directional prediction.

    Components:
        - router: HydraRouter (PyTorch MLP)
        - experts: list[HydraExpert] (K LightGBM classifiers)
        - calibrator: ProbabilityCalibrator (isotonic regression)
        - feature_cols: column names for X input
        - router_indices: indices into X for router features
        - scaler: StandardScaler fitted on router features from train set
    """

    def __init__(
        self,
        n_experts: int = 4,
        router_hidden: list[int] = None,
        router_dropout: float = 0.2,
        router_temperature: float = 1.0,
        n_estimators: int = 2000,
        early_stopping_rounds: int = 100,
        gate_upper: float = 0.60,
        gate_lower: float = 0.40,
        device: str = None,
    ):
        if router_hidden is None:
            router_hidden = [128, 64]
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.n_experts = n_experts
        self.router_hidden = router_hidden
        self.router_dropout = router_dropout
        self.router_temperature = router_temperature
        self.gate_upper = gate_upper
        self.gate_lower = gate_lower
        self.device = device

        self.router: HydraRouter = None
        self.experts: list[HydraExpert] = None
        self.calibrator = ProbabilityCalibrator(method="isotonic")
        self.feature_cols: list[str] = None
        self.router_indices: np.ndarray = None
        self.scaler: StandardScaler = None
        self.n_estimators = n_estimators
        self.early_stopping_rounds = early_stopping_rounds

    def initialize(self, feature_cols: list[str]) -> None:
        """Initialize all components given feature column names.

        Args:
            feature_cols: List of feature column names matching X columns.
        """
        self.feature_cols = feature_cols
        self.router_indices = get_router_feature_indices(feature_cols)
        n_router_features = len(self.router_indices)

        logger.info(f"Router: {n_router_features} features, hidden={self.router_hidden}")
        logger.info(f"Experts: {self.n_experts} LightGBM classifiers")

        self.router = HydraRouter(
            input_dim=n_router_features,
            n_experts=self.n_experts,
            hidden_dims=self.router_hidden,
            dropout=self.router_dropout,
            temperature=self.router_temperature,
        ).to(self.device)

        self.experts = ExpertFactory.create_all(
            feature_cols=feature_cols,
            n_estimators=self.n_estimators,
            early_stopping_rounds=self.early_stopping_rounds,
        )

        self.scaler = StandardScaler()

    def fit_scaler(self, X_train: np.ndarray) -> None:
        """Fit router feature scaler on training data only.

        Args:
            X_train: Training feature matrix.
        """
        X_router = X_train[:, self.router_indices]
        X_router = np.nan_to_num(X_router, nan=0.0, posinf=0.0, neginf=0.0)
        self.scaler.fit(X_router)

    def get_router_input(self, X: np.ndarray) -> torch.Tensor:
        """Extract, scale, and tensorize router features.

        Args:
            X: Full feature matrix (n, d).

        Returns:
            Torch tensor (n, n_router_features) on device.
        """
        X_router = X[:, self.router_indices].copy()
        X_router = np.nan_to_num(X_router, nan=0.0, posinf=0.0, neginf=0.0)
        X_scaled = self.scaler.transform(X_router)
        X_scaled = np.nan_to_num(X_scaled, nan=0.0, posinf=0.0, neginf=0.0)
        return torch.tensor(X_scaled, dtype=torch.float32, device=self.device)

    def get_routing_weights(self, X: np.ndarray) -> np.ndarray:
        """Get soft routing weights for all bars.

        Args:
            X: Full feature matrix.

        Returns:
            Routing weights (n, K) numpy array.
        """
        self.router.eval()
        x_router = self.get_router_input(X)
        with torch.no_grad():
            weights = self.router(x_router).cpu().numpy()
        return weights

    def get_expert_predictions(self, X: np.ndarray) -> np.ndarray:
        """Get predictions from all experts.

        Args:
            X: Full feature matrix.

        Returns:
            Expert probabilities (n, K) numpy array.
        """
        X_clean = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
        expert_probas = np.zeros((len(X), self.n_experts), dtype=np.float32)
        for k, expert in enumerate(self.experts):
            expert_probas[:, k] = expert.predict_proba(X_clean)
        return expert_probas

    def predict(
        self,
        X: np.ndarray,
        return_routing_weights: bool = False,
        return_expert_probas: bool = False,
        calibrated: bool = True,
    ) -> dict:
        """Full inference pipeline.

        Args:
            X: Feature matrix (n, d).
            return_routing_weights: Include per-bar routing weights in output.
            return_expert_probas: Include per-expert probabilities in output.
            calibrated: Apply isotonic calibration.

        Returns:
            Dict with proba, direction, trade_signal, and optional routing info.
        """
        routing_weights = self.get_routing_weights(X)
        expert_probas = self.get_expert_predictions(X)

        # Weighted sum
        proba = (routing_weights * expert_probas).sum(axis=1)
        proba = np.clip(proba, 0.0, 1.0).astype(np.float32)

        if calibrated and self.calibrator.calibrator is not None:
            proba = self.calibrator.transform(proba)

        direction = (proba >= 0.5).astype(np.int32)
        trade_signal = ((proba > self.gate_upper) | (proba < self.gate_lower)).astype(np.int32)
        dominant_expert = routing_weights.argmax(axis=1)

        result = {
            "proba": proba,
            "direction": direction,
            "trade_signal": trade_signal,
            "dominant_expert": dominant_expert,
        }

        if return_routing_weights:
            result["routing_weights"] = routing_weights
        if return_expert_probas:
            result["expert_probas"] = expert_probas

        return result

    def save(self, output_dir: str) -> None:
        """Save all components to output directory."""
        out = Path(output_dir) / "models"
        out.mkdir(parents=True, exist_ok=True)

        # Router
        torch.save(self.router.state_dict(), out / "router.pt")

        # Experts
        for k, expert in enumerate(self.experts):
            expert.save(str(out / f"expert_{k}.pkl"))

        # Calibrator
        self.calibrator.save(str(out / "calibrator.pkl"))

        # Metadata
        meta = {
            "n_experts": self.n_experts,
            "router_hidden": self.router_hidden,
            "router_dropout": self.router_dropout,
            "router_temperature": self.router_temperature,
            "gate_upper": self.gate_upper,
            "gate_lower": self.gate_lower,
            "feature_cols": self.feature_cols,
            "router_indices": self.router_indices.tolist(),
            "scaler_mean": self.scaler.mean_.tolist(),
            "scaler_scale": self.scaler.scale_.tolist(),
        }
        with open(out / "moe_meta.pkl", "wb") as f:
            pickle.dump(meta, f)

        logger.info(f"Model saved to {out}")

    @classmethod
    def load(cls, output_dir: str) -> "HydraMoE":
        """Load full system from saved artifacts.

        Args:
            output_dir: Path to output_hydra_moe directory.

        Returns:
            Loaded HydraMoE instance.
        """
        out = Path(output_dir) / "models"

        with open(out / "moe_meta.pkl", "rb") as f:
            meta = pickle.load(f)

        moe = cls(
            n_experts=meta["n_experts"],
            router_hidden=meta["router_hidden"],
            router_dropout=meta["router_dropout"],
            router_temperature=meta["router_temperature"],
            gate_upper=meta["gate_upper"],
            gate_lower=meta["gate_lower"],
        )

        moe.feature_cols = meta["feature_cols"]
        moe.router_indices = np.array(meta["router_indices"], dtype=np.int64)

        # Scaler
        moe.scaler = StandardScaler()
        moe.scaler.mean_ = np.array(meta["scaler_mean"])
        moe.scaler.scale_ = np.array(meta["scaler_scale"])
        moe.scaler.var_ = moe.scaler.scale_ ** 2
        moe.scaler.n_features_in_ = len(moe.scaler.mean_)

        # Router
        n_router = len(moe.router_indices)
        moe.router = HydraRouter(
            input_dim=n_router,
            n_experts=moe.n_experts,
            hidden_dims=moe.router_hidden,
            dropout=moe.router_dropout,
            temperature=moe.router_temperature,
        ).to(moe.device)
        moe.router.load_state_dict(torch.load(out / "router.pt", map_location=moe.device, weights_only=True))
        moe.router.eval()

        # Experts
        moe.experts = []
        for k in range(moe.n_experts):
            expert = HydraExpert(expert_id=k, expert_name="", lgb_params={})
            expert.load(str(out / f"expert_{k}.pkl"))
            moe.experts.append(expert)

        # Calibrator
        moe.calibrator = ProbabilityCalibrator()
        moe.calibrator.load(str(out / "calibrator.pkl"))

        return moe
