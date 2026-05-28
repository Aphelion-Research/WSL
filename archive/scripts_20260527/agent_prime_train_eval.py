#!/usr/bin/env python3
"""Train/evaluate Agent-Prime models with chronological non-overlapping events."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet, LogisticRegression, Ridge
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import RobustScaler

try:
    import lightgbm as lgb

    LGBM_AVAILABLE = True
except Exception:
    LGBM_AVAILABLE = False

try:
    import xgboost as xgb

    XGB_AVAILABLE = True
except Exception:
    XGB_AVAILABLE = False

try:
    from catboost import CatBoostRegressor

    CATBOOST_AVAILABLE = True
except Exception:
    CATBOOST_AVAILABLE = False


TARGET_RE = re.compile(r"(^|_)(fwd|future|target|label|lead|next)(_|$)|fwd_ret|forward", re.IGNORECASE)
PERIODS_PER_YEAR_5M = 252 * 288


@dataclass
class ModelConfig:
    name: str
    family: str
    task: str
    feature_mode: str
    factory: Callable[[], Any] | None
    scale: bool = False
    max_features: int | None = None
    min_horizon: int = 0


def is_target_like(name: str) -> bool:
    return bool(TARGET_RE.search(name))


def parse_horizon(col: str) -> int:
    m = re.search(r"(\d+)b", col)
    if not m:
        raise ValueError(f"Cannot parse horizon from {col}")
    return int(m.group(1))


def load_manifest(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for entry in data.get("features", []):
        out[entry["feature_name"]] = entry.get("feature_family", "unknown")
    return out


def leakage_audit(feature_cols: list[str], manifest_path: Path, times: pd.Series, target_cols: list[str], test_fraction: float) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target_like = [c for c in feature_cols if is_target_like(c)]
    manifest_future = [
        entry["feature_name"]
        for entry in manifest.get("features", [])
        if entry.get("uses_future_data") not in (False, "false", "False")
    ]
    negative_shift_names = [c for c in feature_cols if "shift-" in c.lower() or "lead" in c.lower()]
    t = pd.to_datetime(times, utc=True, errors="coerce")
    split = int(len(t) * (1.0 - test_fraction))
    return {
        "no_fwd_ret_columns_in_X": not any("fwd_ret" in c.lower() for c in feature_cols),
        "no_label_columns_in_X": not any(c.lower().startswith("label_") or "_label" in c.lower() for c in feature_cols),
        "no_target_like_columns_in_X": len(target_like) == 0,
        "target_like_feature_columns": target_like,
        "no_negative_shift_feature_names": len(negative_shift_names) == 0,
        "negative_shift_name_hits": negative_shift_names,
        "manifest_uses_future_data_all_false": len(manifest_future) == 0,
        "manifest_future_hits": manifest_future[:20],
        "timestamp_monotonic_increasing": bool(t.is_monotonic_increasing),
        "duplicate_timestamps": int(t.duplicated().sum()),
        "train_validation_rows": int(split),
        "final_test_rows": int(len(t) - split),
        "chronological_split": str(t.iloc[split]) if len(t) and split < len(t) else None,
        "final_test_untouched_until_selection": True,
        "target_columns": target_cols,
        "selected_feature_count_after_leakage_filter": len(feature_cols),
    }


def model_configs(n_jobs: int) -> list[ModelConfig]:
    configs = [
        ModelConfig("mean_predictor", "baseline", "regression", "all", None),
        ModelConfig("previous_return_sign", "baseline", "regression", "all", None),
        ModelConfig("volatility_only_ridge", "baseline", "regression", "volatility", lambda: Ridge(alpha=10.0, solver="lsqr"), scale=True),
        ModelConfig("ridge_alpha_10", "linear", "regression", "all", lambda: Ridge(alpha=10.0, solver="lsqr"), scale=True, max_features=600),
        ModelConfig("elasticnet_a001_l1_02", "linear", "regression", "all", lambda: ElasticNet(alpha=0.001, l1_ratio=0.2, max_iter=2000, random_state=17), scale=True, max_features=500),
        ModelConfig("logistic_direction_l2", "linear", "classification", "all", lambda: LogisticRegression(C=0.5, max_iter=300, class_weight="balanced", solver="saga"), scale=True, max_features=400, min_horizon=20),
        ModelConfig("random_forest_depth8", "tree", "regression", "all", lambda: RandomForestRegressor(n_estimators=90, max_depth=8, min_samples_leaf=40, max_features="sqrt", n_jobs=n_jobs, random_state=19), max_features=600, min_horizon=20),
        ModelConfig("extra_trees_depth8", "tree", "regression", "all", lambda: ExtraTreesRegressor(n_estimators=100, max_depth=8, min_samples_leaf=40, max_features="sqrt", n_jobs=n_jobs, random_state=23), max_features=600, min_horizon=20),
        ModelConfig("hist_gradient_boosting", "boosting", "regression", "all", lambda: HistGradientBoostingRegressor(max_iter=120, learning_rate=0.04, max_leaf_nodes=31, l2_regularization=0.1, random_state=29), max_features=500, min_horizon=20),
    ]
    if LGBM_AVAILABLE:
        configs.append(
            ModelConfig(
                "lightgbm_l2_leaves31",
                "boosting",
                "regression",
                "all",
                lambda: lgb.LGBMRegressor(
                    n_estimators=350,
                    learning_rate=0.03,
                    num_leaves=31,
                    subsample=0.85,
                    colsample_bytree=0.75,
                    min_child_samples=80,
                    reg_lambda=2.0,
                    n_jobs=n_jobs,
                    random_state=31,
                    verbose=-1,
                ),
                max_features=700,
                min_horizon=20,
            )
        )
    if XGB_AVAILABLE:
        configs.append(
            ModelConfig(
                "xgboost_hist_depth3",
                "boosting",
                "regression",
                "all",
                lambda: xgb.XGBRegressor(
                    n_estimators=260,
                    learning_rate=0.035,
                    max_depth=3,
                    subsample=0.85,
                    colsample_bytree=0.75,
                    reg_lambda=3.0,
                    objective="reg:squarederror",
                    tree_method="hist",
                    n_jobs=n_jobs,
                    random_state=37,
                ),
                max_features=700,
                min_horizon=20,
            )
        )
    if CATBOOST_AVAILABLE:
        configs.append(
            ModelConfig(
                "catboost_depth6",
                "boosting",
                "regression",
                "all",
                lambda: CatBoostRegressor(iterations=200, learning_rate=0.04, depth=6, loss_function="RMSE", random_seed=41, verbose=False, thread_count=n_jobs),
                max_features=700,
                min_horizon=20,
            )
        )
    return configs


def choose_columns(feature_cols: list[str], family_by_feature: dict[str, str], mode: str, top_features: list[str] | None = None) -> list[str]:
    if mode == "all":
        return feature_cols
    if mode.startswith("no_"):
        family = mode[3:]
        return [c for c in feature_cols if family_by_feature.get(c, "unknown") != family]
    if mode == "volatility":
        return [c for c in feature_cols if family_by_feature.get(c, "unknown") == "volatility"]
    if mode == "microstructure":
        return [c for c in feature_cols if family_by_feature.get(c, "unknown") == "microstructure"]
    if mode == "top50":
        return [c for c in (top_features or [])[:50] if c in feature_cols]
    if mode == "top100":
        return [c for c in (top_features or [])[:100] if c in feature_cols]
    raise ValueError(f"Unknown feature mode: {mode}")


def chronological_events(n: int, horizon: int, target: pd.Series) -> np.ndarray:
    events = np.arange(0, n, horizon, dtype=int)
    return events[target.iloc[events].notna().to_numpy()]


def make_folds(n: int, horizon: int, events: np.ndarray, test_fraction: float, folds: int) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray, int]:
    test_start = int(n * (1.0 - test_fraction))
    train_val_end = max(0, test_start - horizon)
    val_start_min = int(train_val_end * 0.45)
    edges = np.linspace(val_start_min, train_val_end, folds + 1, dtype=int)
    fold_indices = []
    for i in range(folds):
        val_start = int(edges[i])
        val_end = int(edges[i + 1])
        train_events = events[events < max(0, val_start - horizon)]
        val_events = events[(events >= val_start) & (events < val_end)]
        if len(train_events) >= 200 and len(val_events) >= 50:
            fold_indices.append((train_events, val_events))
    test_events = events[events >= test_start]
    return fold_indices, test_events, test_start


def feature_prefilter(X_train: pd.DataFrame, y_train: pd.Series, cols: list[str], max_features: int | None = None) -> list[str]:
    if not cols:
        return []
    subset = X_train[cols]
    keep = []
    for col in cols:
        s = subset[col]
        if s.notna().mean() < 0.05:
            continue
        if s.nunique(dropna=True) <= 1:
            continue
        keep.append(col)
    if max_features is not None and len(keep) > max_features:
        corr = subset[keep].corrwith(y_train).abs().replace([np.inf, -np.inf], np.nan).fillna(0.0)
        keep = corr.sort_values(ascending=False).head(max_features).index.tolist()
    return keep


def fit_predict(config: ModelConfig, X_train: pd.DataFrame, y_train: pd.Series, X_eval: pd.DataFrame, horizon: int) -> tuple[np.ndarray, Any]:
    if config.name == "mean_predictor":
        return np.full(len(X_eval), float(y_train.mean())), {"mean": float(y_train.mean())}
    if config.name == "previous_return_sign":
        col = "ret_pct_1b" if "ret_pct_1b" in X_eval.columns else None
        if col is None:
            return np.zeros(len(X_eval)), {"fallback": "missing ret_pct_1b"}
        scale = float(np.nanmedian(np.abs(y_train))) if len(y_train) else 0.0
        return np.sign(X_eval[col].fillna(0.0).to_numpy()) * scale, {"scale": scale}

    y_fit = y_train.copy()
    model = config.factory()
    steps: list[tuple[str, Any]] = [("imputer", SimpleImputer(strategy="median", keep_empty_features=True))]
    if config.scale:
        steps.append(("scaler", RobustScaler()))
    steps.append(("model", model))
    pipe = Pipeline(steps)
    if config.task == "classification":
        y_fit = (y_train > 0).astype(int)
    pipe.fit(X_train, y_fit)
    if config.task == "classification":
        proba = pipe.predict_proba(X_eval)[:, 1]
        scale = float(np.nanmedian(np.abs(y_train))) if len(y_train) else 1.0
        pred = (proba - 0.5) * 2.0 * scale
    else:
        pred = pipe.predict(X_eval)
    return np.asarray(pred, dtype="float64"), pipe


def strategy_returns(pred: np.ndarray, actual: np.ndarray, threshold: float, cost_bps: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    pos = np.where(pred > threshold, 1.0, np.where(pred < -threshold, -1.0, 0.0))
    prev = np.concatenate([[0.0], pos[:-1]])
    turnover = np.abs(pos - prev)
    costs = turnover * cost_bps / 10000.0
    returns = pos * actual - costs
    return returns, pos, turnover


def max_drawdown(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return float("nan")
    peak = np.maximum.accumulate(equity)
    dd = equity / np.maximum(peak, 1e-12) - 1.0
    return float(np.nanmin(dd))


def profit_factor(returns: np.ndarray) -> float | None:
    gains = returns[returns > 0].sum()
    losses = -returns[returns < 0].sum()
    if losses <= 1e-12:
        return None
    return float(gains / losses)


def aggregate_worst(times: pd.Series, returns: np.ndarray, freq: str) -> float | None:
    if len(returns) == 0:
        return None
    s = pd.Series(returns, index=pd.to_datetime(times, utc=True))
    grouped = s.groupby(pd.Grouper(freq=freq)).sum()
    grouped = grouped.dropna()
    if grouped.empty:
        return None
    return float(grouped.min())


def metrics(pred: np.ndarray, actual: np.ndarray, times: pd.Series, horizon: int, threshold: float, cost_bps: float) -> dict[str, Any]:
    pred = np.asarray(pred, dtype="float64")
    actual = np.asarray(actual, dtype="float64")
    mask = np.isfinite(pred) & np.isfinite(actual)
    pred = pred[mask]
    actual = actual[mask]
    times = times.iloc[np.where(mask)[0]].reset_index(drop=True)
    if len(actual) == 0:
        return {"events": 0}

    strat, pos, turnover = strategy_returns(pred, actual, threshold, cost_bps)
    equity = np.cumprod(1.0 + np.clip(strat, -0.999, None))
    total_return = float(equity[-1] - 1.0)
    periods_per_year = PERIODS_PER_YEAR_5M / horizon
    years = max(len(strat) / periods_per_year, 1e-12)
    ann_return = float((1.0 + total_return) ** (1.0 / years) - 1.0) if total_return > -1 else -1.0
    ann_vol = float(np.nanstd(strat) * math.sqrt(periods_per_year))
    sharpe = float(np.nanmean(strat) / (np.nanstd(strat) + 1e-12) * math.sqrt(periods_per_year))
    downside = strat[strat < 0]
    sortino = float(np.nanmean(strat) / (np.nanstd(downside) + 1e-12) * math.sqrt(periods_per_year)) if len(downside) else None
    mdd = max_drawdown(equity)
    calmar = float(ann_return / abs(mdd)) if mdd < -1e-12 else None
    trade_count = int((turnover > 0).sum())
    active = pos != 0
    active_returns = strat[active]
    return {
        "events": int(len(actual)),
        "threshold": float(threshold),
        "cost_bps": float(cost_bps),
        "r2": float(r2_score(actual, pred)) if len(actual) >= 2 else None,
        "mse": float(mean_squared_error(actual, pred)),
        "directional_accuracy": float((np.sign(pred) == np.sign(actual)).mean()),
        "total_return": total_return,
        "annualized_return": ann_return,
        "annualized_vol": ann_vol,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": mdd,
        "turnover": float(turnover.sum()),
        "avg_turnover_per_event": float(turnover.mean()),
        "number_of_trades": trade_count,
        "average_trade_return": float(active_returns.mean()) if len(active_returns) else None,
        "win_rate": float((active_returns > 0).mean()) if len(active_returns) else None,
        "profit_factor": profit_factor(active_returns),
        "worst_day": aggregate_worst(times, strat, "D"),
        "worst_week": aggregate_worst(times, strat, "W"),
        "worst_month": aggregate_worst(times, strat, "ME"),
        "exposure_percentage": float(active.mean() * 100.0),
        "hit_rate": float((strat > 0).mean()),
    }


def choose_threshold(pred: np.ndarray, actual: np.ndarray, times: pd.Series, horizon: int, cost_bps: float) -> tuple[float, dict[str, Any]]:
    finite_abs = np.abs(pred[np.isfinite(pred)])
    if finite_abs.size == 0:
        return 0.0, metrics(pred, actual, times, horizon, 0.0, cost_bps)
    candidates = {0.0}
    for q in [0.25, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95]:
        candidates.add(float(np.quantile(finite_abs, q)))
    best_threshold = 0.0
    best_metrics = None
    best_objective = -1e99
    for threshold in sorted(candidates):
        m = metrics(pred, actual, times, horizon, threshold, cost_bps)
        if m.get("events", 0) == 0:
            continue
        if m.get("number_of_trades", 0) < 5 or m.get("exposure_percentage", 0.0) < 1.0:
            continue
        objective = float(m.get("sharpe") or -999.0) - 0.50 * abs(float(m.get("max_drawdown") or 0.0))
        if objective > best_objective:
            best_objective = objective
            best_threshold = threshold
            best_metrics = m
    if best_metrics is None:
        best_metrics = metrics(pred, actual, times, horizon, 0.0, cost_bps)
    return best_threshold, best_metrics


def evaluate_config(
    config: ModelConfig,
    X: pd.DataFrame,
    y: pd.Series,
    times: pd.Series,
    feature_cols: list[str],
    family_by_feature: dict[str, str],
    horizon: int,
    folds: list[tuple[np.ndarray, np.ndarray]],
    cost_bps: float,
    feature_mode: str | None = None,
    top_features: list[str] | None = None,
) -> dict[str, Any]:
    mode = feature_mode or config.feature_mode
    cols0 = choose_columns(feature_cols, family_by_feature, mode, top_features)
    if not cols0:
        return {"model": config.name, "feature_mode": mode, "status": "NO_FEATURES"}

    all_pred = []
    all_actual = []
    all_times = []
    fold_summaries = []
    started = time.time()
    for fold_id, (train_idx, val_idx) in enumerate(folds, 1):
        if config.name == "mean_predictor":
            cols = []
        elif config.name == "previous_return_sign":
            cols = ["ret_pct_1b"] if "ret_pct_1b" in X.columns else []
        else:
            cols = feature_prefilter(X.iloc[train_idx], y.iloc[train_idx], cols0, config.max_features)
        if config.name == "previous_return_sign" and not cols:
            fold_summaries.append({"fold": fold_id, "status": "ERROR", "error": "missing ret_pct_1b"})
            continue
        if not cols:
            if config.name != "mean_predictor":
                continue
        try:
            pred, _ = fit_predict(config, X.iloc[train_idx][cols], y.iloc[train_idx], X.iloc[val_idx][cols], horizon)
        except Exception as exc:
            fold_summaries.append({"fold": fold_id, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
            continue
        actual = y.iloc[val_idx].to_numpy(dtype="float64")
        all_pred.append(pred)
        all_actual.append(actual)
        all_times.append(times.iloc[val_idx].reset_index(drop=True))
        fold_summaries.append({"fold": fold_id, "status": "OK", "train_events": int(len(train_idx)), "validation_events": int(len(val_idx)), "features": int(len(cols))})

    if not all_pred:
        return {"model": config.name, "feature_mode": mode, "status": "NO_VALID_FOLDS", "folds": fold_summaries}

    pred = np.concatenate(all_pred)
    actual = np.concatenate(all_actual)
    val_times = pd.concat(all_times, ignore_index=True)
    threshold, val_metrics = choose_threshold(pred, actual, val_times, horizon, cost_bps)
    return {
        "model": config.name,
        "family": config.family,
        "task": config.task,
        "feature_mode": mode,
        "status": "OK",
        "horizon": horizon,
        "selected_threshold": threshold,
        "validation_metrics": val_metrics,
        "folds": fold_summaries,
        "elapsed_seconds": time.time() - started,
    }


def fit_final_model(config: ModelConfig, X: pd.DataFrame, y: pd.Series, train_idx: np.ndarray, test_idx: np.ndarray, cols: list[str], horizon: int) -> tuple[np.ndarray, Any, list[str]]:
    if config.name == "mean_predictor":
        cols = []
    elif config.name == "previous_return_sign":
        cols = ["ret_pct_1b"] if "ret_pct_1b" in X.columns else []
    else:
        cols = feature_prefilter(X.iloc[train_idx], y.iloc[train_idx], cols, config.max_features)
    pred, model = fit_predict(config, X.iloc[train_idx][cols], y.iloc[train_idx], X.iloc[test_idx][cols], horizon)
    return pred, model, cols


def feature_importance(model: Any, cols: list[str]) -> list[dict[str, Any]]:
    if isinstance(model, dict):
        return []
    estimator = model.named_steps.get("model") if isinstance(model, Pipeline) else model
    values = None
    if hasattr(estimator, "feature_importances_"):
        values = np.asarray(estimator.feature_importances_, dtype="float64")
    elif hasattr(estimator, "coef_"):
        values = np.abs(np.asarray(estimator.coef_, dtype="float64")).ravel()
    if values is None or len(values) != len(cols):
        return []
    order = np.argsort(values)[::-1]
    return [{"feature": cols[i], "importance": float(values[i])} for i in order[:50]]


def baseline_thresholded_direction(y: pd.Series, events: np.ndarray, horizon: int, times: pd.Series) -> dict[str, Any]:
    actual = y.iloc[events].to_numpy(dtype="float64")
    pred = np.zeros_like(actual)
    return metrics(pred, actual, times.iloc[events].reset_index(drop=True), horizon, 1e-99, 2.0)


def generate_report(summary: dict[str, Any], output_path: Path) -> None:
    best = summary["best"]
    final = summary["final_test"]
    validation = best.get("validation_metrics", {})
    lines = [
        "# Agent-Prime XAUUSD Dataset and Model Report",
        "",
        f"Conclusion: **{summary['conclusion']}**",
        "",
        "## Dataset",
        f"- Chosen source: `{summary['dataset_choice']['chosen_source']}`",
        f"- Reason: {summary['dataset_choice']['reason']}",
        f"- Dataset output: `{summary['dataset_paths']['combined']}`",
        f"- Feature path: `{summary['dataset_paths']['features']}`",
        f"- Target path: `{summary['dataset_paths']['targets']}`",
        f"- Manifest: `{summary['dataset_paths']['manifest']}`",
        f"- Rows: {summary['dataset_validation'].get('rows'):,}",
        f"- Feature count: {summary['dataset_validation'].get('feature_columns'):,}",
        f"- Families: `{summary['dataset_validation'].get('features_by_family')}`",
        "",
        "## Leakage Audit",
        "```json",
        json.dumps(summary["leakage_audit"], indent=2),
        "```",
        "",
        "## Model Search",
        f"- Models tried: {', '.join(summary['models_tried'])}",
        f"- Best validation config: `{best['model']}` target `fwd_ret_{best['horizon']}b`, threshold `{best['selected_threshold']:.8g}`",
        f"- Validation Sharpe at 2 bps: `{validation.get('sharpe')}`",
        f"- Validation max drawdown at 2 bps: `{validation.get('max_drawdown')}`",
        f"- Validation directional accuracy: `{validation.get('directional_accuracy')}`",
        f"- Validation R2: `{validation.get('r2')}`",
        "",
        "## Final Untouched OOS Test",
        "The final test period was not used for target/model/threshold selection.",
        "```json",
        json.dumps(final, indent=2),
        "```",
        "",
        "## Cost Sensitivity",
        "```json",
        json.dumps(summary["cost_sensitivity"], indent=2),
        "```",
        "",
        "## Feature Importance",
    ]
    for row in summary.get("feature_importance", [])[:25]:
        lines.append(f"- `{row['feature']}`: {row['importance']:.6g}")
    lines.extend(
        [
            "",
            "## Ablation Results",
            "```json",
            json.dumps(summary["ablations"], indent=2),
            "```",
            "",
            "## Failure Modes",
        ]
    )
    for item in summary["failure_modes"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Predictive Character",
            summary["predictive_character"],
            "",
            "## Production Worthiness",
            summary["production_worthiness"],
            "",
            "## Next 5 Highest-ROI Improvements",
        ]
    )
    for item in summary["next_improvements"]:
        lines.append(f"- {item}")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default="data/agent_prime/agent_prime_xauusd_m5_features.parquet")
    parser.add_argument("--targets", default="data/agent_prime/agent_prime_xauusd_m5_targets.parquet")
    parser.add_argument("--manifest", default="data/agent_prime/agent_prime_xauusd_m5_feature_manifest.json")
    parser.add_argument("--dataset-validation", default="data/agent_prime/agent_prime_xauusd_m5_validation.json")
    parser.add_argument("--output-json", default="reports/agent_prime_model_results.json")
    parser.add_argument("--output-report", default="reports/agent_prime_dataset_model_report.md")
    parser.add_argument("--folds", type=int, default=4)
    parser.add_argument("--test-fraction", type=float, default=0.20)
    parser.add_argument("--selection-cost-bps", type=float, default=2.0)
    parser.add_argument("--horizons", nargs="*", type=int, default=None)
    parser.add_argument("--n-jobs", type=int, default=min(os.cpu_count() or 4, 20))
    args = parser.parse_args()

    features = pd.read_parquet(args.features)
    targets = pd.read_parquet(args.targets)
    data = features.merge(targets, on="time", how="inner", validate="one_to_one")
    data["time"] = pd.to_datetime(data["time"], utc=True, errors="coerce")
    data = data.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    target_cols = [c for c in targets.columns if c.startswith("fwd_ret_")]
    if args.horizons:
        allowed = {f"fwd_ret_{h}b" for h in args.horizons}
        target_cols = [c for c in target_cols if c in allowed]
    if not target_cols:
        raise ValueError("No fwd_ret_* target columns available")

    feature_cols = [c for c in features.columns if c != "time" and not is_target_like(c)]
    numeric_feature_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(features[c])]
    family_by_feature = load_manifest(Path(args.manifest))
    audit = leakage_audit(numeric_feature_cols, Path(args.manifest), data["time"], target_cols, args.test_fraction)

    configs = model_configs(args.n_jobs)
    all_results = []
    models_tried = []
    for target_col in target_cols:
        horizon = parse_horizon(target_col)
        y = data[target_col].astype("float64")
        events = chronological_events(len(data), horizon, y)
        folds, test_events, test_start = make_folds(len(data), horizon, events, args.test_fraction, args.folds)
        if len(folds) == 0 or len(test_events) < 20:
            all_results.append({"target": target_col, "status": "INSUFFICIENT_EVENTS", "horizon": horizon})
            continue
        X = data[numeric_feature_cols]
        for config in configs:
            models_tried.append(config.name)
            if horizon < config.min_horizon:
                all_results.append(
                    {
                        "target": target_col,
                        "horizon": horizon,
                        "model": config.name,
                        "family": config.family,
                        "task": config.task,
                        "feature_mode": config.feature_mode,
                        "status": f"SKIPPED_MIN_HORIZON_{config.min_horizon}",
                        "reason": "short-horizon event count is large; this family is covered on longer horizons",
                    }
                )
                continue
            print(f"MODEL_SEARCH target={target_col} model={config.name} folds={len(folds)} events={len(events)}", flush=True)
            result = evaluate_config(
                config,
                X,
                y,
                data["time"],
                numeric_feature_cols,
                family_by_feature,
                horizon,
                folds,
                args.selection_cost_bps,
            )
            result["target"] = target_col
            result["test_events"] = int(len(test_events))
            result["test_start_index"] = int(test_start)
            all_results.append(result)

    valid_results = [r for r in all_results if r.get("status") == "OK" and r.get("validation_metrics", {}).get("events", 0) > 0]
    if not valid_results:
        raise RuntimeError("No valid model search result")

    def result_key(r: dict[str, Any]) -> tuple[float, float]:
        m = r["validation_metrics"]
        return (float(m.get("sharpe") or -999.0), -abs(float(m.get("max_drawdown") or 0.0)))

    best = max(valid_results, key=result_key)
    best_config = next(c for c in configs if c.name == best["model"])
    horizon = int(best["horizon"])
    target_col = best["target"]
    y = data[target_col].astype("float64")
    events = chronological_events(len(data), horizon, y)
    folds, test_events, test_start = make_folds(len(data), horizon, events, args.test_fraction, args.folds)
    train_events = events[events < max(0, test_start - horizon)]
    X = data[numeric_feature_cols]
    final_cols = choose_columns(numeric_feature_cols, family_by_feature, best_config.feature_mode)
    final_pred, final_model, final_cols = fit_final_model(best_config, X, y, train_events, test_events, final_cols, horizon)
    final_actual = y.iloc[test_events].to_numpy(dtype="float64")
    final_times = data["time"].iloc[test_events].reset_index(drop=True)
    final_metrics = metrics(final_pred, final_actual, final_times, horizon, float(best["selected_threshold"]), args.selection_cost_bps)

    cost_sensitivity = {
        f"{cost:g}bps": metrics(final_pred, final_actual, final_times, horizon, float(best["selected_threshold"]), cost)
        for cost in [0.0, 1.0, 2.0, 5.0]
    }
    importances = feature_importance(final_model, final_cols)
    top_features = [row["feature"] for row in importances]

    ablations = {}
    for mode in ["all", "no_macro", "no_volatility", "no_time", "no_microstructure", "top50", "top100", "volatility"]:
        print(f"ABLATION mode={mode}", flush=True)
        res = evaluate_config(
            best_config,
            X,
            y,
            data["time"],
            numeric_feature_cols,
            family_by_feature,
            horizon,
            folds,
            args.selection_cost_bps,
            feature_mode=mode,
            top_features=top_features,
        )
        ablations[mode] = {
            "status": res.get("status"),
            "selected_threshold": res.get("selected_threshold"),
            "validation_metrics": res.get("validation_metrics"),
        }

    dataset_validation = json.loads(Path(args.dataset_validation).read_text(encoding="utf-8"))
    final_sharpe = float(final_metrics.get("sharpe") or 0.0)
    final_dd = abs(float(final_metrics.get("max_drawdown") or 0.0))
    final_r2 = float(final_metrics.get("r2") or 0.0)
    final_dir = float(final_metrics.get("directional_accuracy") or 0.0)
    if not audit["no_target_like_columns_in_X"] or not audit["manifest_uses_future_data_all_false"]:
        conclusion = "BUGGED / INVALID RESULT"
    elif final_sharpe > 1.5 and final_dd < 0.25 and final_dir > 0.515:
        conclusion = "PRODUCTION-CANDIDATE"
    elif final_sharpe > 0.5 or final_dir > 0.505:
        conclusion = "RESEARCH-ONLY"
    else:
        conclusion = "FAILED / NOT ENOUGH EDGE"

    vol_ablation = ablations.get("no_volatility", {}).get("validation_metrics") or {}
    all_ablation = ablations.get("all", {}).get("validation_metrics") or {}
    if all_ablation.get("sharpe") is not None and vol_ablation.get("sharpe") is not None:
        vol_dependency = float(all_ablation["sharpe"]) - float(vol_ablation["sharpe"])
    else:
        vol_dependency = None

    predictive_character = (
        f"Final OOS R2={final_r2:.6f}, directional accuracy={final_dir:.4f}, Sharpe@2bps={final_sharpe:.4f}. "
        f"Validation no-volatility Sharpe delta={vol_dependency}; this is treated as volatility/risk-timing edge unless R2 and directional accuracy are both clearly positive."
    )
    production_worthiness = (
        "Not production-worthy unless conclusion is PRODUCTION-CANDIDATE and live execution/slippage checks pass. "
        "This run is research evidence only; it uses historical M5 non-overlapping events and local daily macro data lagged by one day."
    )
    failure_modes = [
        "RAGD MCP was unavailable on 127.0.0.1:7474 during startup, so retrieval context could not be loaded live.",
        "QuantLib is not installed, so holiday-proximity features were not added.",
        "Daily macro/cross-asset data are conservatively lagged one calendar day; intraday release-time precision is not modeled.",
        "Evaluation uses non-overlapping horizon events to avoid overlapping-label inflation; per-bar deployment behavior still needs a separate simulator.",
        "Existing HYDRA clean features are trusted as existing point-in-time features but cannot be re-derived column-by-column in this run.",
    ]
    next_improvements = [
        "Rebuild every existing HYDRA feature from raw sources with a machine-checkable point-in-time manifest.",
        "Add a release-calendar-aware macro join instead of one-day lag approximations.",
        "Train a purged cross-validation stacker only on validation folds, then test once on a later untouched live-like slice.",
        "Add spread/slippage estimates from true tick data instead of generic bps sensitivity.",
        "Run live paper-trading shadow evaluation with frozen features/model and no threshold retuning.",
    ]

    summary = {
        "dataset_choice": {
            "chosen_source": "data/mt5_history/XAUUSD_M5_dukascopy.parquet plus data/hydra_xauusd_m5_master_clean.parquet",
            "reason": "It has the longest stable M5 OHLCV range that aligns one-to-one with the clean existing HYDRA feature table; the MT5 MASTER file has a corrupted time column and extra unmatched rows.",
        },
        "dataset_paths": {
            "features": args.features,
            "targets": args.targets,
            "combined": "data/agent_prime/agent_prime_xauusd_m5_modeling.parquet",
            "manifest": args.manifest,
            "validation": args.dataset_validation,
        },
        "dataset_validation": dataset_validation,
        "leakage_audit": audit,
        "models_tried": sorted(set(models_tried)),
        "all_model_results": all_results,
        "best": best,
        "final_test": final_metrics,
        "cost_sensitivity": cost_sensitivity,
        "feature_importance": importances,
        "ablations": ablations,
        "failure_modes": failure_modes,
        "predictive_character": predictive_character,
        "production_worthiness": production_worthiness,
        "next_improvements": next_improvements,
        "conclusion": conclusion,
    }

    Path(args.output_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    generate_report(summary, Path(args.output_report))
    print(json.dumps({k: summary[k] for k in ["conclusion", "best", "final_test", "cost_sensitivity"]}, indent=2))
    print(f"REPORT {args.output_report}")
    print(f"RESULTS {args.output_json}")


if __name__ == "__main__":
    main()
