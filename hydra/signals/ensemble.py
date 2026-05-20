"""Bayesian Model Averaging + threshold-based signal generation."""
from __future__ import annotations

import numpy as np

from hydra.config import ENSEMBLE


def bma_weights(val_sharpes: np.ndarray, temperature: float = ENSEMBLE.bma_temp) -> np.ndarray:
    """Compute BMA weights from validation Sharpe ratios via softmax."""
    s = np.array(val_sharpes, dtype=np.float64)
    s = np.clip(s, -10, 10)
    exp_s = np.exp(s / temperature)
    return exp_s / exp_s.sum()


def bma_predict(
    model_probs: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    """Weighted average of model probabilities.

    Args:
        model_probs: (n_samples, n_models) probability matrix
        weights: (n_models,) BMA weights
    """
    return model_probs @ weights


def threshold_signal(
    proba: np.ndarray,
    long_thresh: float = ENSEMBLE.long_threshold,
    short_thresh: float = ENSEMBLE.short_threshold,
) -> tuple[np.ndarray, np.ndarray]:
    """Convert P(long) to signal and confidence.

    Returns:
        (signals, confidences) where signal in {-1, 0, 1}
    """
    signals = np.zeros(len(proba), dtype=np.int8)
    confidences = np.zeros(len(proba), dtype=np.float64)

    long_mask = proba > long_thresh
    short_mask = proba < short_thresh

    signals[long_mask] = 1
    signals[short_mask] = -1

    confidences[long_mask] = proba[long_mask]
    confidences[short_mask] = 1.0 - proba[short_mask]

    return signals, confidences
