#!/usr/bin/env python3
"""Shadow comparison: HYDRA-MoE vs Single-Brain Day side-by-side."""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score, accuracy_score
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Compare MoE vs baseline predictions")
    parser.add_argument("--moe-proba", type=str, required=True, help="Path to MoE OOS proba .npy")
    parser.add_argument("--baseline-proba", type=str, required=True, help="Path to baseline OOS proba .npy")
    parser.add_argument("--labels", type=str, help="Path to OOS labels .npy (optional)")
    parser.add_argument("--gate", type=float, default=0.60, help="Confidence gate threshold")
    return parser.parse_args()


def main():
    """Main comparison entrypoint."""
    args = parse_args()

    console.print("\n[bold]═══ SHADOW COMPARISON: MoE vs Baseline ═══[/bold]\n")

    # Load predictions
    moe_proba = np.load(args.moe_proba)
    baseline_proba = np.load(args.baseline_proba)

    console.print(f"  MoE proba shape: {moe_proba.shape}")
    console.print(f"  Baseline proba shape: {baseline_proba.shape}")

    # Align lengths
    n = min(len(moe_proba), len(baseline_proba))
    moe_proba = moe_proba[-n:]
    baseline_proba = baseline_proba[-n:]

    console.print(f"  Aligned length: {n:,}\n")

    # Load labels if provided
    y_true = None
    if args.labels:
        y_true = np.load(args.labels)
        y_true = y_true[-n:]

    # Convert to signals
    gate = args.gate
    moe_signal = ((moe_proba > gate) | (moe_proba < (1 - gate))).astype(int)
    baseline_signal = ((baseline_proba > gate) | (baseline_proba < (1 - gate))).astype(int)

    moe_direction = (moe_proba >= 0.5).astype(int)
    baseline_direction = (baseline_proba >= 0.5).astype(int)

    # Agreement rate
    agreement = (moe_direction == baseline_direction).mean()
    console.print(f"[cyan]Agreement Rate:[/cyan] {agreement*100:.2f}%")

    # Trade signal overlap
    both_trade = (moe_signal & baseline_signal).sum()
    moe_only = (moe_signal & ~baseline_signal).sum()
    baseline_only = (~moe_signal & baseline_signal).sum()
    neither = (~moe_signal & ~baseline_signal).sum()

    console.print(f"[cyan]Trade Signal Overlap:[/cyan]")
    console.print(f"  Both trade:      {both_trade:,} ({both_trade/n*100:.1f}%)")
    console.print(f"  MoE only:        {moe_only:,} ({moe_only/n*100:.1f}%)")
    console.print(f"  Baseline only:   {baseline_only:,} ({baseline_only/n*100:.1f}%)")
    console.print(f"  Neither:         {neither:,} ({neither/n*100:.1f}%)\n")

    # Disagreement analysis (if labels provided)
    if y_true is not None:
        console.print("[bold cyan]Disagreement Analysis (when they differ):[/bold cyan]")
        disagree_mask = moe_direction != baseline_direction

        if disagree_mask.sum() > 0:
            moe_correct = (moe_direction[disagree_mask] == y_true[disagree_mask]).sum()
            baseline_correct = (baseline_direction[disagree_mask] == y_true[disagree_mask]).sum()

            console.print(f"  Disagreement bars: {disagree_mask.sum():,} ({disagree_mask.mean()*100:.1f}%)")
            console.print(f"  MoE correct:       {moe_correct} ({moe_correct/disagree_mask.sum()*100:.1f}%)")
            console.print(f"  Baseline correct:  {baseline_correct} ({baseline_correct/disagree_mask.sum()*100:.1f}%)\n")

        # Combined signals
        console.print("[bold cyan]Combined Signal Strategies:[/bold cyan]")

        # AND: trade only when both agree
        and_signal = moe_signal & baseline_signal
        and_trade_rate = and_signal.mean()
        and_direction = moe_direction  # doesn't matter, they agree
        if and_signal.sum() > 0:
            and_acc = accuracy_score(y_true[and_signal], and_direction[and_signal])
            try:
                and_auc = roc_auc_score(y_true[and_signal], moe_proba[and_signal])
            except ValueError:
                and_auc = 0.5
        else:
            and_acc = 0.0
            and_auc = 0.5

        # OR: trade when either agrees
        or_signal = moe_signal | baseline_signal
        or_trade_rate = or_signal.mean()
        # For direction when they disagree: use MoE (or could use voting)
        or_direction = moe_direction
        if or_signal.sum() > 0:
            or_acc = accuracy_score(y_true[or_signal], or_direction[or_signal])
            try:
                or_auc = roc_auc_score(y_true[or_signal], moe_proba[or_signal])
            except ValueError:
                or_auc = 0.5
        else:
            or_acc = 0.0
            or_auc = 0.5

        table = Table(title="Combined Signals", box=box.SIMPLE)
        table.add_column("Strategy", style="cyan")
        table.add_column("Trade Rate", style="yellow")
        table.add_column("Accuracy", style="green")
        table.add_column("AUC", style="magenta")

        table.add_row("AND (both agree)", f"{and_trade_rate*100:.1f}%", f"{and_acc:.4f}", f"{and_auc:.4f}")
        table.add_row("OR (either)", f"{or_trade_rate*100:.1f}%", f"{or_acc:.4f}", f"{or_auc:.4f}")
        table.add_row("MoE only", f"{moe_signal.mean()*100:.1f}%",
                      f"{accuracy_score(y_true[moe_signal], moe_direction[moe_signal]) if moe_signal.sum() > 0 else 0:.4f}",
                      f"{roc_auc_score(y_true[moe_signal], moe_proba[moe_signal]) if moe_signal.sum() > 0 else 0.5:.4f}")
        table.add_row("Baseline only", f"{baseline_signal.mean()*100:.1f}%",
                      f"{accuracy_score(y_true[baseline_signal], baseline_direction[baseline_signal]) if baseline_signal.sum() > 0 else 0:.4f}",
                      f"{roc_auc_score(y_true[baseline_signal], baseline_proba[baseline_signal]) if baseline_signal.sum() > 0 else 0.5:.4f}")

        console.print("\n")
        console.print(table)

    console.print("\n[bold green]═══ Shadow Comparison Complete ═══[/bold green]\n")


if __name__ == "__main__":
    main()
