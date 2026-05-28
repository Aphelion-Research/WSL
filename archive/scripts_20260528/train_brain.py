#!/usr/bin/env python3
"""Train a single Hydra brain (scalp/day/swing) with NO LEAKAGE.

Usage:
    python scripts/train_brain.py scalp
    python scripts/train_brain.py day
    python scripts/train_brain.py swing

Each brain uses different target label horizons:
    scalp → label_12b  (1hr on M5, fast reversals)
    day   → label_72b  (6hr on M5, intraday trends)
    swing → label_288b (24hr on M5, multi-day moves)

Same feature matrix for all. Temporal 70/15/15 split.
Saves: model, OOS probabilities, metrics JSON.
"""
import sys
import json
import time
import pickle
from pathlib import Path
from datetime import datetime

import numpy as np
import polars as pl
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, log_loss
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

BRAIN_CONFIG = {
    "scalp": {
        "target": "label_12b",
        "horizon": "1hr (12 bars M5)",
        "xgb_params": {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "max_depth": 7,
            "learning_rate": 0.03,
            "subsample": 0.8,
            "colsample_bytree": 0.6,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "min_child_weight": 10,
            "random_state": 42,
            "verbosity": 0,
        },
        "n_rounds": 1000,
        "early_stop": 50,
    },
    "day": {
        "target": "label_72b",
        "horizon": "6hr (72 bars M5)",
        "xgb_params": {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "max_depth": 6,
            "learning_rate": 0.02,
            "subsample": 0.8,
            "colsample_bytree": 0.7,
            "reg_alpha": 0.05,
            "reg_lambda": 1.5,
            "min_child_weight": 20,
            "random_state": 42,
            "verbosity": 0,
        },
        "n_rounds": 1500,
        "early_stop": 80,
    },
    "swing": {
        "target": "label_288b",
        "horizon": "24hr (288 bars M5)",
        "xgb_params": {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "tree_method": "hist",
            "max_depth": 5,
            "learning_rate": 0.01,
            "subsample": 0.7,
            "colsample_bytree": 0.5,
            "reg_alpha": 0.2,
            "reg_lambda": 2.0,
            "min_child_weight": 50,
            "random_state": 42,
            "verbosity": 0,
        },
        "n_rounds": 2000,
        "early_stop": 100,
    },
}


def get_feature_cols(df: pl.DataFrame) -> list[str]:
    """Return clean feature columns — NO leakage."""
    exclude = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"}
    label_cols = {c for c in df.columns if "label" in c.lower()}
    fwd_cols = {c for c in df.columns if "fwd_ret" in c or "fwd_" in c or "future" in c}
    exclude.update(label_cols)
    exclude.update(fwd_cols)
    return [c for c in df.columns if c not in exclude]


