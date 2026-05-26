#!/usr/bin/env python3
"""
GPU-Accelerated Multi-Style Trading Model Training
Optimized for H200 - No Colab dependencies
"""

import json
import time
import warnings
import gc
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
import xgboost as xgb
from tqdm.auto import tqdm
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
sns.set_style('darkgrid')


def log(msg):
    """Timestamped logging."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


MODEL_CONFIGS = [
    {"name": "XGB_Scalper_Fast", "horizon": 5, "style": "scalper",
     "params": {"max_depth": 12, "eta": 0.05, "n_estimators": 500, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_Scalper_Deep", "horizon": 5, "style": "scalper",
     "params": {"max_depth": 18, "eta": 0.03, "n_estimators": 600, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_Scalper_Aggressive", "horizon": 5, "style": "scalper",
     "params": {"max_depth": 20, "eta": 0.02, "n_estimators": 700, "subsample": 0.95, "colsample_bytree": 0.95, "gamma": 0.05}},
    {"name": "XGB_DayTrader_Fast", "horizon": 72, "style": "day_trader",
     "params": {"max_depth": 15, "eta": 0.05, "n_estimators": 500, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_DayTrader_Deep", "horizon": 72, "style": "day_trader",
     "params": {"max_depth": 22, "eta": 0.03, "n_estimators": 700, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_DayTrader_Aggressive", "horizon": 72, "style": "day_trader",
     "params": {"max_depth": 25, "eta": 0.02, "n_estimators": 800, "subsample": 0.95, "colsample_bytree": 0.95, "gamma": 0.05}},
    {"name": "XGB_SwingTrader_Fast", "horizon": 288, "style": "swing_trader",
     "params": {"max_depth": 18, "eta": 0.05, "n_estimators": 500, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_SwingTrader_Deep", "horizon": 288, "style": "swing_trader",
     "params": {"max_depth": 28, "eta": 0.03, "n_estimators": 800, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_MultiStyle_Light", "horizon": "multi", "style": "all",
     "params": {"max_depth": 15, "eta": 0.05, "n_estimators": 600, "subsample": 0.9, "colsample_bytree": 0.9}},
    {"name": "XGB_MultiStyle_Deep", "horizon": "multi", "style": "all",
     "params": {"max_depth": 25, "eta": 0.03, "n_estimators": 900, "subsample": 0.95, "colsample_bytree": 0.95, "gamma": 0.05}},
]


def load_dataset(dataset_path):
    """Load and prepare dataset."""
    log("="*80)
    log("LOADING DATASET")
    log("="*80)

    load_start = time.time()

    log("Step 1/5: Reading parquet...")
    df = pl.read_parquet(dataset_path)
    log(f"  Loaded {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    log("Step 2/5: Identifying features...")
    exclude_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {f"label_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    fwd_ret_cols = {f"fwd_ret_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    exclude_cols.update(label_cols)
    exclude_cols.update(fwd_ret_cols)
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    log(f"  Features: {len(feature_cols)}")

    log("Step 3/5: Selecting columns...")
    target_cols = [f"label_{h}b" for h in [5, 72, 288]]
    df_select = df.select(["time"] + feature_cols + target_cols)
    del df
    gc.collect()

    log("Step 4/5: Cleaning NaN...")
    target_mask = pl.all_horizontal([pl.col(c).is_not_null() for c in target_cols])
    df_clean = df_select.filter(target_mask)
    del df_select
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])
    log(f"  After cleaning: {df_clean.shape[0]:,} rows")

    log("Step 5/5: Train/test split...")
    split_idx = int(len(df_clean) * 0.7)

    log("  Converting to numpy (float32 for H200)...")
    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = {h: df_clean[f"label_{h}b"].to_numpy().astype(np.int8) for h in [5, 72, 288]}
    del df_clean
    gc.collect()

    log("  Splitting...")
    X_train, X_test = X[:split_idx], X[split_idx:]
    del X
    y_train = {h: y[h][:split_idx] for h in [5, 72, 288]}
    y_test = {h: y[h][split_idx:] for h in [5, 72, 288]}
    del y
    gc.collect()

    load_time = time.time() - load_start

    log("")
    log(f"  Train: {X_train.shape[0]:,} samples")
    log(f"  Test:  {X_test.shape[0]:,} samples")
    log(f"  Features: {X_train.shape[1]}")
    log(f"  Memory: Train={X_train.nbytes/(1024**3):.2f}GB, Test={X_test.nbytes/(1024**3):.2f}GB")
    log(f"  Load time: {load_time:.1f}s")

    log("")
    log("Label Distribution:")
    for h in [5, 72, 288]:
        unique, counts = np.unique(y_train[h], return_counts=True)
        dist = {int(u): int(c) for u, c in zip(unique, counts)}
        log(f"  H{h:3d}: SELL={dist.get(-1,0):6,d} | HOLD={dist.get(0,0):6,d} | BUY={dist.get(1,0):6,d}")

    log("="*80)

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "feature_cols": feature_cols,
    }


def train_model(config, data, model_idx, total_models):
    """Train single model."""

    log("")
    log("#"*80)
    log(f"MODEL {model_idx}/{total_models}: {config['name']}")
    log("#"*80)
    log(f"  Style: {config['style']} | Horizon: {config['horizon']} bars")
    log(f"  Depth: {config['params']['max_depth']} | LR: {config['params']['eta']} | Trees: {config['params']['n_estimators']}")

    start_time = time.time()

    # Prepare targets (remap -1/0/1 -> 0/1/2)
    log("Preparing targets...")
    if config["horizon"] == "multi":
        y_train = np.round(np.stack([data["y_train"][h] for h in [5, 72, 288]], axis=1).mean(axis=1)).astype(np.int8) + 1
        y_test = np.round(np.stack([data["y_test"][h] for h in [5, 72, 288]], axis=1).mean(axis=1)).astype(np.int8) + 1
    else:
        y_train = data["y_train"][config["horizon"]].astype(np.int8) + 1
        y_test = data["y_test"][config["horizon"]].astype(np.int8) + 1

    unique, counts = np.unique(y_train, return_counts=True)
    log(f"  Class balance: SELL={counts[0]:,} | HOLD={counts[1]:,} | BUY={counts[2]:,}")

    # Class weights
    class_weights = len(y_train) / (len(unique) * counts)
    sample_weights = class_weights[y_train].astype(np.float32)

    # DMatrix
    log("Building DMatrix...")
    dtrain = xgb.DMatrix(data["X_train"], label=y_train, weight=sample_weights)
    dtest = xgb.DMatrix(data["X_test"], label=y_test)
    del sample_weights
    gc.collect()

    # Parameters (H200 optimized)
    params = config["params"].copy()
    n_est = params.pop("n_estimators", 500)
    params.update({
        "objective": "multi:softmax",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "tree_method": "gpu_hist",
        "device": "cuda",
        "max_bin": 512,  # H200 can handle more bins
        "verbosity": 0,
    })

    # Train
    log(f"Training {n_est} trees on GPU (early stop=50)...")
    train_losses = []
    test_losses = []

    with tqdm(total=n_est, desc=f"  {config['name'][:30]}", unit="tree", ncols=100) as pbar:
        def callback(env):
            train_losses.append(env.evaluation_result_list[0][1])
            test_losses.append(env.evaluation_result_list[1][1])
            pbar.update(1)
            if (env.iteration + 1) % 50 == 0:
                pbar.set_postfix({"loss": f"{test_losses[-1]:.4f}", "iter": env.iteration + 1})

        model = xgb.train(
            params,
            dtrain,
            num_boost_round=n_est,
            evals=[(dtrain, "train"), (dtest, "test")],
            early_stopping_rounds=50,
            verbose_eval=False,
            callbacks=[callback]
        )

    train_time = time.time() - start_time
    best_iter = model.best_iteration if hasattr(model, 'best_iteration') else n_est

    log(f"  Best iteration: {best_iter}/{n_est}")

    # Predictions
    log("Predicting...")
    y_pred_train = model.predict(dtrain)
    y_pred_test = model.predict(dtest)

    # Metrics
    train_acc = accuracy_score(y_train, y_pred_train)
    test_acc = accuracy_score(y_test, y_pred_test)
    test_prec = precision_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_rec = recall_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_f1 = f1_score(y_test, y_pred_test, average="weighted", zero_division=0)
    cm = confusion_matrix(y_test, y_pred_test)

    # Per-class accuracy
    per_class_acc = {}
    for cls_idx, cls_name in enumerate(["SELL", "HOLD", "BUY"]):
        mask = y_test == cls_idx
        if mask.sum() > 0:
            per_class_acc[cls_name] = accuracy_score(y_test[mask], y_pred_test[mask])

    # Feature importance
    top_10_feats = []
    try:
        feat_imp = model.get_score(importance_type="weight")
        top_10 = sorted(feat_imp.items(), key=lambda x: -x[1])[:10]
        for k, v in top_10:
            if k.startswith("f"):
                idx = int(k.replace("f", ""))
                if idx < len(data["feature_cols"]):
                    top_10_feats.append((data["feature_cols"][idx], float(v)))
    except:
        pass

    # Results
    log("="*80)
    log("RESULTS")
    log("="*80)
    log(f"  Time: {train_time:.1f}s ({train_time/60:.1f}min)")
    log(f"  Train Acc: {train_acc:.4f} | Test Acc: {test_acc:.4f}")
    log(f"  Test F1: {test_f1:.4f} | Prec: {test_prec:.4f} | Recall: {test_rec:.4f}")
    log(f"  Per-Class Acc: SELL={per_class_acc.get('SELL',0):.4f} | HOLD={per_class_acc.get('HOLD',0):.4f} | BUY={per_class_acc.get('BUY',0):.4f}")
    log("  Confusion Matrix:")
    log("         SELL    HOLD     BUY")
    for i, rn in enumerate(["SELL", "HOLD", "BUY"]):
        log(f"    {rn:5s} {cm[i][0]:6,d} {cm[i][1]:7,d} {cm[i][2]:7,d}")
    if top_10_feats:
        log("  Top 5 Features:")
        for j, (fn, fv) in enumerate(top_10_feats[:5], 1):
            log(f"    {j}. {fn[:45]:45s} {fv:6.0f}")
    log("="*80)

    # Cleanup
    del model, dtrain, dtest, y_train, y_test, y_pred_train, y_pred_test
    gc.collect()

    return {
        "config": config,
        "train_time": train_time,
        "best_iteration": best_iter,
        "train_acc": train_acc,
        "test_acc": test_acc,
        "test_precision": test_prec,
        "test_recall": test_rec,
        "test_f1": test_f1,
        "per_class_acc": per_class_acc,
        "confusion_matrix": cm.tolist(),
        "top_10_features": top_10_feats,
    }


def generate_visualization(summary_sorted, output_dir):
    """Generate comparison plots."""
    log("Generating visualizations...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    names = [s["name"].replace("XGB_", "") for s in summary_sorted]
    f1s = [s["test_f1"] for s in summary_sorted]
    colors = ['#FF6B6B' if s["style"] == 'scalper' else '#4ECDC4' if s["style"] == 'day_trader'
              else '#45B7D1' if s["style"] == 'swing_trader' else '#FFA07A' for s in summary_sorted]

    axes[0, 0].barh(names, f1s, color=colors)
    axes[0, 0].set_xlabel('Test F1')
    axes[0, 0].set_title('F1 Score by Model')
    axes[0, 0].grid(axis='x', alpha=0.3)

    train_accs = [s["train_acc"] for s in summary_sorted]
    test_accs = [s["test_acc"] for s in summary_sorted]
    x = np.arange(len(names))
    w = 0.35
    axes[0, 1].bar(x - w/2, train_accs, w, label='Train', alpha=0.8)
    axes[0, 1].bar(x + w/2, test_accs, w, label='Test', alpha=0.8)
    axes[0, 1].set_ylabel('Accuracy')
    axes[0, 1].set_title('Train vs Test Accuracy')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels([n[:15] for n in names], rotation=45, ha='right', fontsize=8)
    axes[0, 1].legend()
    axes[0, 1].grid(axis='y', alpha=0.3)

    times = [s["train_time"]/60 for s in summary_sorted]
    axes[1, 0].barh(names, times, color='#FDCB6E')
    axes[1, 0].set_xlabel('Time (min)')
    axes[1, 0].set_title('Training Time')
    axes[1, 0].grid(axis='x', alpha=0.3)

    precs = [s["test_precision"] for s in summary_sorted]
    recs = [s["test_recall"] for s in summary_sorted]
    axes[1, 1].scatter(precs, recs, s=150, c=f1s, cmap='viridis', alpha=0.7, edgecolors='black')
    axes[1, 1].set_xlabel('Precision')
    axes[1, 1].set_ylabel('Recall')
    axes[1, 1].set_title('Precision vs Recall')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    vis_path = output_dir / 'model_comparison.png'
    plt.savefig(vis_path, dpi=300, bbox_inches='tight')
    log(f"  ✓ Saved: {vis_path}")


def main():
    parser = argparse.ArgumentParser(description="Train multi-style trading models on GPU")
    parser.add_argument("dataset_path", type=str, help="Path to parquet dataset")
    parser.add_argument("--output-dir", type=str, default="./output", help="Output directory")
    args = parser.parse_args()

    # Setup
    log("="*80)
    log("INITIALIZATION")
    log("="*80)
    log(f"XGBoost: {xgb.__version__}")
    log(f"Polars:  {pl.__version__}")
    log(f"Dataset: {args.dataset_path}")
    log(f"Output:  {args.output_dir}")

    try:
        gpu_available = "cuda" in xgb.build_info()["BUILD_FLAGS"]
        log(f"GPU:     {gpu_available}")
    except:
        log("GPU:     Unknown")

    log("="*80)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    data = load_dataset(args.dataset_path)

    # Train models
    log("")
    log("="*80)
    log("TRAINING PIPELINE START")
    log("="*80)

    pipeline_start = time.time()
    results = []

    for i, config in enumerate(MODEL_CONFIGS, 1):
        res = train_model(config, data, i, len(MODEL_CONFIGS))
        results.append(res)

    pipeline_time = time.time() - pipeline_start

    log("")
    log("="*80)
    log("ALL MODELS TRAINED")
    log("="*80)
    log(f"  Total: {pipeline_time:.1f}s ({pipeline_time/60:.1f}min)")
    log(f"  Avg: {pipeline_time/len(results):.1f}s/model")
    log("="*80)

    # Summary
    summary = []
    for res in results:
        summary.append({
            "name": res["config"]["name"],
            "style": res["config"]["style"],
            "horizon": res["config"]["horizon"],
            "train_acc": res["train_acc"],
            "test_acc": res["test_acc"],
            "test_f1": res["test_f1"],
            "test_precision": res["test_precision"],
            "test_recall": res["test_recall"],
            "train_time": res["train_time"],
        })

    summary_sorted = sorted(summary, key=lambda x: x["test_f1"], reverse=True)

    log("")
    log("="*110)
    log("MODEL RANKING (by Test F1)")
    log("="*110)
    log(f"{'#':<3} {'Model':<35} {'Style':<12} {'H':<8} {'Acc':<7} {'F1':<7} {'Prec':<7} {'Rec':<7} {'Time':<8}")
    log("-"*110)
    for i, row in enumerate(summary_sorted, 1):
        log(f"{i:<3} {row['name']:<35} {row['style']:<12} {str(row['horizon']):<8} "
            f"{row['test_acc']:<7.4f} {row['test_f1']:<7.4f} {row['test_precision']:<7.4f} "
            f"{row['test_recall']:<7.4f} {row['train_time']:<8.1f}s")
    log("="*110)

    log("")
    log("BEST PER STYLE:")
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            log(f"  {style.upper():15s}: {best['config']['name']:35s} F1={best['test_f1']:.4f}")

    # Visualization
    generate_visualization(summary_sorted, output_dir)

    # Save report
    log("")
    log("Saving report...")
    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": args.dataset_path,
            "train_samples": int(data["X_train"].shape[0]),
            "test_samples": int(data["X_test"].shape[0]),
            "num_features": int(data["X_train"].shape[1]),
            "total_time": pipeline_time,
        },
        "summary": [
            {
                "rank": i,
                "name": row["name"],
                "style": row["style"],
                "horizon": row["horizon"],
                "train_acc": row["train_acc"],
                "test_acc": row["test_acc"],
                "test_f1": row["test_f1"],
                "test_precision": row["test_precision"],
                "test_recall": row["test_recall"],
                "train_time": row["train_time"],
            }
            for i, row in enumerate(summary_sorted, 1)
        ],
        "best_per_style": {},
        "detailed_results": results,
    }

    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            report["best_per_style"][style] = {
                "name": best["config"]["name"],
                "test_f1": best["test_f1"],
                "test_acc": best["test_acc"],
            }

    report_path = output_dir / "training_report_gpu.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"  ✓ Saved: {report_path}")
    log("")
    log("="*80)
    log("COMPLETE!")
    log("="*80)


if __name__ == "__main__":
    main()
