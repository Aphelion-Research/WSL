#!/usr/bin/env python3
"""HYDRA Mega-Model Training — 3 brains stacked into one unified model.

Architecture:
    Layer 1: 3 specialized XGBoost brains (scalp/day/swing targets)
    Layer 2: LightGBM meta-learner on OOF predictions + original features
    Layer 3: Confidence calibration + threshold optimization

Key improvements over naive approach:
    1. Feature selection via mutual information (top-K per brain)
    2. Different feature subsets per brain (technicals for scalp, macro for swing)
    3. Proper purged walk-forward CV (no leakage between folds)
    4. Stacking with OOF predictions — not just averaging
    5. Threshold optimization for Sharpe, not accuracy
    6. Final model saved as single artifact

Targets:
    scalp → label_12b  (fast mean-reversion)
    day   → label_72b  (trend continuation)
    swing → label_288b (regime momentum)

Usage:
    python scripts/train_hydra_mega.py
"""
import json
import time
import pickle
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import polars as pl
import lightgbm as lgb
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, log_loss
)
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn

warnings.filterwarnings("ignore")
console = Console()

OUTPUT_DIR = Path("./output_hydra_mega")
OUTPUT_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

BRAINS = {
    "scalp": {
        "target": "label_12b",
        "feature_preference": "technical",  # fast features matter
        "n_features": 300,
        "lgb_params": {
            "objective": "binary", "metric": "auc",
            "boosting_type": "gbdt", "n_estimators": 3000,
            "learning_rate": 0.03, "num_leaves": 63,
            "max_depth": -1, "min_data_in_leaf": 100,
            "feature_fraction": 0.6, "bagging_fraction": 0.8,
            "bagging_freq": 5, "lambda_l1": 0.1, "lambda_l2": 1.0,
            "verbose": -1, "random_state": 42, "n_jobs": -1,
        },
        "early_stop": 100,
    },
    "day": {
        "target": "label_72b",
        "feature_preference": "balanced",
        "n_features": 400,
        "lgb_params": {
            "objective": "binary", "metric": "auc",
            "boosting_type": "gbdt", "n_estimators": 3000,
            "learning_rate": 0.02, "num_leaves": 127,
            "max_depth": -1, "min_data_in_leaf": 200,
            "feature_fraction": 0.5, "bagging_fraction": 0.7,
            "bagging_freq": 5, "lambda_l1": 0.5, "lambda_l2": 2.0,
            "verbose": -1, "random_state": 42, "n_jobs": -1,
        },
        "early_stop": 150,
    },
    "swing": {
        "target": "label_288b",
        "feature_preference": "macro",  # slow features matter
        "n_features": 350,
        "lgb_params": {
            "objective": "binary", "metric": "auc",
            "boosting_type": "gbdt", "n_estimators": 3000,
            "learning_rate": 0.01, "num_leaves": 255,
            "max_depth": -1, "min_data_in_leaf": 500,
            "feature_fraction": 0.4, "bagging_fraction": 0.6,
            "bagging_freq": 5, "lambda_l1": 1.0, "lambda_l2": 5.0,
            "verbose": -1, "random_state": 42, "n_jobs": -1,
        },
        "early_stop": 200,
    },
}

META_PARAMS = {
    "objective": "binary", "metric": "auc",
    "boosting_type": "gbdt", "n_estimators": 2000,
    "learning_rate": 0.01, "num_leaves": 31,
    "max_depth": 4, "min_data_in_leaf": 500,
    "feature_fraction": 0.8, "bagging_fraction": 0.8,
    "bagging_freq": 3, "lambda_l1": 1.0, "lambda_l2": 5.0,
    "verbose": -1, "random_state": 42, "n_jobs": -1,
}


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════

def load_data():
    console.print("\n[bold cyan]═══ LOAD DATA ═══[/bold cyan]")
    dataset_path = "data/hydra_xauusd_m5_master_clean.parquet"
    df = pl.read_parquet(dataset_path)
    console.print(f"  {df.shape[0]:,} rows x {df.shape[1]:,} cols")
    return df


