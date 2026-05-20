"""Gradient boosting models: LightGBM, XGBoost, CatBoost."""
from __future__ import annotations

from typing import Optional

import numpy as np

from hydra.models.base import ModelWrapper


LGBM_PARAMS = dict(
    objective="binary", boosting_type="gbdt", n_estimators=2000,
    learning_rate=0.02, num_leaves=63, max_depth=-1,
    min_data_in_leaf=50, feature_fraction=0.8, bagging_fraction=0.8,
    bagging_freq=5, lambda_l1=0.1, lambda_l2=0.1,
    verbose=-1, random_state=42,
)

XGB_PARAMS = dict(
    objective="binary:logistic", eval_metric="logloss", n_estimators=2000,
    learning_rate=0.02, max_depth=8, min_child_weight=10,
    subsample=0.8, colsample_bytree=0.8, reg_alpha=0.1, reg_lambda=0.1,
    tree_method="hist", random_state=42,
)

CAT_PARAMS = dict(
    loss_function="Logloss", iterations=2000, learning_rate=0.02,
    depth=8, l2_leaf_reg=3.0, border_count=128, random_strength=1.0,
    od_type="Iter", od_wait=100, random_seed=42, verbose=False,
)


class LGBMModel(ModelWrapper):
    name = "lgbm"

    def __init__(self, **kwargs):
        self.params = {**LGBM_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        import lightgbm as lgb
        params = {**self.params}
        if X_val is not None:
            self.model = lgb.LGBMClassifier(**params)
            self.model.fit(X=X, y=y, sample_weight=sample_weight,
                           eval_set=[(X_val, y_val)],
                           callbacks=[lgb.early_stopping(100, verbose=False)])
        else:
            params["n_estimators"] = min(params.get("n_estimators", 2000), 500)
            self.model = lgb.LGBMClassifier(**params)
            self.model.fit(X=X, y=y, sample_weight=sample_weight)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        import lightgbm as lgb
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        params = {**self.params, "n_estimators": 100}
        callbacks = [lgb.early_stopping(50, verbose=False)]
        new_model = lgb.LGBMClassifier(**params)
        eval_set = [(X_val, y_val)] if X_val is not None else None
        fit_params = dict(
            X=X, y=y, sample_weight=sample_weight,
            eval_set=eval_set, callbacks=callbacks,
            init_model=self.model.booster_,
        )
        if eval_set is None:
            fit_params.pop("eval_set")
            fit_params.pop("callbacks")
        new_model.fit(**fit_params)
        self.model = new_model
        return self

    def feature_importance(self):
        if self.model is None:
            return None
        return self.model.feature_importances_


class XGBModel(ModelWrapper):
    name = "xgb"

    def __init__(self, **kwargs):
        self.params = {**XGB_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        import xgboost as xgb
        params = {**self.params}
        params.pop("early_stopping_rounds", None)
        if X_val is not None:
            self.model = xgb.XGBClassifier(**params, early_stopping_rounds=100)
            self.model.fit(X=X, y=y, sample_weight=sample_weight,
                           eval_set=[(X_val, y_val)], verbose=False)
        else:
            params["n_estimators"] = min(params.get("n_estimators", 2000), 500)
            self.model = xgb.XGBClassifier(**params)
            self.model.fit(X=X, y=y, sample_weight=sample_weight, verbose=False)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        import xgboost as xgb
        params = {**self.params, "n_estimators": 100}
        new_model = xgb.XGBClassifier(**params)
        eval_set = [(X_val, y_val)] if X_val is not None else None
        fit_kw = dict(X=X, y=y, sample_weight=sample_weight,
                      xgb_model=self.model.get_booster())
        if eval_set:
            fit_kw["eval_set"] = eval_set
            fit_kw["verbose"] = False
        new_model.fit(**fit_kw)
        self.model = new_model
        return self

    def feature_importance(self):
        if self.model is None:
            return None
        return self.model.feature_importances_


class CatBoostModel(ModelWrapper):
    name = "catboost"

    def __init__(self, **kwargs):
        self.params = {**CAT_PARAMS, **kwargs}
        self.model = None

    def fit(self, X, y, sample_weight=None, X_val=None, y_val=None):
        from catboost import CatBoostClassifier, Pool
        self.model = CatBoostClassifier(**self.params)
        train_pool = Pool(X, y, weight=sample_weight)
        eval_pool = Pool(X_val, y_val) if X_val is not None else None
        self.model.fit(train_pool, eval_set=eval_pool)
        return self

    def predict_proba(self, X):
        proba = self.model.predict_proba(X)
        return proba[:, 1] if proba.ndim == 2 else proba

    def warm_update(self, X, y, sample_weight=None, X_val=None, y_val=None):
        if self.model is None:
            return self.fit(X, y, sample_weight, X_val, y_val)
        from catboost import CatBoostClassifier, Pool
        params = {**self.params, "iterations": 100}
        new_model = CatBoostClassifier(**params)
        train_pool = Pool(X, y, weight=sample_weight)
        eval_pool = Pool(X_val, y_val) if X_val is not None else None
        new_model.fit(train_pool, eval_set=eval_pool, init_model=self.model)
        self.model = new_model
        return self

    def feature_importance(self):
        if self.model is None:
            return None
        return self.model.get_feature_importance()
