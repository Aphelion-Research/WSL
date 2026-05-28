#!/usr/bin/env python3
"""
Multi-Style Trading Model Training
Trains 10 models across scalper, day trader, and swing trader horizons.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import polars as pl
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import xgboost as xgb
import lightgbm as lgb

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# CONFIGURATION
# ============================================================

DATASET_PATH = ROOT / "data" / "feature_fabric" / "hydra_xauusd_feature_fabric_v1.parquet"
OUTPUT_DIR = ROOT / "models" / "multi_style" / datetime.now().strftime("%Y%m%d_%H%M%S")

# Trading style horizons
HORIZONS = {
    "scalper": 5,      # 5 bars = 25 minutes
    "day_trader": 72,  # 72 bars = 6 hours
    "swing_trader": 288,  # 288 bars = 24 hours
}

# Multi-horizon for unified models
MULTI_HORIZONS = [5, 72, 288]

# Model configs
MODEL_CONFIGS = [
    {
        "name": "RF_Scalper",
        "type": "RandomForest",
        "horizon": 5,
        "style": "scalper",
        "params": {
            "n_estimators": 200,
            "max_depth": 15,
            "min_samples_split": 100,
            "min_samples_leaf": 50,
            "n_jobs": -1,
            "random_state": 42,
        }
    },
    {
        "name": "RF_DayTrader",
        "type": "RandomForest",
        "horizon": 72,
        "style": "day_trader",
        "params": {
            "n_estimators": 200,
            "max_depth": 20,
            "min_samples_split": 100,
            "min_samples_leaf": 50,
            "n_jobs": -1,
            "random_state": 42,
        }
    },
    {
        "name": "RF_SwingTrader",
        "type": "RandomForest",
        "horizon": 288,
        "style": "swing_trader",
        "params": {
            "n_estimators": 200,
            "max_depth": 25,
            "min_samples_split": 100,
            "min_samples_leaf": 50,
            "n_jobs": -1,
            "random_state": 42,
        }
    },
    {
        "name": "XGB_MultiStyle",
        "type": "XGBoost",
        "horizon": "multi",
        "style": "all",
        "params": {
            "n_estimators": 300,
            "max_depth": 10,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_jobs": -1,
            "random_state": 42,
            "tree_method": "hist",
        }
    },
    {
        "name": "LGB_Scalper",
        "type": "LightGBM",
        "horizon": 5,
        "style": "scalper",
        "params": {
            "n_estimators": 300,
            "max_depth": 15,
            "learning_rate": 0.05,
            "num_leaves": 128,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_jobs": -1,
            "random_state": 42,
            "verbose": -1,
        }
    },
    {
        "name": "LGB_DayTrader",
        "type": "LightGBM",
        "horizon": 72,
        "style": "day_trader",
        "params": {
            "n_estimators": 300,
            "max_depth": 20,
            "learning_rate": 0.05,
            "num_leaves": 256,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_jobs": -1,
            "random_state": 42,
            "verbose": -1,
        }
    },
    {
        "name": "LGB_SwingTrader",
        "type": "LightGBM",
        "horizon": 288,
        "style": "swing_trader",
        "params": {
            "n_estimators": 300,
            "max_depth": 25,
            "learning_rate": 0.05,
            "num_leaves": 512,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_jobs": -1,
            "random_state": 42,
            "verbose": -1,
        }
    },
    {
        "name": "XGB_Scalper_Tuned",
        "type": "XGBoost",
        "horizon": 5,
        "style": "scalper",
        "params": {
            "n_estimators": 400,
            "max_depth": 12,
            "learning_rate": 0.03,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "gamma": 0.1,
            "min_child_weight": 5,
            "n_jobs": -1,
            "random_state": 42,
            "tree_method": "hist",
        }
    },
    {
        "name": "XGB_DayTrader_Tuned",
        "type": "XGBoost",
        "horizon": 72,
        "style": "day_trader",
        "params": {
            "n_estimators": 400,
            "max_depth": 15,
            "learning_rate": 0.03,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "gamma": 0.1,
            "min_child_weight": 5,
            "n_jobs": -1,
            "random_state": 42,
            "tree_method": "hist",
        }
    },
    {
        "name": "Ensemble_AllStyles",
        "type": "Ensemble",
        "horizon": "multi",
        "style": "all",
        "params": {
            "voting": "soft",
            "n_jobs": -1,
        }
    },
]


# ============================================================
# DATA LOADING
# ============================================================

def load_and_prepare_data():
    """Load dataset and prepare features/targets."""
    print(f"[1/5] Loading dataset from {DATASET_PATH}")
    df = pl.read_parquet(DATASET_PATH)
    print(f"  Loaded {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    # Identify feature columns
    exclude_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {f"label_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    fwd_ret_cols = {f"fwd_ret_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    exclude_cols.update(label_cols)
    exclude_cols.update(fwd_ret_cols)

    feature_cols = [c for c in df.columns if c not in exclude_cols]
    print(f"  Feature columns: {len(feature_cols)}")

    # Drop rows with NaN in targets only, fill features with 0
    target_cols = [f"label_{h}b" for h in MULTI_HORIZONS]

    # Select columns
    df_select = df.select(["time"] + feature_cols + target_cols)

    # Drop rows where any target is null
    target_mask = pl.all_horizontal([pl.col(c).is_not_null() for c in target_cols])
    df_clean = df_select.filter(target_mask)

    # Fill remaining NaN in features with 0
    df_clean = df_clean.with_columns([
        pl.col(c).fill_null(0.0) for c in feature_cols
    ])

    print(f"  After dropping target NaN + filling feature NaN: {df_clean.shape[0]:,} rows")

    # Convert to numpy
    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = {h: df_clean[f"label_{h}b"].to_numpy().astype(np.int32) for h in MULTI_HORIZONS}
    times = df_clean["time"].to_numpy()

    # Train/test split (70/30 time-based)
    split_idx = int(len(X) * 0.7)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train = {h: y[h][:split_idx] for h in MULTI_HORIZONS}
    y_test = {h: y[h][split_idx:] for h in MULTI_HORIZONS}
    times_train, times_test = times[:split_idx], times[split_idx:]

    print(f"  Train: {X_train.shape[0]:,} rows")
    print(f"  Test: {X_test.shape[0]:,} rows")

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "times_train": times_train,
        "times_test": times_test,
        "feature_cols": feature_cols,
    }


# ============================================================
# MODEL TRAINING
# ============================================================

def train_single_model(config, data):
    """Train a single model."""
    print(f"\n[MODEL] {config['name']} ({config['style']}, horizon={config['horizon']})")

    start_time = time.time()

    # Select target
    if config["horizon"] == "multi":
        # Multi-horizon: use average label
        y_train = np.stack([data["y_train"][h] for h in MULTI_HORIZONS], axis=1).mean(axis=1).round().astype(np.int32)
        y_test = np.stack([data["y_test"][h] for h in MULTI_HORIZONS], axis=1).mean(axis=1).round().astype(np.int32)
    else:
        y_train = data["y_train"][config["horizon"]]
        y_test = data["y_test"][config["horizon"]]

    # Build model
    if config["type"] == "RandomForest":
        model = RandomForestClassifier(**config["params"])
    elif config["type"] == "XGBoost":
        model = xgb.XGBClassifier(**config["params"])
    elif config["type"] == "LightGBM":
        model = lgb.LGBMClassifier(**config["params"])
    elif config["type"] == "Ensemble":
        # Build ensemble from best models of each style
        rf_scalper = RandomForestClassifier(n_estimators=200, max_depth=15, n_jobs=-1, random_state=42)
        xgb_day = xgb.XGBClassifier(n_estimators=300, max_depth=15, learning_rate=0.05, n_jobs=-1, random_state=42)
        lgb_swing = lgb.LGBMClassifier(n_estimators=300, max_depth=25, learning_rate=0.05, n_jobs=-1, random_state=42, verbose=-1)

        model = VotingClassifier(
            estimators=[
                ("rf_scalper", rf_scalper),
                ("xgb_day", xgb_day),
                ("lgb_swing", lgb_swing),
            ],
            voting=config["params"]["voting"],
            n_jobs=config["params"]["n_jobs"],
        )
    else:
        raise ValueError(f"Unknown model type: {config['type']}")

    # Train
    print("  Training...")
    model.fit(data["X_train"], y_train)
    train_time = time.time() - start_time

    # Predict
    print("  Predicting...")
    y_pred_train = model.predict(data["X_train"])
    y_pred_test = model.predict(data["X_test"])

    if hasattr(model, "predict_proba"):
        y_proba_test = model.predict_proba(data["X_test"])
    else:
        y_proba_test = None

    # Evaluate
    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)
    test_prec = precision_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_rec = recall_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_f1 = f1_score(y_test, y_pred_test, average="weighted", zero_division=0)

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred_test)

    # Class distribution
    unique_train, counts_train = np.unique(y_train, return_counts=True)
    unique_test, counts_test = np.unique(y_test, return_counts=True)

    # Per-class accuracy
    per_class_acc = {}
    for cls in unique_test:
        mask = y_test == cls
        if mask.sum() > 0:
            per_class_acc[int(cls)] = accuracy_score(y_test[mask], y_pred_test[mask])

    # Feature importance (if available)
    if hasattr(model, "feature_importances_"):
        feat_imp = model.feature_importances_
        top_10_idx = np.argsort(feat_imp)[-10:][::-1]
        top_10_feats = [(data["feature_cols"][i], float(feat_imp[i])) for i in top_10_idx]
    else:
        top_10_feats = []

    print(f"  Train Acc: {train_acc:.4f}")
    print(f"  Test Acc: {test_acc:.4f}")
    print(f"  Test F1: {test_f1:.4f}")
    print(f"  Training time: {train_time:.1f}s")

    return {
        "config": config,
        "train_time": train_time,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "test_precision": test_prec,
        "test_recall": test_rec,
        "test_f1": test_f1,
        "confusion_matrix": cm.tolist(),
        "per_class_accuracy": per_class_acc,
        "class_distribution_train": dict(zip(unique_train.tolist(), counts_train.tolist())),
        "class_distribution_test": dict(zip(unique_test.tolist(), counts_test.tolist())),
        "top_10_features": top_10_feats,
        "model": model,
    }


# ============================================================
# REPORTING
# ============================================================

def generate_report(results, data):
    """Generate comprehensive report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[5/5] Generating report...")

    # Summary table
    summary = []
    for res in results:
        summary.append({
            "name": res["config"]["name"],
            "type": res["config"]["type"],
            "style": res["config"]["style"],
            "horizon": res["config"]["horizon"],
            "train_acc": f"{res['train_acc']:.4f}",
            "test_acc": f"{res['test_acc']:.4f}",
            "test_f1": f"{res['test_f1']:.4f}",
            "train_time": f"{res['train_time']:.1f}s",
        })

    # Sort by test F1
    summary_sorted = sorted(summary, key=lambda x: float(x["test_f1"]), reverse=True)

    # Print summary
    print("\n" + "="*80)
    print("MODEL PERFORMANCE SUMMARY (sorted by Test F1)")
    print("="*80)
    print(f"{'Rank':<5} {'Model':<25} {'Style':<15} {'Horizon':<10} {'Test Acc':<10} {'Test F1':<10} {'Time':<10}")
    print("-"*80)
    for i, row in enumerate(summary_sorted, 1):
        print(f"{i:<5} {row['name']:<25} {row['style']:<15} {str(row['horizon']):<10} {row['test_acc']:<10} {row['test_f1']:<10} {row['train_time']:<10}")
    print("="*80)

    # Best model per style
    print("\nBEST MODEL PER STYLE:")
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            print(f"  {style:<15}: {best['config']['name']} (F1={best['test_f1']:.4f})")

    # Save detailed report
    report_path = OUTPUT_DIR / "training_report.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dataset": str(DATASET_PATH),
            "train_samples": data["X_train"].shape[0],
            "test_samples": data["X_test"].shape[0],
            "num_features": data["X_train"].shape[1],
            "summary": summary_sorted,
            "detailed_results": [
                {
                    "name": r["config"]["name"],
                    "config": r["config"],
                    "train_time": r["train_time"],
                    "metrics": {
                        "train_acc": r["train_acc"],
                        "test_acc": r["test_acc"],
                        "test_precision": r["test_precision"],
                        "test_recall": r["test_recall"],
                        "test_f1": r["test_f1"],
                    },
                    "confusion_matrix": r["confusion_matrix"],
                    "per_class_accuracy": r["per_class_accuracy"],
                    "class_distribution_train": r["class_distribution_train"],
                    "class_distribution_test": r["class_distribution_test"],
                    "top_10_features": r["top_10_features"],
                }
                for r in results
            ]
        }, f, indent=2)

    print(f"\nDetailed report saved to: {report_path}")

    # Save best model per style
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            model_path = OUTPUT_DIR / f"best_{style}_model.json"

            # Save model metadata (actual model object too large for JSON)
            with open(model_path, "w") as f:
                json.dump({
                    "name": best["config"]["name"],
                    "config": best["config"],
                    "metrics": {
                        "train_acc": best["train_acc"],
                        "test_acc": best["test_acc"],
                        "test_f1": best["test_f1"],
                    },
                    "top_features": best["top_10_features"],
                }, f, indent=2)

            print(f"Best {style} model metadata saved to: {model_path}")

    return report_path


# ============================================================
# MAIN
# ============================================================

def main():
    print("="*80)
    print("MULTI-STYLE TRADING MODEL TRAINING")
    print("="*80)
    print(f"Training {len(MODEL_CONFIGS)} models across 3 trading styles")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Load data
    data = load_and_prepare_data()

    # Train models
    print("\n[2/5] Training models...")
    results = []
    for i, config in enumerate(MODEL_CONFIGS, 1):
        print(f"\n--- Model {i}/{len(MODEL_CONFIGS)} ---")
        res = train_single_model(config, data)
        results.append(res)

    # Generate report
    report_path = generate_report(results, data)

    print("\n" + "="*80)
    print("TRAINING COMPLETE")
    print("="*80)
    print(f"Trained {len(results)} models")
    print(f"Report: {report_path}")
    print()


if __name__ == "__main__":
    main()
