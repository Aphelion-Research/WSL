"""Joint training loop for HYDRA-MoE: 3-phase alternating optimization."""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from loguru import logger

from hydra.moe.moe_model import HydraMoE
from hydra.moe.router import RouterTrainer
from hydra.moe.regime_labels import assign_initial_regimes, get_soft_regime_weights


@dataclass
class MoEConfig:
    """All hyperparameters for HYDRA-MoE training."""

    # Router
    n_experts: int = 4
    router_hidden: list = field(default_factory=lambda: [128, 64])
    router_dropout: float = 0.2
    router_lr: float = 1e-3
    router_weight_decay: float = 1e-4
    router_temperature_start: float = 1.0
    router_temperature_end: float = 0.5
    lambda_entropy: float = 0.01

    # Training phases
    n_alternating_rounds: int = 5
    router_steps_per_round: int = 500
    router_batch_size: int = 4096

    # Expert common
    n_estimators: int = 2000
    early_stopping_rounds: int = 100

    # Data
    train_frac: float = 0.60
    val_frac: float = 0.20

    # Confidence gate
    gate_upper: float = 0.60
    gate_lower: float = 0.40

    # Random state
    random_state: int = 42


@dataclass
class TrainingResults:
    """Training outcome container."""

    phase0_metrics: dict = field(default_factory=dict)
    phase1_metrics: list = field(default_factory=list)
    final_val_auc: float = 0.0
    final_oos_auc: float = 0.0
    training_time_seconds: float = 0.0


