#!/usr/bin/env python3
"""HYDRA-MoE: Jointly-trained Mixture-of-Experts for XAU/USD M5 directional prediction.

Full 3-phase training: initialization → alternating optimization → calibration → evaluation.
"""

import argparse
import sys
import time
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

warnings.filterwarnings("ignore")

# Add repo root to path
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from hydra.moe import HydraMoE, MoETrainer, MoEConfig
from hydra.moe.evaluation import MoEEvaluator

console = Console()


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Train HYDRA-MoE system")
    parser.add_argument(
        "--data",
        type=str,
        default="data/hydra_xauusd_m5_master_clean.parquet",
        help="Path to dataset parquet file",
    )
    parser.add_argument(
        "--n-experts",
        type=int,
        default=4,
        help="Number of experts (regimes)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: use only 50k bars for fast iteration",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output_hydra_moe",
        help="Output directory",
    )
    return parser.parse_args()


def setup_logging(output_dir: Path):
    """Configure loguru logger to file and stdout."""
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "training.log"

    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        log_path,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
    )
    logger.info(f"Logging to {log_path}")


def load_data(data_path: Path, debug: bool = False):
    """Load dataset and extract features/labels."""
    if not data_path.exists():
        console.print(f"[red]ERROR: Dataset not found: {data_path}[/red]")
        console.print("[yellow]Expected path: data/hydra_xauusd_m5_master_clean.parquet[/yellow]")
        sys.exit(1)

    logger.info(f"Loading dataset: {data_path}")
    df = pl.read_parquet(data_path)
    logger.info(f"  Raw shape: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    # Use label_72b (6-hour horizon)
    target_col = "label_72b"
    if target_col not in df.columns:
        console.print(f"[red]ERROR: Target column '{target_col}' not found[/red]")
        sys.exit(1)

    # Drop rows with missing labels
    df_clean = df.drop_nulls(subset=[target_col]).sort("time")
    logger.info(f"  After dropping nulls: {df_clean.shape[0]:,} rows")

    # Debug mode: use only 50k bars
    if debug:
        logger.warning("DEBUG MODE: Using only 50,000 bars")
        df_clean = df_clean.tail(50000)

    # Exclude base and label columns
    exclude = {
        "time", "timestamp", "open", "high", "low", "close", "volume", "tick_volume",
        "spread", "real_volume", "date", "datetime", "id", "index",
    }
    exclude.update({c for c in df_clean.columns if "label" in c or "fwd_ret" in c or "quality" in c})

    feature_cols = sorted([c for c in df_clean.columns if c not in exclude])
    logger.info(f"  Feature columns: {len(feature_cols)}")

    # Fill NaNs and clip
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])
    float_cols = [c for c in feature_cols if df_clean[c].dtype in (pl.Float32, pl.Float64)]
    df_clean = df_clean.with_columns([pl.col(c).clip(-1e6, 1e6) for c in float_cols])

    # Extract arrays
    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    y = df_clean[target_col].to_numpy().astype(np.int32)

    logger.info(f"  Final shape: {X.shape}")
    logger.info(f"  Label distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

    return X, y, feature_cols


def temporal_split(X, y, train_frac=0.60, val_frac=0.20):
    """Chronological train/val/oos split."""
    n = len(X)
    train_end = int(train_frac * n)
    val_end = int((train_frac + val_frac) * n)

    idx_train = np.arange(0, train_end)
    idx_val = np.arange(train_end, val_end)
    idx_oos = np.arange(val_end, n)

    logger.info(f"Split: train={len(idx_train):,} | val={len(idx_val):,} | oos={len(idx_oos):,}")

    return (
        X[idx_train], y[idx_train],
        X[idx_val], y[idx_val],
        X[idx_oos], y[idx_oos],
    )


def print_summary_table(results: dict):
    """Print formatted summary table to console."""
    console.print("\n")
    console.print("═" * 70, style="bold green")
    console.print("              HYDRA-MoE Evaluation Summary", style="bold green")
    console.print("═" * 70, style="bold green")

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="yellow")

    # Core metrics
    oos_auc = results["oos"]["auc"]
    val_auc = results["val"]["auc"]
    table.add_row("OOS AUC (MoE)", f"{oos_auc:.4f}")
    table.add_row("Val AUC (MoE)", f"{val_auc:.4f}")

    # Baseline comparison
    vs_sb = results.get("vs_single_brain", {})
    if "single_brain_oos_auc" in vs_sb:
        baseline_auc = vs_sb["single_brain_oos_auc"]
        improvement = vs_sb["improvement"]
        pvalue = vs_sb["delong_pvalue"]
        significant = vs_sb["significant"]

        table.add_row("OOS AUC (Single-Brain)", f"{baseline_auc:.4f}")
        table.add_row("Improvement", f"+{improvement:.4f}" if improvement >= 0 else f"{improvement:.4f}")
        table.add_row("DeLong p-value", f"{pvalue:.4f}")
        table.add_row("Significant", "YES" if significant else "NO")

    # Calibration
    ece = results["calibration"]["oos_ece"]
    brier = results["calibration"]["oos_brier"]
    table.add_row("ECE (calibration)", f"{ece:.4f}")
    table.add_row("Brier Score", f"{brier:.4f}")

    # Gated metrics
    gated_60 = results["gated"].get("gate_0.60", {})
    if gated_60:
        table.add_row("Gated Accuracy (0.60)", f"{gated_60['gated_accuracy']:.4f}")
        table.add_row("Trade Rate (0.60)", f"{gated_60['trade_rate']*100:.1f}%")

    # Expert routing
    table.add_row("", "")
    table.add_row("Expert Routing (OOS):", "")
    for k, expert_data in enumerate(results["expert_breakdown"].values()):
        pct = expert_data.get("pct", 0)
        table.add_row(f"  Expert {k}", f"{pct:.1f}%")

    console.print(table)

    # Recommendation
    rec = results["production_recommendation"]
    rec_color = {"DEPLOY": "green", "RESEARCH": "yellow", "REJECT": "red"}.get(rec, "white")
    console.print("═" * 70, style="bold green")
    console.print(f"  RECOMMENDATION: {rec}", style=f"bold {rec_color}")
    console.print("═" * 70, style="bold green")
    console.print("\n")


