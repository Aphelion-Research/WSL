"""Out-of-fold stacking with meta-learner."""
from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.model_selection import KFold
from sklearn.linear_model import LogisticRegression

from hydra.models.base import ModelWrapper


class StackingEnsemble:
    """12-model stacking with logistic meta-learner."""

    def __init__(self, base_models: list[ModelWrapper], n_inner_folds: int = 5):
        self.base_models = base_models
        self.n_inner_folds = n_inner_folds
        self.meta_learner = LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=1000, random_state=42)
        self._fitted_models: list[list[ModelWrapper]] = []

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        sample_weight: Optional[np.ndarray] = None,
    ) -> "StackingEnsemble":
        """Generate OOF predictions and train meta-learner."""
        n = len(X)
        n_models = len(self.base_models)
        oof = np.zeros((n, n_models), dtype=np.float64)
        kf = KFold(n_splits=self.n_inner_folds, shuffle=False)

        self._fitted_models = [[] for _ in range(n_models)]

        for fold_idx, (tr_idx, val_idx) in enumerate(kf.split(X)):
            X_tr, y_tr = X[tr_idx], y[tr_idx]
            X_va = X[val_idx]
            sw_tr = sample_weight[tr_idx] if sample_weight is not None else None

            for m_idx, model_template in enumerate(self.base_models):
                import copy
                model = copy.deepcopy(model_template)
                model.fit(X_tr, y_tr, sample_weight=sw_tr)
                oof[val_idx, m_idx] = model.predict_proba(X_va)
                self._fitted_models[m_idx].append(model)

        valid_mask = np.isfinite(oof).all(axis=1) & np.isfinite(y)
        self.meta_learner.fit(oof[valid_mask], y[valid_mask])
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Average each base model's fold predictions, then meta-learner."""
        n = len(X)
        n_models = len(self.base_models)
        preds = np.zeros((n, n_models), dtype=np.float64)

        for m_idx in range(n_models):
            fold_preds = []
            for model in self._fitted_models[m_idx]:
                fold_preds.append(model.predict_proba(X))
            preds[:, m_idx] = np.mean(fold_preds, axis=0)

        meta_proba = self.meta_learner.predict_proba(preds)
        return meta_proba[:, 1] if meta_proba.ndim == 2 else meta_proba

    def predict_base(self, X: np.ndarray) -> np.ndarray:
        """Return raw base model predictions (n_samples, n_models)."""
        n = len(X)
        n_models = len(self.base_models)
        preds = np.zeros((n, n_models), dtype=np.float64)
        for m_idx in range(n_models):
            fold_preds = []
            for model in self._fitted_models[m_idx]:
                fold_preds.append(model.predict_proba(X))
            preds[:, m_idx] = np.mean(fold_preds, axis=0)
        return preds
