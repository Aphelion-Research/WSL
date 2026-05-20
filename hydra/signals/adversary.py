"""HYDRA-ADVERSARY: predicts whether next trade will lose."""
from __future__ import annotations

from typing import Optional

import numpy as np


class HydraAdversary:
    """LightGBM classifier trained on past trade outcomes to veto bad entries."""

    def __init__(self, veto_threshold: float = 0.65):
        self.veto_threshold = veto_threshold
        self.model = None

    def fit(
        self,
        confidence: np.ndarray,
        regime: np.ndarray,
        realised_vol: np.ndarray,
        slippage: np.ndarray,
        hour: np.ndarray,
        outcomes: np.ndarray,
    ) -> "HydraAdversary":
        """Train on historical trade features. outcomes: 1=loss, 0=win."""
        X = np.column_stack([confidence, regime, realised_vol, slippage, hour])
        valid = np.isfinite(X).all(axis=1) & np.isfinite(outcomes)

        if valid.sum() < 50:
            return self

        try:
            import lightgbm as lgb
            self.model = lgb.LGBMClassifier(
                n_estimators=200, learning_rate=0.05, num_leaves=31,
                max_depth=5, verbose=-1, random_state=42,
            )
            self.model.fit(X[valid], outcomes[valid])
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier
            self.model = GradientBoostingClassifier(
                n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42)
            self.model.fit(X[valid], outcomes[valid])

        return self

    def should_veto(
        self,
        confidence: float,
        regime: float,
        realised_vol: float,
        slippage: float,
        hour: float,
    ) -> bool:
        """Returns True if trade should be vetoed."""
        if self.model is None:
            return False
        X = np.array([[confidence, regime, realised_vol, slippage, hour]])
        proba = self.model.predict_proba(X)
        p_loss = proba[0, 1] if proba.ndim == 2 else proba[0]
        return p_loss > self.veto_threshold

    def veto_mask(
        self,
        confidence: np.ndarray,
        regime: np.ndarray,
        realised_vol: np.ndarray,
        slippage: np.ndarray,
        hour: np.ndarray,
    ) -> np.ndarray:
        """Returns boolean mask: True = allow trade, False = veto."""
        if self.model is None:
            return np.ones(len(confidence), dtype=bool)

        X = np.column_stack([confidence, regime, realised_vol, slippage, hour])
        proba = self.model.predict_proba(X)
        p_loss = proba[:, 1] if proba.ndim == 2 else proba
        return p_loss <= self.veto_threshold
