#!/usr/bin/env python3
"""
100 Model Training on 8x L4 GPUs + 96 vCPUs + 384GB RAM
Maximum power utilization - sequential training with live logging
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
import threading

import numpy as np
import polars as pl
import xgboost as xgb
from tqdm.auto import tqdm
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
sns.set_style('darkgrid')


def log(msg):
    """Live logging with timestamp and flush."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ============================================================================
# 100 MODEL CONFIGURATIONS - EXTREME VARIETY
# ============================================================================

def generate_model_configs():
    """Generate 100 diverse model configurations."""
    configs = []
    model_id = 1

    # Scalper models (5 bars) - 30 models
    horizons_scalper = [5]
    for depth in [10, 12, 15, 18, 20, 22, 25, 28, 30, 35]:
        for lr in [0.01, 0.03, 0.05]:
            configs.append({
                "id": model_id,
                "name": f"Scalper_D{depth}_LR{int(lr*100)}",
                "horizon": 5,
                "style": "scalper",
                "params": {
                    "max_depth": depth,
                    "eta": lr,
                    "n_estimators": 600 + depth * 10,
                    "subsample": 0.9,
                    "colsample_bytree": 0.9,
                    "max_bin": 512,
                }
            })
            model_id += 1

    # Day trader models (72 bars) - 35 models
    for depth in [12, 15, 18, 20, 22, 25, 28, 30, 32, 35, 38]:
        for lr in [0.01, 0.02, 0.03]:
            configs.append({
                "id": model_id,
                "name": f"DayTrader_D{depth}_LR{int(lr*100)}",
                "horizon": 72,
                "style": "day_trader",
                "params": {
                    "max_depth": depth,
                    "eta": lr,
                    "n_estimators": 700 + depth * 10,
                    "subsample": 0.9,
                    "colsample_bytree": 0.85,
                    "max_bin": 512,
                    "gamma": 0.05 if depth > 25 else 0,
                }
            })
            model_id += 1
            if len(configs) >= 65:
                break
        if len(configs) >= 65:
            break

    # Swing trader models (288 bars) - 25 models
    for depth in [15, 18, 20, 25, 28, 30, 32, 35, 38, 40]:
        for lr in [0.01, 0.02, 0.03]:
            if len(configs) >= 90:
                break
            configs.append({
                "id": model_id,
                "name": f"SwingTrader_D{depth}_LR{int(lr*100)}",
                "horizon": 288,
                "style": "swing_trader",
                "params": {
                    "max_depth": depth,
                    "eta": lr,
                    "n_estimators": 800 + depth * 10,
                    "subsample": 0.85,
                    "colsample_bytree": 0.8,
                    "max_bin": 512,
                    "gamma": 0.1 if depth > 30 else 0.05,
                }
            })
            model_id += 1
        if len(configs) >= 90:
            break

    # Multi-style models - 10 models
    for depth in [15, 18, 20, 25, 28, 30, 32, 35, 38, 40]:
        configs.append({
            "id": model_id,
            "name": f"MultiStyle_D{depth}",
            "horizon": "multi",
            "style": "all",
            "params": {
                "max_depth": depth,
                "eta": 0.03,
                "n_estimators": 900 + depth * 10,
                "subsample": 0.9,
                "colsample_bytree": 0.9,
                "max_bin": 512,
            }
        })
        model_id += 1
        if len(configs) >= 100:
            break

    return configs[:100]


MODEL_CONFIGS = generate_model_configs()


# ============================================================================
# GPU MONITORING
# ============================================================================

