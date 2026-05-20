"""RobustScaler with fit/apply separation and persistence."""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from hydra.config import ARTIFACTS


class RobustScaler:
    """Percentile-based scaler (5th-95th by default)."""

    def __init__(self, q_low: float = 5.0, q_high: float = 95.0):
        self.q_low = q_low
        self.q_high = q_high
        self.center_: np.ndarray | None = None
        self.scale_: np.ndarray | None = None

    def fit(self, X: np.ndarray) -> "RobustScaler":
        low = np.nanpercentile(X, self.q_low, axis=0)
        high = np.nanpercentile(X, self.q_high, axis=0)
        self.center_ = np.nanmedian(X, axis=0)
        self.scale_ = high - low
        self.scale_[self.scale_ < 1e-10] = 1.0
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.center_) / self.scale_

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        self.fit(X)
        return self.transform(X)

    def save(self, fold: int) -> Path:
        path = ARTIFACTS / f"scaler_fold{fold}.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        return path

    @classmethod
    def load(cls, fold: int) -> "RobustScaler":
        path = ARTIFACTS / f"scaler_fold{fold}.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)