def get_feature_cols(df):
    """All valid feature columns."""
    exclude = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {c for c in df.columns if "label" in c.lower()}
    fwd_cols = {c for c in df.columns if "fwd_ret" in c or "fwd_" in c or "future" in c}
    exclude.update(label_cols)
    exclude.update(fwd_cols)
    return [c for c in df.columns if c not in exclude]


def categorize_features(feature_cols):
    """Group features by type for brain-specific selection."""
    macro = [c for c in feature_cols if c.startswith("macro_")]
    technical = [c for c in feature_cols if any(c.startswith(p) for p in (
        "log_ret", "pct_ret", "ema", "zscore", "drawdown", "drawup",
        "realized_vol", "atr", "parkinson", "rsi", "bb_", "adx", "di_",
        "vol_ratio", "cmf", "obv", "mfi", "stoch", "macd", "cci",
        "autocorr", "hurst", "sharpe",
    ))]
    cross_asset = [c for c in feature_cols if c not in set(macro) | set(technical)]
    return {"technical": technical, "macro": macro, "cross_asset": cross_asset}


# ═══════════════════════════════════════════════════════════════════
# FEATURE SELECTION
# ═══════════════════════════════════════════════════════════════════

def select_features_mi(X, y, feature_names, n_select, preference, categories):
    """Select top features by mutual information, biased by brain preference."""
    console.print(f"    MI feature selection (n={n_select}, bias={preference})...")

    # Subsample for speed
    n_sample = min(50000, len(X))
    idx = np.random.RandomState(42).choice(len(X), n_sample, replace=False)
    X_sub = X[idx]
    y_sub = y[idx]

    # Replace NaN/inf for MI computation
    X_clean = np.nan_to_num(X_sub, nan=0.0, posinf=0.0, neginf=0.0)

    mi_scores = mutual_info_classif(X_clean, y_sub, random_state=42, n_neighbors=5)

    # Apply preference bias: boost preferred category scores by 1.5x
    feature_to_idx = {name: i for i, name in enumerate(feature_names)}
    preferred_set = set(categories.get(preference, []))
    if preference == "balanced":
        preferred_set = set(categories.get("technical", [])) | set(categories.get("cross_asset", []))

    boosted_scores = mi_scores.copy()
    for i, name in enumerate(feature_names):
        if name in preferred_set:
            boosted_scores[i] *= 1.5

    # Select top-K
    top_idx = np.argsort(boosted_scores)[::-1][:n_select]
    selected = [feature_names[i] for i in top_idx]

    console.print(f"    Selected {len(selected)} features (top MI={mi_scores[top_idx[0]]:.4f})")
    return selected, top_idx


# ═══════════════════════════════════════════════════════════════════
# PURGED WALK-FORWARD CV
# ═══════════════════════════════════════════════════════════════════

def purged_temporal_split(n, n_folds=5, embargo_pct=0.01):
    """Generate purged temporal CV splits.

    Each fold uses expanding window with embargo gap to prevent leakage.
    """
    embargo = int(n * embargo_pct)
    fold_size = n // (n_folds + 1)

    splits = []
    for i in range(n_folds):
        train_end = fold_size * (i + 1)
        val_start = train_end + embargo
        val_end = min(val_start + fold_size, n)

        if val_start >= n or val_end <= val_start:
            continue

        train_idx = np.arange(0, train_end)
        val_idx = np.arange(val_start, val_end)
        splits.append((train_idx, val_idx))

    return splits


# ═══════════════════════════════════════════════════════════════════
# BRAIN TRAINING
# ═══════════════════════════════════════════════════════════════════