def train_brain(brain_name: str):
    if brain_name not in BRAIN_CONFIG:
        console.print(f"[red]Unknown brain: {brain_name}. Use: scalp, day, swing[/red]")
        sys.exit(1)

    cfg = BRAIN_CONFIG[brain_name]
    target_col = cfg["target"]
    output_dir = Path(f"./output_hydra_{brain_name}")
    output_dir.mkdir(exist_ok=True)

    console.print(Panel.fit(
        f"HYDRA {brain_name.upper()} BRAIN\n"
        f"Target: {target_col} ({cfg['horizon']})\n"
        f"Rounds: {cfg['n_rounds']} | Early stop: {cfg['early_stop']}",
        style="bold green"
    ))

    # Load
    console.print("\n[bold cyan]LOAD[/bold cyan]")
    dataset_path = "data/hydra_xauusd_m5_master_clean.parquet"
    df = pl.read_parquet(dataset_path)
    console.print(f"  {df.shape[0]:,} rows x {df.shape[1]:,} cols")

    # Features (no leakage)
    feature_cols = get_feature_cols(df)
    console.print(f"  {len(feature_cols)} features (excluded labels+fwd)")

    # Check target exists
    if target_col not in df.columns:
        console.print(f"[red]Target {target_col} not in dataset![/red]")
        sys.exit(1)

    # Prep
    console.print("\n[bold magenta]PREP[/bold magenta]")
    df_clean = df.select([target_col, "time"] + feature_cols).drop_nulls(subset=[target_col])
    df_clean = df_clean.sort("time")
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])

    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = df_clean[target_col].to_numpy().astype(np.int32)
    console.print(f"  {X.shape[0]:,} samples x {X.shape[1]} features")

    classes, counts = np.unique(y, return_counts=True)
    console.print(f"  Target dist: {dict(zip(classes.tolist(), counts.tolist()))}")

    # Temporal split: 70% train / 15% val / 15% OOS
    console.print("\n[bold blue]TEMPORAL SPLIT (70/15/15)[/bold blue]")
    n = len(X)
    train_end = int(0.70 * n)
    val_end = int(0.85 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:val_end], y[train_end:val_end]
    X_oos, y_oos = X[val_end:], y[val_end:]

    console.print(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | OOS: {len(X_oos):,}")

    # Train XGBoost
    console.print(f"\n[bold red]TRAINING ({cfg['n_rounds']} rounds max)[/bold red]")
    import xgboost as xgb

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    doos = xgb.DMatrix(X_oos, label=y_oos)

    start = time.time()
    model = xgb.train(
        cfg["xgb_params"],
        dtrain,
        num_boost_round=cfg["n_rounds"],
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=cfg["early_stop"],
        verbose_eval=50,
    )
    train_time = time.time() - start
    console.print(f"\n  Trained in {train_time:.1f}s (best iter: {model.best_iteration})")

    # Predict on OOS
    console.print("\n[bold green]OOS EVALUATION[/bold green]")
    y_proba_oos = model.predict(doos)
    y_pred_oos = (y_proba_oos > 0.5).astype(int)

    # Also predict on val for calibration
    y_proba_val = model.predict(dval)
    y_pred_val = (y_proba_val > 0.5).astype(int)

    # Metrics
    def compute_metrics(y_true, y_pred, y_proba):
        return {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "f1": float(f1_score(y_true, y_pred, average="binary")),
            "precision": float(precision_score(y_true, y_pred, average="binary", zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, average="binary")),
            "auc_roc": float(roc_auc_score(y_true, y_proba)),
            "log_loss": float(log_loss(y_true, y_proba)),
        }

    oos_metrics = compute_metrics(y_oos, y_pred_oos, y_proba_oos)
    val_metrics = compute_metrics(y_val, y_pred_val, y_proba_val)

    # Results table
    table = Table(title=f"HYDRA {brain_name.upper()} — OOS Results", box=box.DOUBLE_EDGE)
    table.add_column("Metric", style="cyan")
    table.add_column("Val", style="yellow")
    table.add_column("OOS", style="magenta")
    for key in oos_metrics:
        table.add_row(key, f"{val_metrics[key]:.4f}", f"{oos_metrics[key]:.4f}")
    table.add_row("", "", "")
    table.add_row("Leak check", "", "PASS" if oos_metrics["accuracy"] < 0.65 else "SUSPICIOUS" if oos_metrics["accuracy"] < 0.80 else "LEAK")
    console.print(table)

    # Feature importance
    importance = model.get_score(importance_type="gain")
    top_features = sorted(importance.items(), key=lambda x: -x[1])[:15]
    console.print("\n[bold cyan]TOP 15 FEATURES[/bold cyan]")
    for i, (fname, gain) in enumerate(top_features, 1):
        console.print(f"  {i:2d}. {fname}: {gain:.1f}")

    # Save everything
    console.print("\n[bold magenta]SAVE[/bold magenta]")

    model_path = output_dir / f"model_{brain_name}.json"
    model.save_model(str(model_path))

    # Save OOS probabilities (needed for mega-merge)
    np.save(output_dir / f"oos_proba_{brain_name}.npy", y_proba_oos)
    np.save(output_dir / f"oos_labels_{brain_name}.npy", y_oos)
    np.save(output_dir / f"val_proba_{brain_name}.npy", y_proba_val)
    np.save(output_dir / f"val_labels_{brain_name}.npy", y_val)

    results = {
        "brain": brain_name,
        "target": target_col,
        "horizon": cfg["horizon"],
        "dataset": dataset_path,
        "n_features": len(feature_cols),
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "oos_samples": len(X_oos),
        "train_time_s": train_time,
        "best_round": model.best_iteration,
        "val_metrics": val_metrics,
        "oos_metrics": oos_metrics,
        "top_features": [(f, float(g)) for f, g in top_features],
        "timestamp": datetime.now().isoformat(),
    }

    results_path = output_dir / f"results_{brain_name}.json"
    results_path.write_text(json.dumps(results, indent=2))

    console.print(f"  Model: {model_path}")
    console.print(f"  Results: {results_path}")
    console.print(f"  OOS proba: {output_dir}/oos_proba_{brain_name}.npy")

    console.print(f"\n[bold green]HYDRA {brain_name.upper()} COMPLETE[/bold green]")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python scripts/train_brain.py <scalp|day|swing>[/red]")
        sys.exit(1)
    train_brain(sys.argv[1])
