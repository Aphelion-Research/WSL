#!/usr/bin/env python3
"""
Single Model Training - Maximum Speed Local
"""

import json
import time
import gc
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
import xgboost as xgb
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def main():
    if len(sys.argv) < 2:
        print("Usage: python train_single_fast.py <dataset.parquet>")
        sys.exit(1)

    dataset_path = sys.argv[1]
    output_dir = Path("./output_single")
    output_dir.mkdir(exist_ok=True)

    log("="*80)
    log("SINGLE MODEL TRAINING - MAXIMUM SPEED")
    log("="*80)
    log(f"Dataset: {dataset_path}")

    # Load
    log("Loading dataset...")
    start = time.time()
    df = pl.read_parquet(dataset_path)
    log(f"  Loaded {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    # Features
    exclude_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {f"label_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    fwd_ret_cols = {f"fwd_ret_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    exclude_cols.update(label_cols)
    exclude_cols.update(fwd_ret_cols)
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    log(f"  Features: {len(feature_cols)}")

    # Select and clean
    target_col = "label_72b"  # Day trader
    df_select = df.select(feature_cols + [target_col])
    del df
    gc.collect()

    df_clean = df_select.filter(pl.col(target_col).is_not_null())
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])
    del df_select
    gc.collect()
    log(f"  Clean: {df_clean.shape[0]:,} rows")

    # Split
    split_idx = int(len(df_clean) * 0.7)
    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = df_clean[target_col].to_numpy().astype(np.int8) + 1  # Remap -1/0/1 -> 0/1/2
    del df_clean
    gc.collect()

    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    del X, y
    gc.collect()

    log(f"  Train: {X_train.shape[0]:,} samples")
    log(f"  Test:  {X_test.shape[0]:,} samples")
    log(f"  Load time: {time.time() - start:.1f}s")

    # Class weights
    unique, counts = np.unique(y_train, return_counts=True)
    class_weights = len(y_train) / (len(unique) * counts)
    sample_weights = class_weights[y_train].astype(np.float32)

    # DMatrix
    log("Building DMatrix...")
    dtrain = xgb.DMatrix(X_train, label=y_train, weight=sample_weights)
    dtest = xgb.DMatrix(X_test, label=y_test)
    del sample_weights
    gc.collect()

    # Train - FAST CONFIG
    log("Training XGBoost (fast config)...")
    train_start = time.time()

    params = {
        "objective": "multi:softmax",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "tree_method": "hist",
        "max_depth": 15,
        "eta": 0.05,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "max_bin": 256,
        "verbosity": 1,
        "nthread": -1,  # Use all cores
    }

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=300,  # Reduced from 700
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=30,
        verbose_eval=50
    )

    train_time = time.time() - train_start
    log(f"  Train time: {train_time:.1f}s")

    # Predict
    log("Evaluating...")
    y_pred_train = model.predict(dtrain)
    y_pred_test = model.predict(dtest)

    # Metrics
    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)
    test_prec = precision_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_rec = recall_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_f1 = f1_score(y_test, y_pred_test, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred_test)

    # Results
    log("="*80)
    log("RESULTS")
    log("="*80)
    log(f"  Model: DayTrader_Fast (H72, depth=15, lr=0.05, trees={model.best_iteration})")
    log(f"  Train Acc: {train_acc:.4f}")
    log(f"  Test Acc:  {test_acc:.4f}")
    log(f"  Test F1:   {test_f1:.4f}")
    log(f"  Test Prec: {test_prec:.4f}")
    log(f"  Test Rec:  {test_rec:.4f}")
    log("  Confusion Matrix:")
    log("         SELL    HOLD     BUY")
    for i, rn in enumerate(["SELL", "HOLD", "BUY"]):
        log(f"    {rn:5s} {cm[i][0]:6,d} {cm[i][1]:7,d} {cm[i][2]:7,d}")
    log("="*80)

    # Save
    result = {
        "model": "DayTrader_Fast",
        "horizon": 72,
        "train_time": train_time,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "test_f1": test_f1,
        "test_precision": test_prec,
        "test_recall": test_rec,
        "confusion_matrix": cm.tolist(),
        "timestamp": datetime.now().isoformat(),
    }

    result_path = output_dir / "result.json"
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)

    log(f"  Saved: {result_path}")
    log("DONE")

if __name__ == "__main__":
    main()