class GPUMonitor:
    """Monitor all 8 GPUs."""
    def __init__(self):
        self.running = False
        self.stats = {i: [] for i in range(8)}
        self.thread = None

        try:
            import GPUtil
            self.GPUtil = GPUtil
            self.available = True
        except:
            self.available = False

    def _loop(self):
        while self.running:
            if self.available:
                try:
                    gpus = self.GPUtil.getGPUs()
                    for gpu in gpus:
                        self.stats[gpu.id].append({
                            'load': gpu.load * 100,
                            'memory': (gpu.memoryUsed / gpu.memoryTotal) * 100
                        })
                except:
                    pass
            time.sleep(2)

    def start(self):
        if self.available and not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def get_stats(self):
        if not self.available:
            return None
        summary = {}
        for gpu_id, data in self.stats.items():
            if data:
                summary[f"GPU{gpu_id}"] = {
                    'load_avg': np.mean([d['load'] for d in data]),
                    'mem_avg': np.mean([d['memory'] for d in data]),
                }
        return summary

    def clear(self):
        self.stats = {i: [] for i in range(8)}


gpu_monitor = GPUMonitor()


# ============================================================================
# DATA LOADING
# ============================================================================

def load_dataset(dataset_path):
    """Load dataset with maximum efficiency."""
    log("="*80)
    log("LOADING DATASET - MAXIMUM POWER MODE")
    log("="*80)

    load_start = time.time()

    log("Step 1/5: Reading parquet (using all CPU cores)...")
    df = pl.read_parquet(dataset_path)
    log(f"  ✓ {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    log("Step 2/5: Feature identification...")
    exclude_cols = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {f"label_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    fwd_ret_cols = {f"fwd_ret_{h}b" for h in [5, 10, 20, 72, 144, 288]}
    exclude_cols.update(label_cols)
    exclude_cols.update(fwd_ret_cols)
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    log(f"  ✓ {len(feature_cols)} features")

    log("Step 3/5: Column selection...")
    target_cols = [f"label_{h}b" for h in [5, 72, 288]]
    df_select = df.select(["time"] + feature_cols + target_cols)
    del df
    gc.collect()

    log("Step 4/5: NaN handling...")
    target_mask = pl.all_horizontal([pl.col(c).is_not_null() for c in target_cols])
    df_clean = df_select.filter(target_mask)
    del df_select
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])
    log(f"  ✓ {df_clean.shape[0]:,} rows after cleaning")

    log("Step 5/5: Train/test split (70/30)...")
    split_idx = int(len(df_clean) * 0.7)

    # Full float32 for maximum GPU utilization
    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = {h: df_clean[f"label_{h}b"].to_numpy().astype(np.int8) for h in [5, 72, 288]}
    del df_clean
    gc.collect()

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
        log(f"  H{h:3d}: SELL={dist.get(-1,0):7,d} | HOLD={dist.get(0,0):7,d} | BUY={dist.get(1,0):7,d}")

    log("="*80)

    return {
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "feature_cols": feature_cols,
    }


# ============================================================================
# TRAINING FUNCTION (OPTIMIZED FOR 8x L4)
# ============================================================================

