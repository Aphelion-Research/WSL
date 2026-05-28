#!/usr/bin/env python3
"""
Fast Multi-Style Trading Model Training
XGBoost GPU + parallelized training.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
import multiprocessing as mp

import numpy as np
import polars as pl
import xgboost as xgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

ROOT = Path(__file__).resolve().parent.parent

DATASET_PATH = ROOT / "data" / "feature_fabric" / "hydra_xauusd_feature_fabric_v1.parquet"
OUTPUT_DIR = ROOT / "models" / "multi_style_fast" / datetime.now().strftime("%Y%m%d_%H%M%S")

MODEL_CONFIGS = [
    {"name": "XGB_Scalper", "horizon": 5, "style": "scalper", "params": {"max_depth": 12, "eta": 0.05, "n_estimators": 300, "tree_method": "hist"}},
    {"name": "XGB_DayTrader", "horizon": 72, "style": "day_trader", "params": {"max_depth": 15, "eta": 0.05, "n_estimators": 300, "tree_method": "hist"}},
    {"name": "XGB_SwingTrader", "horizon": 288, "style": "swing_trader", "params": {"max_depth": 18, "eta": 0.05, "n_estimators": 300, "tree_method": "hist"}},
    {"name": "XGB_Scalper_Deep", "horizon": 5, "style": "scalper", "params": {"max_depth": 15, "eta": 0.03, "n_estimators": 200, "tree_method": "hist"}},
    {"name": "XGB_DayTrader_Deep", "horizon": 72, "style": "day_trader", "params": {"max_depth": 20, "eta": 0.03, "n_estimators": 200, "tree_method": "hist"}},
    {"name": "XGB_SwingTrader_Deep", "horizon": 288, "style": "swing_trader", "params": {"max_depth": 25, "eta": 0.03, "n_estimators": 200, "tree_method": "hist"}},
    {"name": "XGB_MultiStyle_Light", "horizon": "multi", "style": "all", "params": {"max_depth": 12, "eta": 0.05, "n_estimators": 150, "tree_method": "hist"}},
    {"name": "XGB_MultiStyle_Deep", "horizon": "multi", "style": "all", "params": {"max_depth": 18, "eta": 0.03, "n_estimators": 250, "tree_method": "hist"}},
    {"name": "XGB_Scalper_Aggressive", "horizon": 5, "style": "scalper", "params": {"max_depth": 18, "eta": 0.02, "n_estimators": 250, "subsample": 0.9, "colsample_bytree": 0.9, "tree_method": "hist"}},
    {"name": "XGB_SwingTrader_Conservative", "horizon": 288, "style": "swing_trader", "params": {"max_depth": 15, "eta": 0.01, "n_estimators": 300, "subsample": 0.8, "colsample_bytree": 0.8, "tree_method": "hist"}},
]


def load_and_prepare_data():
    """Load dataset."""
    print(f"[1/4] Loading dataset from {DATASET_PATH}")
    df = pl.read_parquet(DATASET_PATH)
    print(f"  Loaded {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    # Features
    exclude_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {f"label_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    fwd_ret_cols = {f"fwd_ret_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    exclude_cols.update(label_cols)
    exclude_cols.update(fwd_ret_cols)

    feature_cols = [c for c in df.columns if c not in exclude_cols]
    print(f"  Features: {len(feature_cols)}")

    # Clean
    target_cols = [f"label_{h}b" for h in [5, 72, 288]]
    df_select = df.select(["time"] + feature_cols + target_cols)
    target_mask = pl.all_horizontal([pl.col(c).is_not_null() for c in target_cols])
    df_clean = df_select.filter(target_mask)
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])

    print(f"  After cleaning: {df_clean.shape[0]:,} rows")

    # Split
    split_idx = int(len(df_clean) * 0.7)
    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = {h: df_clean[f"label_{h}b"].to_numpy().astype(np.int32) for h in [5, 72, 288]}

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train = {h: y[h][:split_idx] for h in [5, 72, 288]}
    y_test = {h: y[h][split_idx:] for h in [5, 72, 288]}

    print(f"  Train: {X_train.shape[0]:,}, Test: {X_test.shape[0]:,}")

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "feature_cols": feature_cols,
    }


def train_single_model(config, data):
    """Train single XGBoost model."""
    print(f"\n[MODEL] {config['name']} ({config['style']}, horizon={config['horizon']})")

    start_time = time.time()

    # Target (remap -1/0/1 → 0/1/2 for XGBoost)
    if config["horizon"] == "multi":
        y_train = np.round(np.stack([data["y_train"][h] for h in [5, 72, 288]], axis=1).mean(axis=1)).astype(np.int32) + 1
        y_test = np.round(np.stack([data["y_test"][h] for h in [5, 72, 288]], axis=1).mean(axis=1)).astype(np.int32) + 1
    else:
        y_train = data["y_train"][config["horizon"]].astype(np.int32) + 1
        y_test = data["y_test"][config["horizon"]].astype(np.int32) + 1

    # Build DMatrix
    dtrain = xgb.DMatrix(data["X_train"], label=y_train)
    dtest = xgb.DMatrix(data["X_test"], label=y_test)

    # Train
    params = config["params"].copy()
    n_est = params.pop("n_estimators", 300)
    params.update({
        "objective": "multi:softmax",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "verbosity": 0,
    })

    print(f"  Training {n_est} trees (device={params.get('device', 'cpu')})...")
    model = xgb.train(params, dtrain, num_boost_round=n_est, evals=[(dtest, "test")], verbose_eval=False)
    train_time = time.time() - start_time

    # Predict
    y_pred_train = model.predict(dtrain)
    y_pred_test = model.predict(dtest)

    # Metrics
    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)
    test_f1 = f1_score(y_test, y_pred_test, average="weighted", zero_division=0)

    print(f"  Train Acc: {train_acc:.4f}, Test Acc: {test_acc:.4f}, Test F1: {test_f1:.4f}, Time: {train_time:.1f}s")

    # Feature importance
    try:
        feat_imp = model.get_score(importance_type="weight")
        top_10 = sorted(feat_imp.items(), key=lambda x: -x[1])[:10]
        top_10_feats = [(data["feature_cols"][int(k.replace("f", ""))], v) for k, v in top_10 if k.startswith("f") and int(k.replace("f", "")) < len(data["feature_cols"])]
    except:
        top_10_feats = []

    return {
        "config": config,
        "train_time": train_time,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "test_f1": test_f1,
        "top_10_features": top_10_feats,
    }


def generate_report(results, data):
    """Generate report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = []
    for res in results:
        summary.append({
            "name": res["config"]["name"],
            "style": res["config"]["style"],
            "horizon": res["config"]["horizon"],
            "train_acc": f"{res['train_acc']:.4f}",
            "test_acc": f"{res['test_acc']:.4f}",
            "test_f1": f"{res['test_f1']:.4f}",
            "train_time": f"{res['train_time']:.1f}s",
        })

    summary_sorted = sorted(summary, key=lambda x: float(x["test_f1"]), reverse=True)

    print("\n" + "="*90)
    print("MULTI-STYLE MODEL PERFORMANCE (sorted by Test F1)")
    print("="*90)
    print(f"{'Rank':<5} {'Model':<35} {'Style':<15} {'Test Acc':<10} {'Test F1':<10} {'Time':<8}")
    print("-"*90)
    for i, row in enumerate(summary_sorted, 1):
        print(f"{i:<5} {row['name']:<35} {row['style']:<15} {row['test_acc']:<10} {row['test_f1']:<10} {row['train_time']:<8}")
    print("="*90)

    print("\nBEST MODEL PER STYLE:")
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            print(f"  {style:<15}: {best['config']['name']:<35} F1={best['test_f1']:.4f}, Time={best['train_time']:.1f}s")

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
                    "metrics": {"train_acc": r["train_acc"], "test_acc": r["test_acc"], "test_f1": r["test_f1"]},
                    "train_time": r["train_time"],
                    "top_10_features": r["top_10_features"],
                }
                for r in results
            ]
        }, f, indent=2)

    print(f"\nReport saved: {report_path}")
    return report_path


def main():
    print("="*90)
    print("FAST MULTI-STYLE TRADING MODEL TRAINING (XGBoost GPU)")
    print("="*90)
    print(f"Models: {len(MODEL_CONFIGS)}")
    print(f"Output: {OUTPUT_DIR}\n")

    data = load_and_prepare_data()

    print("\n[2/4] Training models...")
    results = []
    for i, config in enumerate(MODEL_CONFIGS, 1):
        print(f"\n--- Model {i}/{len(MODEL_CONFIGS)} ---")
        res = train_single_model(config, data)
        results.append(res)

    print("\n[3/4] Generating report...")
    report_path = generate_report(results, data)

    print("\n" + "="*90)
    print("TRAINING COMPLETE")
    print("="*90)
    print(f"Trained {len(results)} models")
    print(f"Total time: {sum(r['train_time'] for r in results):.1f}s")
    print(f"Report: {report_path}\n")


if __name__ == "__main__":
    main()
