"""Model wrapper protocol and warm-start API."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import numpy as np


class ModelWrapper(ABC):
    """Protocol for all HYDRA base learners."""

    name: str = "base"

    @abstractmethod
    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> "ModelWrapper":
        ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(y=1) for each sample."""
        ...

    def warm_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
    ) -> "ModelWrapper":
        """Incremental update. Default: full refit."""
        return self.fit(X, y, sample_weight, X_val, y_val)

    def feature_importance(self) -> Optional[np.ndarray]:
        return None