def main():
    """Main training entrypoint."""
    args = parse_args()
    output_dir = Path(args.output)
    setup_logging(output_dir)

    console.print(Panel.fit(
        "[bold]HYDRA-MoE Training[/bold]\n"
        "Jointly-trained Mixture-of-Experts\n"
        "3-phase alternating optimization",
        style="bold green",
    ))

    start_time = time.time()

    # Load data
    logger.info("═══ LOAD DATA ═══")
    X, y, feature_cols = load_data(Path(args.data), debug=args.debug)

    # Split
    logger.info("═══ TEMPORAL SPLIT ═══")
    X_train, y_train, X_val, y_val, X_oos, y_oos = temporal_split(X, y)

    # Initialize MoE
    logger.info("═══ INITIALIZE MOE ═══")
    config = MoEConfig(
        n_experts=args.n_experts,
        router_hidden=[128, 64],
        router_dropout=0.2,
        router_lr=1e-3,
        router_weight_decay=1e-4,
        router_temperature_start=1.0,
        router_temperature_end=0.5,
        lambda_entropy=0.01,
        n_alternating_rounds=5,
        router_steps_per_round=500,
        router_batch_size=4096,
        n_estimators=2000,
        early_stopping_rounds=100,
        gate_upper=0.60,
        gate_lower=0.40,
        random_state=42,
    )

    moe = HydraMoE(
        n_experts=config.n_experts,
        router_hidden=config.router_hidden,
        router_dropout=config.router_dropout,
        router_temperature=config.router_temperature_start,
        n_estimators=config.n_estimators,
        early_stopping_rounds=config.early_stopping_rounds,
        gate_upper=config.gate_upper,
        gate_lower=config.gate_lower,
    )

    moe.initialize(feature_cols)

    # Train
    logger.info("═══ TRAIN ═══")
    trainer = MoETrainer(moe, config, output_dir=str(output_dir))
    training_results = trainer.train(X_train, y_train, X_val, y_val, X_oos, y_oos)

    logger.info(f"Training time: {training_results.training_time_seconds:.1f}s")

    # Save model
    logger.info("═══ SAVE MODEL ═══")
    moe.save(str(output_dir))

    # Load baseline for comparison
    baseline_proba = None
    baseline_path = Path("output_hydra_day/oos_proba_day.npy")
    if baseline_path.exists():
        logger.info(f"Loading baseline from {baseline_path}")
        baseline_proba = np.load(baseline_path)
        # Align length if needed
        if len(baseline_proba) != len(y_oos):
            logger.warning(f"Baseline length mismatch: {len(baseline_proba)} vs {len(y_oos)}")
            if len(baseline_proba) > len(y_oos):
                baseline_proba = baseline_proba[-len(y_oos):]
            else:
                baseline_proba = None

    # Evaluation
    logger.info("═══ EVALUATE ═══")
    evaluator = MoEEvaluator(moe, str(output_dir))
    results = evaluator.full_evaluation(X_oos, y_oos, X_val, y_val, baseline_proba)

    # Print summary
    print_summary_table(results)

    # Final message
    elapsed = time.time() - start_time
    console.print(Panel(
        f"[bold green]HYDRA-MoE training complete[/bold green]\n\n"
        f"Time: {elapsed:.1f}s\n"
        f"Results: {output_dir}/metrics/results_moe.json\n"
        f"Models:  {output_dir}/models/\n"
        f"Plots:   {output_dir}/plots/",
        style="bold green",
    ))

    logger.info("Done.")


if __name__ == "__main__":
    main()
