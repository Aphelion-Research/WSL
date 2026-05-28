#!/usr/bin/env python3
"""Standalone evaluation script for saved HYDRA-MoE model."""

import argparse
import sys
from pathlib import Path

import numpy as np
import polars as pl
from loguru import logger
from rich.console import Console

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from hydra.moe import HydraMoE
from hydra.moe.evaluation import MoEEvaluator

console = Console()


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Evaluate saved HYDRA-MoE model")
    parser.add_argument(
        "--model-dir",
        type=str,
        default="output_hydra_moe",
        help="Path to model directory",
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data/hydra_xauusd_m5_master_clean.parquet",
        help="Path to dataset parquet file",
    )
    parser.add_argument(
        "--baseline-proba",
        type=str,
        default="output_hydra_day/oos_proba_day.npy",
        help="Path to baseline OOS proba for comparison",
    )
    return parser.parse_args()


def main():
    """Main evaluation entrypoint."""
    args = parse_args()

    console.print("\n[bold]═══ HYDRA-MoE Evaluation ═══[/bold]\n")

    # Load model
    console.print(f"Loading model from {args.model_dir}...")
    moe = HydraMoE.load(args.model_dir)

    # Load data
    console.print(f"Loading dataset: {args.data}")
    df = pl.read_parquet(args.data)

    target_col = "label_72b"
    df_clean = df.drop_nulls(subset=[target_col]).sort("time")

    # Extract features (same exclusion logic as training)
    exclude = {
        "time", "timestamp", "open", "high", "low", "close", "volume", "tick_volume",
        "spread", "real_volume", "date", "datetime", "id", "index",
    }
    exclude.update({c for c in df_clean.columns if "label" in c or "fwd_ret" in c or "quality" in c})
    feature_cols = sorted([c for c in df_clean.columns if c not in exclude])

    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])
    float_cols = [c for c in feature_cols if df_clean[c].dtype in (pl.Float32, pl.Float64)]
    df_clean = df_clean.with_columns([pl.col(c).clip(-1e6, 1e6) for c in float_cols])

    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = df_clean[target_col].to_numpy().astype(np.int32)

    # Split (same as training)
    n = len(X)
    train_end = int(0.60 * n)
    val_end = int(0.80 * n)

    X_val = X[train_end:val_end]
    y_val = y[train_end:val_end]
    X_oos = X[val_end:]
    y_oos = y[val_end:]

    console.print(f"  Val: {len(X_val):,} | OOS: {len(X_oos):,}")

    # Load baseline
    baseline_proba = None
    if Path(args.baseline_proba).exists():
        console.print(f"Loading baseline from {args.baseline_proba}")
        baseline_proba = np.load(args.baseline_proba)
        if len(baseline_proba) > len(y_oos):
            baseline_proba = baseline_proba[-len(y_oos):]
        elif len(baseline_proba) < len(y_oos):
            console.print("[yellow]Baseline length mismatch, skipping comparison[/yellow]")
            baseline_proba = None

    # Evaluate
    console.print("\n[bold cyan]Running full evaluation...[/bold cyan]")
    evaluator = MoEEvaluator(moe, args.model_dir)
    results = evaluator.full_evaluation(X_oos, y_oos, X_val, y_val, baseline_proba)

    # Print summary
    console.print("\n[bold green]═══ Results ═══[/bold green]")
    console.print(f"  OOS AUC:     {results['oos']['auc']:.4f}")
    console.print(f"  Val AUC:     {results['val']['auc']:.4f}")
    console.print(f"  OOS ECE:     {results['calibration']['oos_ece']:.4f}")
    console.print(f"  Recommendation: {results['production_recommendation']}")

    console.print(f"\n[bold]Results saved: {args.model_dir}/metrics/results_moe.json[/bold]\n")


if __name__ == "__main__":
    main()
