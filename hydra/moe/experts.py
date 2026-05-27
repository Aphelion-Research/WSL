"""LightGBM expert classifiers for HYDRA-MoE."""

import pickle
from pathlib import Path

import numpy as np
import lightgbm as lgb
from loguru import logger


EXPERT_PARAMS = {
    "trend_up": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 127,
        "learning_rate": 0.02,
        "feature_fraction": 0.5,
        "bagging_fraction": 0.7,
        "bagging_freq": 5,
        "lambda_l1": 0.3,
        "lambda_l2": 2.0,
        "min_data_in_leaf": 150,
        "verbose": -1,
        "n_jobs": -1,
    },
    "trend_down": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 127,
        "learning_rate": 0.02,
        "feature_fraction": 0.5,
        "bagging_fraction": 0.7,
        "bagging_freq": 5,
        "lambda_l1": 0.5,
        "lambda_l2": 2.0,
        "min_data_in_leaf": 150,
        "verbose": -1,
        "n_jobs": -1,
    },
    "mean_revert": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 63,
        "learning_rate": 0.03,
        "feature_fraction": 0.6,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "lambda_l1": 0.1,
        "lambda_l2": 1.0,
        "min_data_in_leaf": 100,
        "verbose": -1,
        "n_jobs": -1,
    },
    "crisis_vol": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "num_leaves": 63,
        "learning_rate": 0.03,
        "feature_fraction": 0.5,
        "bagging_fraction": 0.7,
        "bagging_freq": 5,
        "lambda_l1": 1.0,
        "lambda_l2": 3.0,
        "min_data_in_leaf": 200,
        "verbose": -1,
        "n_jobs": -1,
    },
}


class HydraExpert:
    """Single LightGBM expert supporting sample-weighted training for joint optimization."""

    def __init__(
        self,
        expert_id: int,
        expert_name: str,
        lgb_params: dict,
        n_estimators: int = 2000,
        early_stopping_rounds: int = 100,
        feature_cols: list[str] = None,
    ):
        self.expert_id = expert_id
        self.expert_name = expert_name
        self.lgb_params = lgb_params.copy()
        self.n_estimators = n_estimators
        self.early_stopping_rounds = early_stopping_rounds
        self.feature_cols = feature_cols
        self.model = None
        self.best_iteration = None

    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: np.ndarray,
        y_val: np.ndarray,
        sample_weights: np.ndarray = None,
        val_weights: np.ndarray = None,
    ) -> dict:
        """Train LightGBM with optional sample weighting.

        Args:
            X_train: Training features (n_train, n_features).
            y_train: Training labels (n_train,).
            X_val: Validation features.
            y_val: Validation labels.
            sample_weights: Router weights for this expert (n_train,).
            val_weights: Router weights for val set.

        Returns:
            Dict with best_iteration and val_auc.
        """
        # Check class balance and set scale_pos_weight if needed
        params = self.lgb_params.copy()
        if sample_weights is not None:
            n_pos = (y_train * sample_weights).sum()
            n_neg = ((1 - y_train) * sample_weights).sum()
        else:
            n_pos = y_train.sum()
            n_neg = len(y_train) - n_pos

        if n_pos > 0 and n_neg > 0:
            ratio = n_neg / n_pos
            if ratio > 1.5 or ratio < 0.667:
                params["scale_pos_weight"] = ratio

        train_data = lgb.Dataset(
            X_train, label=y_train, weight=sample_weights, free_raw_data=False
        )
        val_data = lgb.Dataset(
            X_val, label=y_val, weight=val_weights, reference=train_data, free_raw_data=False
        )

        callbacks = [
            lgb.early_stopping(self.early_stopping_rounds, verbose=False),
            lgb.log_evaluation(period=0),
        ]

        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=self.n_estimators,
            valid_sets=[val_data],
            valid_names=["val"],
            callbacks=callbacks,
        )

        self.best_iteration = self.model.best_iteration

        val_pred = self.model.predict(X_val, num_iteration=self.best_iteration)
        from sklearn.metrics import roc_auc_score
        try:
            val_auc = roc_auc_score(y_val, val_pred)
        except ValueError:
            val_auc = 0.5

        logger.info(
            f"  Expert {self.expert_id} ({self.expert_name}): "
            f"best_iter={self.best_iteration}, val_auc={val_auc:.4f}"
        )

        return {"best_iteration": self.best_iteration, "val_auc": val_auc}

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(long) for each sample. Shape: (n,)."""
        if self.model is None:
            return np.full(len(X), 0.5, dtype=np.float32)
        pred = self.model.predict(X, num_iteration=self.best_iteration)
        return pred.astype(np.float32)

    def get_feature_importance(self, importance_type: str = "gain") -> dict:
        """Return top-50 feature importances as {feature_name: importance}."""
        if self.model is None:
            return {}
        importance = self.model.feature_importance(importance_type=importance_type)
        if self.feature_cols is not None:
            names = self.feature_cols
        else:
            names = [f"f{i}" for i in range(len(importance))]
        pairs = sorted(zip(names, importance), key=lambda x: -x[1])[:50]
        return {k: float(v) for k, v in pairs}

    def save(self, path: str) -> None:
        """Serialize expert to pickle."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump({
                "expert_id": self.expert_id,
                "expert_name": self.expert_name,
                "lgb_params": self.lgb_params,
                "n_estimators": self.n_estimators,
                "early_stopping_rounds": self.early_stopping_rounds,
                "feature_cols": self.feature_cols,
                "model_str": self.model.model_to_string() if self.model else None,
                "best_iteration": self.best_iteration,
            }, f)

    def load(self, path: str) -> None:
        """Load expert from pickle."""
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.expert_id = data["expert_id"]
        self.expert_name = data["expert_name"]
        self.lgb_params = data["lgb_params"]
        self.n_estimators = data["n_estimators"]
        self.early_stopping_rounds = data["early_stopping_rounds"]
        self.feature_cols = data["feature_cols"]
        self.best_iteration = data["best_iteration"]
        if data["model_str"]:
            self.model = lgb.Booster(model_str=data["model_str"])
        else:
            self.model = None


class ExpertFactory:
    """Factory for creating all 4 HYDRA-MoE experts with correct hyperparameters."""

    @staticmethod
    def create_all(
        feature_cols: list[str],
        n_estimators: int = 2000,
        early_stopping_rounds: int = 100,
    ) -> list[HydraExpert]:
        """Create all 4 experts with architecture-specified hyperparameters.

        Args:
            feature_cols: Feature column names for importance reporting.
            n_estimators: Max boosting rounds.
            early_stopping_rounds: Early stopping patience.

        Returns:
            List of 4 HydraExpert instances.
        """
        from hydra.moe.feature_groups import EXPERT_NAMES

        experts = []
        for i, name in enumerate(EXPERT_NAMES):
            expert = HydraExpert(
                expert_id=i,
                expert_name=name,
                lgb_params=EXPERT_PARAMS[name],
                n_estimators=n_estimators,
                early_stopping_rounds=early_stopping_rounds,
                feature_cols=feature_cols,
            )
            experts.append(expert)
        return experts
