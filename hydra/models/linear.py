"""Linear/probabilistic models: LogReg, GNB, LDA."""
from __future__ import annotations

from typing import Optional

import numpy as np

from hydra.models.base import ModelWrapper

LR_PARAMS = dict(
    penalty="elasticnet", solver="saga", l1_ratio=0.5,
    C=0.5, max_iter=5000, class_weight="balanced", random_state=42,
)

GNB_PARAMS = dict(var_smoothing=1e-9)

LDA_PARAMS = dict(solver="lsqr", shrinkage="auto")


class LRModel(ModelWrapper):
    name = "lr"

    def __init__(self, **kwargs):
        self.params = {**LR_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.linear_model import LogisticRegression
        self.model = LogisticRegression(**self.params)
        self.model.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.linear_model import SGDClassifier
        if not hasattr(self, "_sgd"):
            self._sgd = SGDClassifier(
                loss="log_loss", penalty="elasticnet",
                l1_ratio=0.5, alpha=1.0 / (0.5 * len(y)),
                random_state=42, warm_start=True,
            )
        self._sgd.partial_fit(X, y, classes=[0, 1],
                              sample_weight=sample_weight)
        self.model = self._sgd
        return self


class GNBModel(ModelWrapper):
    name = "gnb"

    def __init__(self, **kwargs):
        self.params = {**GNB_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.naive_bayes import GaussianNB
        self.model = GaussianNB(**self.params)
        self.model.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        self.model.partial_fit(X, y, sample_weight=sample_weight)
        return self


class LDAModel(ModelWrapper):
    name = "lda"

    def __init__(self, **kwargs):
        self.params = {**LDA_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
        self.model = LinearDiscriminantAnalysis(**self.params)
        self.model.fit(X, y)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba
