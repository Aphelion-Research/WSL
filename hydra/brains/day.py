"""Day brain — H1/H4 timeframe specialisation."""
from __future__ import annotations

from typing import Optional

import numpy as np

from hydra.models.base import ModelWrapper
from hydra.models.gbm import LGBMModel, XGBModel, CatBoostModel
from hydra.models.forests import RFModel, ETModel, HGBModel
from hydra.models.linear import LRModel, GNBModel, LDAModel
from hydra.models.neural import MLPModel, LSTMModel, TCNModel
from hydra.models.stacking import StackingEnsemble
from hydra.signals.ensemble import bma_weights, bma_predict, threshold_signal


class DayBrain:
    """H1/H4 medium-timeframe brain."""

    timeframes = ("h1", "h4")
    name = "day"

    def __init__(self):
        self.base_models = self._init_models()
        self.stack: Optional[StackingEnsemble] = None
        self.bma_w: Optional[np.ndarray] = None

    def _init_models(self) -> list[ModelWrapper]:
        return [
            LGBMModel(), XGBModel(), CatBoostModel(),
            RFModel(), ETModel(), HGBModel(),
            LRModel(), GNBModel(), LDAModel(),
            MLPModel(), LSTMModel(), TCNModel(),
        ]

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
    ) -> "DayBrain":
        self.stack = StackingEnsemble(self.base_models)
        self.stack.fit(X, y, sample_weight=sample_weight)
        return self

    def set_bma_weights(self, val_sharpes: np.ndarray):
        self.bma_w = bma_weights(val_sharpes)

    def predict(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if self.stack is None:
            return np.zeros(len(X), dtype=np.int8), np.zeros(len(X))
        proba = self.stack.predict_proba(X)
        return threshold_signal(proba)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if self.stack is None:
            return np.full(len(X), 0.5)
        return self.stack.predict_proba(X)