class MoETrainer:
    """Joint training manager for HYDRA-MoE system."""

    def __init__(
        self,
        moe: HydraMoE,
        config: MoEConfig,
        output_dir: str = "output_hydra_moe",
    ):
        self.moe = moe
        self.config = config
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = moe.device

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        X_oos: np.ndarray,
        y_oos: np.ndarray,
    ) -> TrainingResults:
        """Full 3-phase joint training.

        Args:
            X_train: Training features.
            y_train: Training labels.
            X_val: Validation features.
            y_val: Validation labels.
            X_oos: Out-of-sample features.
            y_oos: Out-of-sample labels.

        Returns:
            TrainingResults with all metrics.
        """
        import time
        start = time.time()
        results = TrainingResults()

        try:
            import mlflow
            mlflow.set_tracking_uri(str(self.output_dir / "mlruns"))
            mlflow.set_experiment("hydra_moe")
            mlflow.start_run()
            mlflow.log_params({
                "n_experts": self.config.n_experts,
                "router_lr": self.config.router_lr,
                "n_alternating_rounds": self.config.n_alternating_rounds,
                "n_train": len(X_train),
                "n_val": len(X_val),
                "n_oos": len(X_oos),
            })
            use_mlflow = True
        except Exception:
            use_mlflow = False

        # Phase 0: Initialization
        logger.info("═══ PHASE 0: INITIALIZATION ═══")
        results.phase0_metrics = self._phase0_init(X_train, y_train, X_val, y_val)

        if use_mlflow:
            mlflow.log_metrics({f"phase0_{k}": v for k, v in results.phase0_metrics.items() if isinstance(v, (int, float))})

        # Phase 1: Alternating Optimization
        logger.info("═══ PHASE 1: ALTERNATING OPTIMIZATION ═══")
        results.phase1_metrics = self._phase1_alternating(X_train, y_train, X_val, y_val)

        for i, rm in enumerate(results.phase1_metrics):
            if use_mlflow:
                mlflow.log_metrics({f"round{i}_{k}": v for k, v in rm.items() if isinstance(v, (int, float))}, step=i)

        # Phase 2: Convergence check (additional rounds if needed)
        logger.info("═══ PHASE 2: CONVERGENCE FINE-TUNING ═══")
        if len(results.phase1_metrics) >= 2:
            last_auc = results.phase1_metrics[-1].get("val_auc", 0)
            prev_auc = results.phase1_metrics[-2].get("val_auc", 0)
            if abs(last_auc - prev_auc) > 0.0005:
                logger.info("  Running 3 additional convergence rounds...")
                extra = self._phase1_alternating(X_train, y_train, X_val, y_val, n_rounds=3)
                results.phase1_metrics.extend(extra)

        # Calibration
        logger.info("═══ CALIBRATION ═══")
        self._calibrate(X_val, y_val)

        # Final evaluation
        val_metrics = self._evaluate_checkpoint(X_val, y_val, "final_val")
        oos_metrics = self._evaluate_checkpoint(X_oos, y_oos, "final_oos")
        results.final_val_auc = val_metrics["auc"]
        results.final_oos_auc = oos_metrics["auc"]

        if use_mlflow:
            mlflow.log_metrics({"final_val_auc": results.final_val_auc, "final_oos_auc": results.final_oos_auc})
            mlflow.end_run()

        results.training_time_seconds = time.time() - start
        logger.info(f"Training complete in {results.training_time_seconds:.1f}s")
        logger.info(f"  Val AUC: {results.final_val_auc:.4f}")
        logger.info(f"  OOS AUC: {results.final_oos_auc:.4f}")

        return results

    def _phase0_init(self, X_train, y_train, X_val, y_val) -> dict:
        """K-Means initialization + independent expert pre-training."""
        # Fit scaler on train router features
        self.moe.fit_scaler(X_train)

        # Assign initial regimes via clustering
        logger.info("  Clustering for initial regime assignment...")
        regime_labels = assign_initial_regimes(
            X_train, self.moe.router_indices,
            n_regimes=self.config.n_experts,
            random_state=self.config.random_state,
        )

        # Check for degenerate clusters
        unique, counts = np.unique(regime_labels, return_counts=True)
        min_frac = counts.min() / len(regime_labels)
        if min_frac < 0.05:
            logger.warning(f"  Degenerate cluster detected (min fraction: {min_frac:.3f})")

        # Train each expert on its assigned regime bars (hard assignment)
        logger.info("  Pre-training experts on assigned regime bars...")
        X_train_clean = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_val_clean = np.nan_to_num(X_val, nan=0.0, posinf=0.0, neginf=0.0)

        expert_aucs = []
        for k, expert in enumerate(self.moe.experts):
            mask = regime_labels == k
            n_bars = mask.sum()
            logger.info(f"  Expert {k} ({expert.expert_name}): {n_bars:,} bars")

            if n_bars < 1000:
                logger.warning(f"  Expert {k} has too few bars ({n_bars}), using full dataset")
                mask = np.ones(len(X_train), dtype=bool)

            metrics = expert.train(
                X_train_clean[mask], y_train[mask],
                X_val_clean, y_val,
            )
            expert_aucs.append(metrics["val_auc"])

        # Initialize router to match clustering soft weights
        logger.info("  Initializing router from cluster assignments...")
        soft_weights = get_soft_regime_weights(
            X_train, self.moe.router_indices,
            n_regimes=self.config.n_experts,
            random_state=self.config.random_state,
        )
        self._warm_start_router(X_train, soft_weights)

        val_auc = self._evaluate_checkpoint(X_val, y_val, "phase0")["auc"]
        return {"expert_aucs": expert_aucs, "val_auc": val_auc, "min_cluster_frac": float(min_frac)}

    def _phase1_alternating(self, X_train, y_train, X_val, y_val, n_rounds=None) -> list:
        """Alternating router/expert optimization."""
        if n_rounds is None:
            n_rounds = self.config.n_alternating_rounds

        X_train_clean = np.nan_to_num(X_train, nan=0.0, posinf=0.0, neginf=0.0)
        X_val_clean = np.nan_to_num(X_val, nan=0.0, posinf=0.0, neginf=0.0)

        round_metrics = []
        prev_val_auc = 0.0

        for rnd in range(n_rounds):
            logger.info(f"  Round {rnd + 1}/{n_rounds}")

            # Anneal temperature linearly
            t_start = self.config.router_temperature_start
            t_end = self.config.router_temperature_end
            progress = rnd / max(n_rounds - 1, 1)
            new_temp = t_start + (t_end - t_start) * progress
            self.moe.router.temperature = new_temp

            # Step A: Fix experts → optimize router
            logger.info(f"    Step A: Optimizing router (temp={new_temp:.3f})...")
            expert_probas_train = self.moe.get_expert_predictions(X_train_clean)
            router_losses = self._train_router_epoch(X_train, expert_probas_train, y_train)

            # Step B: Fix router → retrain experts
            logger.info("    Step B: Retraining experts with routing weights...")
            routing_weights_train = self.moe.get_routing_weights(X_train)
            routing_weights_val = self.moe.get_routing_weights(X_val)

            # Check for expert collapse
            mean_weights = routing_weights_train.mean(axis=0)
            max_weight = mean_weights.max()
            if max_weight > 0.90:
                logger.warning(f"    COLLAPSE DETECTED: Expert {mean_weights.argmax()} gets {max_weight:.2f}")
                self.config.lambda_entropy *= 2
                logger.warning(f"    Doubling lambda_entropy → {self.config.lambda_entropy}")
                # Reset router to init
                soft_weights = get_soft_regime_weights(
                    X_train, self.moe.router_indices,
                    n_regimes=self.config.n_experts,
                    random_state=self.config.random_state + rnd,
                )
                self._warm_start_router(X_train, soft_weights)
                routing_weights_train = self.moe.get_routing_weights(X_train)
                routing_weights_val = self.moe.get_routing_weights(X_val)

            for k, expert in enumerate(self.moe.experts):
                w_train = routing_weights_train[:, k].astype(np.float32)
                w_val = routing_weights_val[:, k].astype(np.float32)
                # Ensure minimum weight to prevent zero-weight training
                w_train = np.maximum(w_train, 0.01)
                w_val = np.maximum(w_val, 0.01)
                expert.train(X_train_clean, y_train, X_val_clean, y_val, w_train, w_val)

            # Evaluate
            metrics = self._evaluate_checkpoint(X_val, y_val, f"round_{rnd}")
            metrics["router_loss_mean"] = float(np.mean(router_losses))
            metrics["routing_distribution"] = mean_weights.tolist()
            metrics["temperature"] = new_temp
            round_metrics.append(metrics)

            logger.info(f"    Val AUC: {metrics['auc']:.4f} | Routing: {[f'{w:.2f}' for w in mean_weights]}")

            # Convergence check
            if abs(metrics["auc"] - prev_val_auc) < 0.0002 and rnd >= 2:
                logger.info("    Converged (AUC delta < 0.0002)")
                break
            prev_val_auc = metrics["auc"]

        return round_metrics

    def _train_router_epoch(self, X_train, expert_probas, y_train) -> list:
        """Train router for N gradient steps on mini-batches."""
        router_trainer = RouterTrainer(
            self.moe.router,
            lr=self.config.router_lr,
            weight_decay=self.config.router_weight_decay,
            lambda_entropy=self.config.lambda_entropy,
            device=self.device,
        )

        x_router_all = self.moe.get_router_input(X_train)
        y_tensor = torch.tensor(y_train, dtype=torch.float32, device=self.device)

        n = len(X_train)
        batch_size = self.config.router_batch_size
        losses = []

        for step in range(self.config.router_steps_per_round):
            idx = np.random.randint(0, n, size=batch_size)
            x_batch = x_router_all[idx]
            y_batch = y_tensor[idx]
            ep_batch = expert_probas[idx]

            loss_dict = router_trainer.step(x_batch, ep_batch, y_batch)
            losses.append(loss_dict["total_loss"])

            if step > 0 and step % 100 == 0:
                router_trainer.step_scheduler()

        return losses

    def _warm_start_router(self, X_train, target_weights):
        """Train router to match target soft routing weights (from clustering)."""
        x_router = self.moe.get_router_input(X_train)
        target = torch.tensor(target_weights, dtype=torch.float32, device=self.device)

        optimizer = torch.optim.Adam(self.moe.router.parameters(), lr=5e-3)
        batch_size = 4096
        n = len(X_train)

        self.moe.router.train()
        for _ in range(200):
            idx = np.random.randint(0, n, size=batch_size)
            pred = self.moe.router(x_router[idx])
            loss = torch.nn.functional.mse_loss(pred, target[idx])
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    def _calibrate(self, X_val, y_val) -> None:
        """Fit isotonic calibration on val set predictions."""
        result = self.moe.predict(X_val, calibrated=False)
        raw_proba = result["proba"]
        self.moe.calibrator.fit(raw_proba, y_val)

    def _evaluate_checkpoint(self, X, y, phase: str) -> dict:
        """Evaluate AUC and accuracy on given set."""
        result = self.moe.predict(X, calibrated=(phase.startswith("final")))
        proba = result["proba"]

        try:
            auc = roc_auc_score(y, proba)
        except ValueError:
            auc = 0.5

        acc = ((proba >= 0.5).astype(int) == y).mean()
        recall = y[proba >= 0.5].sum() / max(y.sum(), 1) if y.sum() > 0 else 0

        return {"auc": float(auc), "accuracy": float(acc), "recall": float(recall), "phase": phase}
