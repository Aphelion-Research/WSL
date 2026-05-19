"""Readout layer for ESN."""
import numpy as np
from typing import Tuple, Optional
from sklearn.linear_model import RidgeCV
from sklearn.metrics import r2_score, mean_squared_error

from reservoir.config import RIDGE_ALPHAS, TRAIN_SPLIT


class RidgeReadout:
    """Ridge regression readout layer."""

    def __init__(self, alphas: list = None):
        """Initialize readout.

        Args:
            alphas: Regularization parameters for cross-validation
        """
        if alphas is None:
            alphas = RIDGE_ALPHAS

        self.ridge = RidgeCV(alphas=alphas, cv=5)
        self.is_fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray) -> 'RidgeReadout':
        """Fit readout layer.

        Args:
            X: Reservoir states (n_samples, n_reservoir)
            y: Target values (n_samples,)

        Returns:
            self
        """
        self.ridge.fit(X, y)
        self.is_fitted = True

        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict using fitted readout.

        Args:
            X: Reservoir states (n_samples, n_reservoir)

        Returns:
            Predictions (n_samples,)
        """
        if not self.is_fitted:
            raise RuntimeError("Readout not fitted")

        return self.ridge.predict(X)

    def get_best_alpha(self) -> float:
        """Get best regularization parameter from CV."""
        if not self.is_fitted:
            return None

        return self.ridge.alpha_


def train_test_split_esn(
    states: np.ndarray,
    targets: np.ndarray,
    train_split: float = TRAIN_SPLIT
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split states and targets into train/test.

    Args:
        states: Reservoir states (n_samples, n_reservoir)
        targets: Target values (n_samples,)
        train_split: Fraction for training

    Returns:
        (X_train, X_test, y_train, y_test)
    """
    n = len(states)
    n_train = int(n * train_split)

    X_train = states[:n_train]
    X_test = states[n_train:]

    y_train = targets[:n_train]
    y_test = targets[n_train:]

    return X_train, X_test, y_train, y_test


def evaluate_readout(
    readout: RidgeReadout,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> dict:
    """Evaluate readout performance.

    Args:
        readout: Fitted readout
        X_test: Test states
        y_test: Test targets

    Returns:
        Dict with metrics
    """
    y_pred = readout.predict(X_test)

    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    # Directional accuracy
    correct_direction = np.sum(np.sign(y_pred) == np.sign(y_test))
    directional_accuracy = correct_direction / len(y_test)

    return {
        "r2": r2,
        "rmse": rmse,
        "directional_accuracy": directional_accuracy,
        "best_alpha": readout.get_best_alpha()
    }
