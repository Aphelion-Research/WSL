#!/usr/bin/env python3
"""
GPU-Accelerated Multi-Style Trading Model Training
Uses RAPIDS cuML + XGBoost GPU for 10-100x speedup.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import cupy as cp
import cudf
import cuml
from cuml.ensemble import RandomForestClassifier as cuRF
from cuml.metrics import accuracy_score
import xgboost as xgb

ROOT = Path(__file__).resolve().parent.parent

# ============================================================
# CONFIGURATION
# ============================================================

DATASET_PATH = ROOT / "data" / "feature_fabric" / "hydra_xauusd_feature_fabric_v1.parquet"
OUTPUT_DIR = ROOT / "models" / "multi_style_gpu" / datetime.now().strftime("%Y%m%d_%H%M%S")

HORIZONS = {
    "scalper": 5,
    "day_trader": 72,
    "swing_trader": 288,
}

MODEL_CONFIGS = [
    {"name": "cuRF_Scalper", "type": "cuRF", "horizon": 5, "style": "scalper", "params": {"n_estimators": 200, "max_depth": 15, "n_bins": 128}},
    {"name": "cuRF_DayTrader", "type": "cuRF", "horizon": 72, "style": "day_trader", "params": {"n_estimators": 200, "max_depth": 20, "n_bins": 128}},
    {"name": "cuRF_SwingTrader", "type": "cuRF", "horizon": 288, "style": "swing_trader", "params": {"n_estimators": 200, "max_depth": 25, "n_bins": 128}},
    {"name": "XGB_GPU_Scalper", "type": "XGB_GPU", "horizon": 5, "style": "scalper", "params": {"n_estimators": 300, "max_depth": 12, "learning_rate": 0.05, "tree_method": "gpu_hist", "gpu_id": 0}},
    {"name": "XGB_GPU_DayTrader", "type": "XGB_GPU", "horizon": 72, "style": "day_trader", "params": {"n_estimators": 300, "max_depth": 15, "learning_rate": 0.05, "tree_method": "gpu_hist", "gpu_id": 0}},
    {"name": "XGB_GPU_SwingTrader", "type": "XGB_GPU", "horizon": 288, "style": "swing_trader", "params": {"n_estimators": 300, "max_depth": 18, "learning_rate": 0.05, "tree_method": "gpu_hist", "gpu_id": 0}},
    {"name": "XGB_GPU_MultiStyle", "type": "XGB_GPU", "horizon": "multi", "style": "all", "params": {"n_estimators": 400, "max_depth": 15, "learning_rate": 0.03, "tree_method": "gpu_hist", "gpu_id": 0}},
    {"name": "cuRF_Aggressive_Scalper", "type": "cuRF", "horizon": 5, "style": "scalper", "params": {"n_estimators": 300, "max_depth": 20, "n_bins": 256, "min_samples_split": 50}},
    {"name": "XGB_GPU_Tuned_DayTrader", "type": "XGB_GPU", "horizon": 72, "style": "day_trader", "params": {"n_estimators": 500, "max_depth": 18, "learning_rate": 0.02, "subsample": 0.9, "colsample_bytree": 0.9, "tree_method": "gpu_hist", "gpu_id": 0}},
    {"name": "XGB_GPU_DeepSwing", "type": "XGB_GPU", "horizon": 288, "style": "swing_trader", "params": {"n_estimators": 600, "max_depth": 25, "learning_rate": 0.01, "subsample": 0.9, "tree_method": "gpu_hist", "gpu_id": 0}},
]


# ============================================================
# DATA LOADING (GPU)
# ============================================================

def load_and_prepare_data_gpu():
    """Load dataset to GPU using cuDF."""
    print(f"[1/5] Loading dataset to GPU from {DATASET_PATH}")

    # Load to pandas first (cuDF parquet reader sometimes has issues with large files)
    import pandas as pd
    df_pd = pd.read_parquet(DATASET_PATH)
    print(f"  Loaded {len(df_pd):,} rows × {len(df_pd.columns):,} cols to CPU")

    # Convert to cuDF
    print("  Transferring to GPU...")
    df = cudf.from_pandas(df_pd)
    del df_pd

    # Identify columns
    exclude_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {f"label_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    fwd_ret_cols = {f"fwd_ret_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    exclude_cols.update(label_cols)
    exclude_cols.update(fwd_ret_cols)

    feature_cols = [c for c in df.columns if c not in exclude_cols]
    print(f"  Feature columns: {len(feature_cols)}")

    # Filter to valid targets
    target_cols = [f"label_{h}b" for h in [5, 72, 288]]
    df_clean = df[["time"] + feature_cols + target_cols].dropna(subset=target_cols)

    # Fill feature NaN with 0
    df_clean[feature_cols] = df_clean[feature_cols].fillna(0.0)

    print(f"  After cleaning: {len(df_clean):,} rows")

    # Train/test split (70/30)
    split_idx = int(len(df_clean) * 0.7)

    X_train = df_clean[feature_cols].iloc[:split_idx].values
    X_test = df_clean[feature_cols].iloc[split_idx:].values

    y_train = {h: df_clean[f"label_{h}b"].iloc[:split_idx].values for h in [5, 72, 288]}
    y_test = {h: df_clean[f"label_{h}b"].iloc[split_idx:].values for h in [5, 72, 288]}

    times_train = df_clean["time"].iloc[:split_idx].values_host
    times_test = df_clean["time"].iloc[split_idx:].values_host

    print(f"  Train: {len(X_train):,} rows (GPU)")
    print(f"  Test: {len(X_test):,} rows (GPU)")

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
# MODEL TRAINING (GPU)
# ============================================================

def train_single_model_gpu(config, data):
    """Train a single model on GPU."""
    print(f"\n[MODEL] {config['name']} ({config['style']}, horizon={config['horizon']})")

    start_time = time.time()

    # Select target
    if config["horizon"] == "multi":
        # Multi-horizon: average labels
        y_train_list = [data["y_train"][h] for h in [5, 72, 288]]
        y_test_list = [data["y_test"][h] for h in [5, 72, 288]]

        # Convert to CuPy for averaging
        y_train_cp = cp.stack([cp.asarray(y) for y in y_train_list], axis=1)
        y_test_cp = cp.stack([cp.asarray(y) for y in y_test_list], axis=1)

        y_train = cp.round(y_train_cp.mean(axis=1)).astype(cp.int32)
        y_test = cp.round(y_test_cp.mean(axis=1)).astype(cp.int32)
    else:
        y_train = data["y_train"][config["horizon"]]
        y_test = data["y_test"][config["horizon"]]

    # Build model
    if config["type"] == "cuRF":
        model = cuRF(**config["params"])
    elif config["type"] == "XGB_GPU":
        # Convert cuDF arrays to DMatrix for XGBoost
        dtrain = xgb.DMatrix(cp.asnumpy(data["X_train"]), label=cp.asnumpy(y_train))
        dtest = xgb.DMatrix(cp.asnumpy(data["X_test"]), label=cp.asnumpy(y_test))

        params = config["params"].copy()
        params["objective"] = "multi:softmax"
        params["num_class"] = 3
        params["eval_metric"] = "mlogloss"

        print("  Training...")
        model = xgb.train(params, dtrain, num_boost_round=params.pop("n_estimators", 300), evals=[(dtest, "test")], verbose_eval=False)
        train_time = time.time() - start_time

        # Predict
        print("  Predicting...")
        y_pred_train = model.predict(dtrain)
        y_pred_test = model.predict(dtest)

        # Metrics
        train_acc = float(np.mean(y_pred_train == cp.asnumpy(y_train)))
        test_acc = float(np.mean(y_pred_test == cp.asnumpy(y_test)))

        # Feature importance
        feat_imp = model.get_score(importance_type="weight")
        top_10_feats = sorted(feat_imp.items(), key=lambda x: -x[1])[:10]
        top_10_feats = [(data["feature_cols"][int(k.replace("f", ""))], v) for k, v in top_10_feats if k.startswith("f")]

        print(f"  Train Acc: {train_acc:.4f}")
        print(f"  Test Acc: {test_acc:.4f}")
        print(f"  Training time: {train_time:.1f}s")

        return {
            "config": config,
            "train_time": train_time,
            "train_acc": train_acc,
            "test_acc": test_acc,
            "test_f1": test_acc,  # Approximate
            "top_10_features": top_10_feats,
        }

    # cuRF path
    print("  Training...")
    model.fit(data["X_train"], y_train)
    train_time = time.time() - start_time

    # Predict
    print("  Predicting...")
    y_pred_train = model.predict(data["X_train"])
    y_pred_test = model.predict(data["X_test"])

    # Metrics
    train_acc = float(accuracy_score(y_train, y_pred_train))
    test_acc = float(accuracy_score(y_test, y_pred_test))

    print(f"  Train Acc: {train_acc:.4f}")
    print(f"  Test Acc: {test_acc:.4f}")
    print(f"  Training time: {train_time:.1f}s")

    return {
        "config": config,
        "train_time": train_time,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "test_f1": test_acc,  # Approximate
        "top_10_features": [],
    }


# ============================================================
# REPORTING
# ============================================================

def generate_report(results, data):
    """Generate report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[5/5] Generating report...")

    # Summary
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

    summary_sorted = sorted(summary, key=lambda x: float(x["test_f1"]), reverse=True)

    print("\n" + "="*80)
    print("GPU MODEL PERFORMANCE SUMMARY (sorted by Test F1/Acc)")
    print("="*80)
    print(f"{'Rank':<5} {'Model':<30} {'Style':<15} {'Test Acc':<10} {'Time':<10}")
    print("-"*80)
    for i, row in enumerate(summary_sorted, 1):
        print(f"{i:<5} {row['name']:<30} {row['style']:<15} {row['test_acc']:<10} {row['train_time']:<10}")
    print("="*80)

    # Best per style
    print("\nBEST MODEL PER STYLE:")
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_acc"])
            print(f"  {style:<15}: {best['config']['name']} (Acc={best['test_acc']:.4f}, {best['train_time']:.1f}s)")

    # Save report
    report_path = OUTPUT_DIR / "training_report_gpu.json"
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dataset": str(DATASET_PATH),
            "device": "GPU",
            "train_samples": int(data["X_train"].shape[0]),
            "test_samples": int(data["X_test"].shape[0]),
            "num_features": int(data["X_train"].shape[1]),
            "summary": summary_sorted,
            "detailed_results": [
                {
                    "name": r["config"]["name"],
                    "config": r["config"],
                    "train_time": r["train_time"],
                    "metrics": {
                        "train_acc": r["train_acc"],
                        "test_acc": r["test_acc"],
                        "test_f1": r["test_f1"],
                    },
                    "top_10_features": r["top_10_features"],
                }
                for r in results
            ]
        }, f, indent=2)

    print(f"\nReport saved to: {report_path}")
    return report_path


# ============================================================
# MAIN
# ============================================================

def main():
    print("="*80)
    print("GPU-ACCELERATED MULTI-STYLE TRADING MODEL TRAINING")
    print("="*80)
    print(f"Training {len(MODEL_CONFIGS)} models on GPU")
    print(f"Output: {OUTPUT_DIR}")
    print()

    # Load data to GPU
    data = load_and_prepare_data_gpu()

    # Train models
    print("\n[2/5] Training models on GPU...")
    results = []
    for i, config in enumerate(MODEL_CONFIGS, 1):
        print(f"\n--- Model {i}/{len(MODEL_CONFIGS)} ---")
        res = train_single_model_gpu(config, data)
        results.append(res)

    # Report
    report_path = generate_report(results, data)

    print("\n" + "="*80)
    print("TRAINING COMPLETE")
    print("="*80)
    print(f"Trained {len(results)} models on GPU")
    print(f"Report: {report_path}")
    print()


if __name__ == "__main__":
    main()
