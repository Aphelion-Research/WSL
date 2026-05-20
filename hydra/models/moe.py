"""Mixture-of-Experts regime gate."""
from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.linear_model import LogisticRegression

from hydra.models.stacking import StackingEnsemble
from hydra.models.base import ModelWrapper


class MixtureOfExperts:
    """Four experts (one per regime), soft gating by regime probabilities."""

    def __init__(self, base_models: list[ModelWrapper], n_regimes: int = 4):
        self.n_regimes = n_regimes
        self.base_models = base_models
        self.experts: list[Optional[StackingEnsemble]] = [None] * n_regimes
        self.gate_weights: Optional[np.ndarray] = None
        self.gate_model = LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=500,
            random_state=42,
        )

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        regime_labels: np.ndarray,
        regime_probs: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
    ) -> "MixtureOfExperts":
        """Train one expert stack per regime, then learn gating."""
        for r in range(self.n_regimes):
            mask = regime_labels == r
            if mask.sum() < 100:
                continue
            expert = StackingEnsemble(self.base_models)
            sw = sample_weight[mask] if sample_weight is not None else None
            expert.fit(X[mask], y[mask], sample_weight=sw)
            self.experts[r] = expert

        gate_X = regime_probs
        gate_y = regime_labels
        valid = np.isfinite(gate_y.astype(float))
        n_classes = len(np.unique(gate_y[valid]))
        if valid.sum() > 50 and n_classes >= 2:
            self.gate_model.fit(gate_X[valid], gate_y[valid])

        return self

    def predict_proba(
        self,
        X: np.ndarray,
        regime_probs: np.ndarray,
        temperature: float = 1.0,
    ) -> np.ndarray:
        """Gated ensemble prediction."""
        n = len(X)
        gate_logits = regime_probs / temperature
        gate = np.exp(gate_logits - gate_logits.max(axis=1, keepdims=True))
        gate = gate / gate.sum(axis=1, keepdims=True)

        output = np.zeros(n, dtype=np.float64)
        for r in range(self.n_regimes):
            if self.experts[r] is None:
                output += gate[:, r] * 0.5
            else:
                expert_pred = self.experts[r].predict_proba(X)
                output += gate[:, r] * expert_pred

        return output
