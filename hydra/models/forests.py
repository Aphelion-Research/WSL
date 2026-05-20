"""Forest models: RandomForest, ExtraTrees, HistGradientBoosting."""
from __future__ import annotations

from typing import Optional

import numpy as np

from hydra.models.base import ModelWrapper

RF_PARAMS = dict(
    n_estimators=800, max_depth=12, min_samples_leaf=30,
    max_features="sqrt", n_jobs=-1, random_state=42, class_weight="balanced",
)

ET_PARAMS = dict(
    n_estimators=800, max_depth=12, min_samples_leaf=30,
    max_features="sqrt", n_jobs=-1, random_state=42, class_weight="balanced",
)

HGB_PARAMS = dict(
    max_iter=1000, learning_rate=0.05, max_leaf_nodes=63,
    min_samples_leaf=30, l2_regularization=0.1,
    early_stopping=True, validation_fraction=0.15, n_iter_no_change=50,
    random_state=42,
)


class RFModel(ModelWrapper):
    name = "rf"

    def __init__(self, **kwargs):
        self.params = {**RF_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.ensemble import RandomForestClassifier
        self.model = RandomForestClassifier(**self.params)
        self.model.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def feature_importance(self):
        if self.model is None:
            return None
        return self.model.feature_importances_


class ETModel(ModelWrapper):
    name = "et"

    def __init__(self, **kwargs):
        self.params = {**ET_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.ensemble import ExtraTreesClassifier
        self.model = ExtraTreesClassifier(**self.params)
        self.model.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def feature_importance(self):
        if self.model is None:
            return None
        return self.model.feature_importances_


class HGBModel(ModelWrapper):
    name = "hgb"

    def __init__(self, **kwargs):
        self.params = {**HGB_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from sklearn.ensemble import HistGradientBoostingClassifier
        self.model = HistGradientBoostingClassifier(**self.params)
        self.model.fit(X, y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        self.model.warm_start = True
        self.model.max_iter += 100
        self.model.fit(X, y, sample_weight=sample_weight)
        return self