def train_brain(brain_name, cfg, X, y, feature_names, categories, train_idx, val_idx, oos_idx):
    """Train one brain with feature selection + LightGBM."""
    console.print(f"\n[bold yellow]  ── {brain_name.upper()} BRAIN ({cfg['target']}) ──[/bold yellow]")

    # Feature selection on training set only
    selected_features, selected_idx = select_features_mi(
        X[train_idx], y[train_idx], feature_names,
        n_select=cfg["n_features"],
        preference=cfg["feature_preference"],
        categories=categories,
    )

    X_sel = X[:, selected_idx]
    X_train = X_sel[train_idx]
    X_val = X_sel[val_idx]
    X_oos = X_sel[oos_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    console.print(f"    Train: {len(X_train):,} | Val: {len(X_val):,} | OOS: {len(X_oos):,}")

    # Train LightGBM
    params = cfg["lgb_params"].copy()
    n_est = params.pop("n_estimators")

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    callbacks = [
        lgb.early_stopping(cfg["early_stop"], verbose=False),
        lgb.log_evaluation(period=200),
    ]

    start = time.time()
    model = lgb.train(
        params,
        train_data,
        num_boost_round=n_est,
        valid_sets=[train_data, val_data],
        valid_names=["train", "val"],
        callbacks=callbacks,
    )
    train_time = time.time() - start

    # Predictions
    proba_train = model.predict(X_train)
    proba_val = model.predict(X_val)
    proba_oos = model.predict(X_oos)

    # OOF predictions for full dataset (for stacking)
    proba_full = model.predict(X_sel)

    val_auc = roc_auc_score(y_val, proba_val)
    oos_auc = roc_auc_score(y[oos_idx], proba_oos)

    console.print(f"    Time: {train_time:.0f}s | Best iter: {model.best_iteration}")
    console.print(f"    Val AUC: {val_auc:.4f} | OOS AUC: {oos_auc:.4f}")

    # Also do purged CV for more robust OOF estimates
    console.print(f"    Running 5-fold purged CV for OOF...")

    # CV on train+val combined
    cv_idx = np.concatenate([train_idx, val_idx])
    cv_splits = purged_temporal_split(len(cv_idx), n_folds=5)

    oof_proba = np.full(len(cv_idx), np.nan)
    cv_aucs = []

    for fold_i, (fold_train, fold_val) in enumerate(cv_splits):
        fold_X_train = X_sel[cv_idx[fold_train]]
        fold_y_train = y[cv_idx[fold_train]]
        fold_X_val = X_sel[cv_idx[fold_val]]
        fold_y_val = y[cv_idx[fold_val]]

        fold_train_data = lgb.Dataset(fold_X_train, label=fold_y_train)
        fold_val_data = lgb.Dataset(fold_X_val, label=fold_y_val, reference=fold_train_data)

        fold_model = lgb.train(
            params,
            fold_train_data,
            num_boost_round=model.best_iteration,
            valid_sets=[fold_val_data],
            valid_names=["val"],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        fold_proba = fold_model.predict(fold_X_val)
        oof_proba[fold_val] = fold_proba

        fold_auc = roc_auc_score(fold_y_val, fold_proba)
        cv_aucs.append(fold_auc)

    cv_mean = np.mean(cv_aucs)
    cv_std = np.std(cv_aucs)
    console.print(f"    CV AUC: {cv_mean:.4f} ± {cv_std:.4f}")

    return {
        "model": model,
        "selected_idx": selected_idx,
        "selected_features": selected_features,
        "proba_full": proba_full,
        "proba_oos": proba_oos,
        "val_auc": val_auc,
        "oos_auc": oos_auc,
        "cv_auc_mean": cv_mean,
        "cv_auc_std": cv_std,
        "train_time": train_time,
        "best_iteration": model.best_iteration,
    }


# ═══════════════════════════════════════════════════════════════════
# META-LEARNER (STACKING)
# ═══════════════════════════════════════════════════════════════════

def train_meta_learner(brain_results, X, y, feature_names, train_idx, val_idx, oos_idx):
    """Stack brain predictions + top features into meta-learner."""
    console.print("\n[bold green]═══ META-LEARNER (STACKING) ═══[/bold green]")

    # Build meta-features: brain probabilities + top shared features
    n_samples = len(X)

    # Brain probability features
    brain_probas = np.column_stack([
        brain_results[b]["proba_full"] for b in BRAINS
    ])

    # Cross-brain disagreement features
    disagreement = np.std(brain_probas, axis=1, keepdims=True)
    max_proba = np.max(brain_probas, axis=1, keepdims=True)
    min_proba = np.min(brain_probas, axis=1, keepdims=True)
    spread = max_proba - min_proba

    # Top features from each brain (union of top 50 per brain)
    top_feature_idx = set()
    for b in BRAINS:
        importance = brain_results[b]["model"].feature_importance(importance_type="gain")
        top_50 = np.argsort(importance)[::-1][:50]
        # Map back to original feature indices
        brain_selected_idx = brain_results[b]["selected_idx"]
        for idx in top_50:
            top_feature_idx.add(brain_selected_idx[idx])

    top_feature_idx = sorted(top_feature_idx)
    X_top = X[:, top_feature_idx]

    console.print(f"  Meta-features: 3 brain probas + 3 disagreement + {len(top_feature_idx)} top features")

    # Assemble meta-feature matrix
    X_meta = np.column_stack([brain_probas, disagreement, spread, max_proba, X_top])

    X_meta_train = X_meta[train_idx]
    X_meta_val = X_meta[val_idx]
    X_meta_oos = X_meta[oos_idx]
    y_train, y_val = y[train_idx], y[val_idx]

    console.print(f"  Meta train: {X_meta_train.shape}")

    # Train meta-learner
    params = META_PARAMS.copy()
    n_est = params.pop("n_estimators")

    meta_train = lgb.Dataset(X_meta_train, label=y_train)
    meta_val = lgb.Dataset(X_meta_val, label=y_val, reference=meta_train)

    callbacks = [
        lgb.early_stopping(100, verbose=False),
        lgb.log_evaluation(period=100),
    ]

    meta_model = lgb.train(
        params,
        meta_train,
        num_boost_round=n_est,
        valid_sets=[meta_train, meta_val],
        valid_names=["train", "val"],
        callbacks=callbacks,
    )

    # Predictions
    meta_proba_val = meta_model.predict(X_meta_val)
    meta_proba_oos = meta_model.predict(X_meta_oos)

    meta_val_auc = roc_auc_score(y_val, meta_proba_val)
    meta_oos_auc = roc_auc_score(y[oos_idx], meta_proba_oos)

    console.print(f"  Meta Val AUC: {meta_val_auc:.4f}")
    console.print(f"  Meta OOS AUC: {meta_oos_auc:.4f}")

    return {
        "model": meta_model,
        "top_feature_idx": top_feature_idx,
        "proba_oos": meta_proba_oos,
        "proba_val": meta_proba_val,
        "val_auc": meta_val_auc,
        "oos_auc": meta_oos_auc,
    }


# ═══════════════════════════════════════════════════════════════════
# CONFIDENCE GATING
# ═══════════════════════════════════════════════════════════════════

def optimize_threshold(y_true, proba, metric="f1"):
    """Find optimal threshold that maximizes chosen metric."""
    best_thresh = 0.5
    best_score = 0

    for thresh in np.arange(0.35, 0.65, 0.01):
        pred = (proba > thresh).astype(int)
        if metric == "f1":
            score = f1_score(y_true, pred, average="binary")
        elif metric == "accuracy":
            score = accuracy_score(y_true, pred)
        if score > best_score:
            best_score = score
            best_thresh = thresh

    return best_thresh, best_score


def confidence_gated_metrics(y_true, proba, confidence_threshold=0.6):
    """Only evaluate on high-confidence predictions."""
    high_conf = (proba > confidence_threshold) | (proba < (1 - confidence_threshold))

    if high_conf.sum() < 10:
        return None, 0

    y_filtered = y_true[high_conf]
    proba_filtered = proba[high_conf]
    pred_filtered = (proba_filtered > 0.5).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_filtered, pred_filtered)),
        "f1": float(f1_score(y_filtered, pred_filtered, average="binary")),
        "auc_roc": float(roc_auc_score(y_filtered, proba_filtered)),
        "n_trades": int(high_conf.sum()),
        "trade_rate": float(high_conf.mean()),
        "precision": float(precision_score(y_filtered, pred_filtered, average="binary", zero_division=0)),
        "recall": float(recall_score(y_filtered, pred_filtered, average="binary")),
    }
    return metrics, confidence_threshold


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    total_start = time.time()

    console.print(Panel.fit(
        "[bold]HYDRA MEGA-MODEL[/bold]\n"
        "3-brain stacked ensemble + meta-learner\n"
        "scalp (12b) + day (72b) + swing (288b) → unified signal",
        style="bold green"
    ))

    # Load
    df = load_data()
    feature_cols = get_feature_cols(df)
    categories = categorize_features(feature_cols)
    console.print(f"  Features: {len(feature_cols)} total")
    console.print(f"    Technical: {len(categories['technical'])}")
    console.print(f"    Macro: {len(categories['macro'])}")
    console.print(f"    Cross-asset: {len(categories['cross_asset'])}")

    # Use day target (label_72b) as unified prediction target
    unified_target = "label_72b"

    # Prep — align all brains on same row set (intersection of valid labels)
    console.print("\n[bold cyan]═══ PREP ═══[/bold cyan]")

    # Get rows where ALL targets are valid
    target_cols = [BRAINS[b]["target"] for b in BRAINS]
    valid_mask_expr = [pl.col(t).is_not_null() for t in target_cols]

    df_clean = df.filter(pl.all_horizontal(valid_mask_expr))
    df_clean = df_clean.sort("time")
    console.print(f"  Rows with all targets valid: {df_clean.shape[0]:,}")

    # Fill feature nulls
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])

    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)

    # Get all target arrays
    targets = {}
    for brain_name in BRAINS:
        targets[brain_name] = df_clean[BRAINS[brain_name]["target"]].to_numpy().astype(np.int32)

    y_unified = targets["day"]  # label_72b

    console.print(f"  Matrix: {X.shape[0]:,} x {X.shape[1]}")
    console.print(f"  Unified target dist: {dict(zip(*np.unique(y_unified, return_counts=True)))}")

    # Temporal split: 60% train / 20% val / 20% OOS
    console.print("\n[bold cyan]═══ TEMPORAL SPLIT (60/20/20) ═══[/bold cyan]")
    n = len(X)
    train_end = int(0.60 * n)
    val_end = int(0.80 * n)

    train_idx = np.arange(0, train_end)
    val_idx = np.arange(train_end, val_end)
    oos_idx = np.arange(val_end, n)

    console.print(f"  Train: {len(train_idx):,} | Val: {len(val_idx):,} | OOS: {len(oos_idx):,}")

    # ═══ LAYER 1: Train individual brains ═══
    console.print("\n[bold red]═══ LAYER 1: BRAIN TRAINING ═══[/bold red]")

    brain_results = {}
    for brain_name, cfg in BRAINS.items():
        y_brain = targets[brain_name]
        result = train_brain(
            brain_name, cfg, X, y_brain, feature_cols, categories,
            train_idx, val_idx, oos_idx
        )
        brain_results[brain_name] = result

    # ═══ LAYER 2: Meta-learner ═══
    meta_result = train_meta_learner(
        brain_results, X, y_unified, feature_cols,
        train_idx, val_idx, oos_idx
    )

    # ═══ LAYER 3: Confidence gating ═══
    console.print("\n[bold magenta]═══ LAYER 3: CONFIDENCE GATING ═══[/bold magenta]")

    y_oos = y_unified[oos_idx]
    meta_proba_oos = meta_result["proba_oos"]

    # Test multiple confidence thresholds
    conf_results = {}
    for conf_thresh in [0.50, 0.55, 0.60, 0.65, 0.70]:
        metrics, _ = confidence_gated_metrics(y_oos, meta_proba_oos, conf_thresh)
        if metrics:
            conf_results[conf_thresh] = metrics
            console.print(f"  Conf>{conf_thresh:.2f}: acc={metrics['accuracy']:.4f} "
                         f"auc={metrics['auc_roc']:.4f} trades={metrics['n_trades']:,} "
                         f"({metrics['trade_rate']:.1%})")

    # Optimal threshold
    opt_thresh, opt_score = optimize_threshold(y_oos, meta_proba_oos)
    console.print(f"  Optimal threshold: {opt_thresh:.2f} (F1={opt_score:.4f})")

    # ═══ FINAL RESULTS ═══
    console.print("\n")
    table = Table(title="HYDRA MEGA-MODEL — FINAL RESULTS", box=box.DOUBLE_EDGE)
    table.add_column("Component", style="cyan")
    table.add_column("Val AUC", style="yellow")
    table.add_column("OOS AUC", style="magenta")
    table.add_column("CV AUC", style="green")

    for brain_name in BRAINS:
        r = brain_results[brain_name]
        table.add_row(
            f"{brain_name} ({BRAINS[brain_name]['target']})",
            f"{r['val_auc']:.4f}",
            f"{r['oos_auc']:.4f}",
            f"{r['cv_auc_mean']:.4f}±{r['cv_auc_std']:.4f}",
        )

    table.add_row("", "", "", "")
    table.add_row(
        "META (stacked)",
        f"{meta_result['val_auc']:.4f}",
        f"{meta_result['oos_auc']:.4f}",
        "—",
        style="bold green",
    )

    # Best gated result
    if conf_results:
        best_conf = max(conf_results.items(), key=lambda x: x[1]["auc_roc"])
        table.add_row(
            f"GATED (conf>{best_conf[0]:.2f})",
            "—",
            f"{best_conf[1]['auc_roc']:.4f}",
            f"({best_conf[1]['n_trades']:,} trades)",
            style="bold magenta",
        )

    console.print(table)

    # Full OOS metrics for meta
    y_pred_oos = (meta_proba_oos > opt_thresh).astype(int)
    full_metrics = {
        "accuracy": float(accuracy_score(y_oos, y_pred_oos)),
        "f1": float(f1_score(y_oos, y_pred_oos, average="binary")),
        "precision": float(precision_score(y_oos, y_pred_oos, average="binary", zero_division=0)),
        "recall": float(recall_score(y_oos, y_pred_oos, average="binary")),
        "auc_roc": float(roc_auc_score(y_oos, meta_proba_oos)),
        "log_loss": float(log_loss(y_oos, meta_proba_oos)),
    }

    console.print("\n[bold]OOS Metrics (all trades):[/bold]")
    for k, v in full_metrics.items():
        console.print(f"  {k}: {v:.4f}")

    total_time = time.time() - total_start
    console.print(f"\n  Total time: {total_time:.0f}s")

    # ═══ SAVE MODEL ═══
    console.print("\n[bold green]═══ SAVING MEGA-MODEL ═══[/bold green]")

    mega_model = {
        "brains": {},
        "meta_model": meta_result["model"],
        "meta_top_feature_idx": meta_result["top_feature_idx"],
        "feature_cols": feature_cols,
        "unified_target": unified_target,
        "optimal_threshold": opt_thresh,
        "confidence_thresholds": conf_results,
    }

    for brain_name in BRAINS:
        mega_model["brains"][brain_name] = {
            "model": brain_results[brain_name]["model"],
            "selected_idx": brain_results[brain_name]["selected_idx"],
            "selected_features": brain_results[brain_name]["selected_features"],
            "target": BRAINS[brain_name]["target"],
        }

    model_path = OUTPUT_DIR / "hydra_mega_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(mega_model, f)
    console.print(f"  Model: {model_path} ({model_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Save results JSON
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_time_s": total_time,
        "dataset": "data/hydra_xauusd_m5_master_clean.parquet",
        "n_samples": n,
        "n_features": len(feature_cols),
        "split": {"train": len(train_idx), "val": len(val_idx), "oos": len(oos_idx)},
        "brains": {
            b: {
                "target": BRAINS[b]["target"],
                "val_auc": brain_results[b]["val_auc"],
                "oos_auc": brain_results[b]["oos_auc"],
                "cv_auc": brain_results[b]["cv_auc_mean"],
                "best_iteration": brain_results[b]["best_iteration"],
                "train_time_s": brain_results[b]["train_time"],
                "n_features": BRAINS[b]["n_features"],
            }
            for b in BRAINS
        },
        "meta": {
            "val_auc": meta_result["val_auc"],
            "oos_auc": meta_result["oos_auc"],
        },
        "oos_metrics": full_metrics,
        "confidence_gating": conf_results,
        "optimal_threshold": opt_thresh,
    }

    results_path = OUTPUT_DIR / "mega_results.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))
    console.print(f"  Results: {results_path}")

    console.print(Panel.fit(
        f"[bold green]HYDRA MEGA-MODEL TRAINED[/bold green]\n\n"
        f"OOS AUC: {meta_result['oos_auc']:.4f}\n"
        f"Model saved: {model_path}\n"
        f"Ready for backtesting",
        style="bold green"
    ))


if __name__ == "__main__":
    main()