def train_model(config, data, model_idx, total_models, gpu_monitor):
    """Train single model with maximum GPU utilization."""

    log("")
    log("#"*80)
    log(f"MODEL {model_idx}/{total_models} [ID={config['id']}]: {config['name']}")
    log("#"*80)
    log(f"  Style: {config['style']} | Horizon: {config['horizon']} bars")
    log(f"  Depth: {config['params']['max_depth']} | LR: {config['params']['eta']} | Trees: {config['params']['n_estimators']}")

    # Assign GPU (round-robin across 8 GPUs)
    gpu_id = (config['id'] - 1) % 8
    log(f"  Assigned GPU: {gpu_id}/8")

    start_time = time.time()
    gpu_monitor.clear()
    gpu_monitor.start()

    # Prepare targets
    if config["horizon"] == "multi":
        y_train = np.round(np.stack([data["y_train"][h] for h in [5, 72, 288]], axis=1).mean(axis=1)).astype(np.int8) + 1
        y_test = np.round(np.stack([data["y_test"][h] for h in [5, 72, 288]], axis=1).mean(axis=1)).astype(np.int8) + 1
    else:
        y_train = data["y_train"][config["horizon"]].astype(np.int8) + 1
        y_test = data["y_test"][config["horizon"]].astype(np.int8) + 1

    # Class weights
    unique, counts = np.unique(y_train, return_counts=True)
    class_weights = len(y_train) / (len(unique) * counts)
    sample_weights = class_weights[y_train].astype(np.float32)

    # DMatrix
    dtrain = xgb.DMatrix(data["X_train"], label=y_train, weight=sample_weights)
    dtest = xgb.DMatrix(data["X_test"], label=y_test)
    del sample_weights
    gc.collect()

    # Parameters - MAXIMUM POWER
    params = config["params"].copy()
    n_est = params.pop("n_estimators", 600)
    params.update({
        "objective": "multi:softmax",
        "num_class": 3,
        "eval_metric": "mlogloss",
        "tree_method": "gpu_hist",
        "device": f"cuda:{gpu_id}",
        "max_bin": 512,  # L4 can handle this
        "gpu_id": gpu_id,
        "verbosity": 0,
        "nthread": 12,  # 96 vCPUs / 8 GPUs = 12 threads per model
    })

    # Train with live progress
    log(f"  Training {n_est} trees on GPU {gpu_id}...")
    train_losses = []
    test_losses = []

    # XGBoost 3.2.0+ callback
    class ProgressCallback(xgb.callback.TrainingCallback):
        def __init__(self, pbar):
            self.pbar = pbar

        def after_iteration(self, model, epoch, evals_log):
            train_losses.append(evals_log['train']['mlogloss'][-1])
            test_losses.append(evals_log['test']['mlogloss'][-1])
            self.pbar.update(1)
            if (epoch + 1) % 50 == 0:
                self.pbar.set_postfix({
                    "loss": f"{test_losses[-1]:.4f}",
                    "iter": epoch + 1,
                })
            return False

    pbar = tqdm(total=n_est, desc=f"  GPU{gpu_id} {config['name'][:25]}", unit="tree", ncols=100, leave=False)

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=n_est,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=50,
        verbose_eval=False,
        callbacks=[ProgressCallback(pbar)]
    )

    pbar.close()

    gpu_monitor.stop()
    train_time = time.time() - start_time
    best_iter = model.best_iteration if hasattr(model, 'best_iteration') else n_est

    # Predictions
    y_pred_test = model.predict(dtest)

    # Metrics
    test_acc = accuracy_score(y_test, y_pred_test)
    test_prec = precision_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_rec = recall_score(y_test, y_pred_test, average="weighted", zero_division=0)
    test_f1 = f1_score(y_test, y_pred_test, average="weighted", zero_division=0)

    # GPU stats
    gpu_stats = gpu_monitor.get_stats()

    # Results
    log(f"  ✓ Complete: {train_time:.1f}s | Best iter: {best_iter}/{n_est}")
    log(f"    Test Acc: {test_acc:.4f} | F1: {test_f1:.4f} | Prec: {test_prec:.4f} | Rec: {test_rec:.4f}")
    if gpu_stats and f"GPU{gpu_id}" in gpu_stats:
        log(f"    GPU{gpu_id}: {gpu_stats[f'GPU{gpu_id}']['load_avg']:.0f}% load, {gpu_stats[f'GPU{gpu_id}']['mem_avg']:.0f}% VRAM")

    # Cleanup
    del model, dtrain, dtest, y_train, y_test, y_pred_test
    gc.collect()

    return {
        "id": config["id"],
        "name": config["name"],
        "config": config,
        "gpu_id": gpu_id,
        "train_time": train_time,
        "best_iteration": best_iter,
        "test_acc": test_acc,
        "test_precision": test_prec,
        "test_recall": test_rec,
        "test_f1": test_f1,
        "gpu_stats": gpu_stats,
    }


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Train 100 models on 8x L4 GPUs")
    parser.add_argument("dataset_path", type=str, help="Path to parquet dataset")
    parser.add_argument("--output-dir", type=str, default="./output_100models", help="Output directory")
    args = parser.parse_args()

    # Setup
    log("="*80)
    log("100 MODEL TRAINING - 8x L4 GPUs - MAXIMUM POWER")
    log("="*80)
    log(f"XGBoost: {xgb.__version__}")
    log(f"Models:  {len(MODEL_CONFIGS)}")
    log(f"GPUs:    8x L4")
    log(f"vCPUs:   96")
    log(f"RAM:     384GB")
    log(f"Dataset: {args.dataset_path}")
    log(f"Output:  {args.output_dir}")

    try:
        gpu_available = "cuda" in xgb.build_info()["BUILD_FLAGS"]
        log(f"CUDA:    {gpu_available}")
    except:
        log("CUDA:    Unknown")

    log("="*80)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    data = load_dataset(args.dataset_path)

    # Train all 100 models
    log("")
    log("="*80)
    log("TRAINING PIPELINE - 100 MODELS SEQUENTIAL")
    log("="*80)

    pipeline_start = time.time()
    results = []

    for i, config in enumerate(MODEL_CONFIGS, 1):
        res = train_model(config, data, i, len(MODEL_CONFIGS), gpu_monitor)
        results.append(res)

        # Incremental save
        with open(output_dir / f"result_{config['id']:03d}.json", "w") as f:
            json.dump(res, f, indent=2)

        # Progress summary every 10 models
        if i % 10 == 0:
            completed_f1s = [r["test_f1"] for r in results]
            log("")
            log(f"  Progress: {i}/{len(MODEL_CONFIGS)} models complete")
            log(f"  Avg F1: {np.mean(completed_f1s):.4f} | Best F1: {np.max(completed_f1s):.4f}")
            log(f"  Avg time: {np.mean([r['train_time'] for r in results]):.1f}s/model")
            log("")

    pipeline_time = time.time() - pipeline_start

    log("")
    log("="*80)
    log("ALL 100 MODELS COMPLETE")
    log("="*80)
    log(f"  Total time: {pipeline_time:.1f}s ({pipeline_time/60:.1f}min)")
    log(f"  Avg time:   {pipeline_time/len(results):.1f}s/model")
    log(f"  Throughput: {len(results)/(pipeline_time/3600):.1f} models/hour")
    log("="*80)

    # Summary
    summary = sorted(results, key=lambda x: x["test_f1"], reverse=True)

    log("")
    log("="*100)
    log("TOP 20 MODELS (by Test F1)")
    log("="*100)
    log(f"{'Rank':<5} {'ID':<5} {'Name':<40} {'Style':<12} {'Acc':<7} {'F1':<7} {'Time':<8}")
    log("-"*100)
    for i, res in enumerate(summary[:20], 1):
        log(f"{i:<5} {res['id']:<5} {res['name']:<40} {res['config']['style']:<12} "
            f"{res['test_acc']:<7.4f} {res['test_f1']:<7.4f} {res['train_time']:<8.1f}s")
    log("="*100)

    log("")
    log("BEST PER STYLE:")
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            log(f"  {style.upper():15s}: {best['name']:40s} F1={best['test_f1']:.4f} (ID={best['id']})")

    # Stats
    log("")
    log("STATISTICS:")
    f1_scores = [r["test_f1"] for r in results]
    log(f"  F1 Mean:  {np.mean(f1_scores):.4f}")
    log(f"  F1 Std:   {np.std(f1_scores):.4f}")
    log(f"  F1 Min:   {np.min(f1_scores):.4f}")
    log(f"  F1 Max:   {np.max(f1_scores):.4f}")

    # Save comprehensive report
    log("")
    log("Saving comprehensive report...")

    report = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "dataset": args.dataset_path,
            "train_samples": int(data["X_train"].shape[0]),
            "test_samples": int(data["X_test"].shape[0]),
            "num_features": int(data["X_train"].shape[1]),
            "total_time": pipeline_time,
            "num_models": len(results),
            "hardware": "8x L4 GPUs, 96 vCPUs, 384GB RAM",
        },
        "top_20": [
            {
                "rank": i,
                "id": res["id"],
                "name": res["name"],
                "style": res["config"]["style"],
                "horizon": res["config"]["horizon"],
                "test_acc": res["test_acc"],
                "test_f1": res["test_f1"],
                "test_precision": res["test_precision"],
                "test_recall": res["test_recall"],
                "train_time": res["train_time"],
                "gpu_id": res["gpu_id"],
            }
            for i, res in enumerate(summary[:20], 1)
        ],
        "best_per_style": {},
        "statistics": {
            "f1_mean": float(np.mean(f1_scores)),
            "f1_std": float(np.std(f1_scores)),
            "f1_min": float(np.min(f1_scores)),
            "f1_max": float(np.max(f1_scores)),
        },
        "all_results": results,
    }

    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r for r in results if r["config"]["style"] == style]
        if style_results:
            best = max(style_results, key=lambda x: x["test_f1"])
            report["best_per_style"][style] = {
                "id": best["id"],
                "name": best["name"],
                "test_f1": best["test_f1"],
                "test_acc": best["test_acc"],
            }

    report_path = output_dir / "training_report_100models.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    log(f"  ✓ Saved: {report_path}")

    # Visualization
    log("")
    log("Generating visualizations...")

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Top 30 F1 scores
    top_30 = summary[:30]
    names = [f"{r['id']}:{r['name'][:20]}" for r in top_30]
    f1s = [r["test_f1"] for r in top_30]
    colors = ['#FF6B6B' if r["config"]["style"] == 'scalper' else '#4ECDC4' if r["config"]["style"] == 'day_trader'
              else '#45B7D1' if r["config"]["style"] == 'swing_trader' else '#FFA07A' for r in top_30]

    axes[0, 0].barh(names, f1s, color=colors)
    axes[0, 0].set_xlabel('Test F1')
    axes[0, 0].set_title('Top 30 Models by F1')
    axes[0, 0].grid(axis='x', alpha=0.3)

    # F1 distribution
    axes[0, 1].hist(f1_scores, bins=30, color='#4ECDC4', alpha=0.7, edgecolor='black')
    axes[0, 1].axvline(np.mean(f1_scores), color='red', linestyle='--', label=f'Mean: {np.mean(f1_scores):.4f}')
    axes[0, 1].set_xlabel('Test F1')
    axes[0, 1].set_ylabel('Count')
    axes[0, 1].set_title('F1 Score Distribution (100 models)')
    axes[0, 1].legend()
    axes[0, 1].grid(alpha=0.3)

    # Training time vs F1
    times = [r["train_time"] for r in results]
    axes[1, 0].scatter(times, f1_scores, alpha=0.6, s=50, c=f1_scores, cmap='viridis')
    axes[1, 0].set_xlabel('Training Time (s)')
    axes[1, 0].set_ylabel('Test F1')
    axes[1, 0].set_title('Training Time vs F1 Score')
    axes[1, 0].grid(alpha=0.3)

    # Style comparison
    style_data = {}
    for style in ["scalper", "day_trader", "swing_trader", "all"]:
        style_results = [r["test_f1"] for r in results if r["config"]["style"] == style]
        if style_results:
            style_data[style] = style_results

    axes[1, 1].boxplot(style_data.values(), labels=[s.replace('_', ' ').title() for s in style_data.keys()])
    axes[1, 1].set_ylabel('Test F1')
    axes[1, 1].set_title('F1 Score by Trading Style')
    axes[1, 1].grid(axis='y', alpha=0.3)

    plt.tight_layout()
    vis_path = output_dir / '100models_analysis.png'
    plt.savefig(vis_path, dpi=300, bbox_inches='tight')
    log(f"  ✓ Saved: {vis_path}")

    log("")
    log("="*80)
    log("COMPLETE! All outputs in: {output_dir}")
    log("="*80)


if __name__ == "__main__":
    main()
