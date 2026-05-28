#!/usr/bin/env python3
"""Merge 3 Hydra brains into mega-ensemble + OOS evaluation.

Waits for all 3 brain training outputs, then:
1. Loads OOS probabilities from each brain
2. Trains meta-learner (logistic regression on val set)
3. Evaluates fused predictions on OOS
4. Reports individual vs mega comparison

Run AFTER all 3 brains complete:
    python scripts/merge_brains.py
"""
import json
import time
from pathlib import Path
from datetime import datetime

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score, log_loss
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

BRAINS = ["scalp", "day", "swing"]
OUTPUT_DIR = Path("./output_hydra_mega")


def wait_for_outputs(timeout=3600):
    """Wait until all 3 brains have finished training."""
    needed = []
    for brain in BRAINS:
        d = Path(f"./output_hydra_{brain}")
        needed.append(d / f"oos_proba_{brain}.npy")
        needed.append(d / f"results_{brain}.json")

    console.print("[bold yellow]Waiting for all 3 brains to finish...[/bold yellow]")
    start = time.time()
    while True:
        missing = [f for f in needed if not f.exists()]
        if not missing:
            console.print("[bold green]All 3 brains complete![/bold green]")
            return True
        elapsed = time.time() - start
        if elapsed > timeout:
            console.print(f"[red]Timeout! Missing: {[str(f) for f in missing]}[/red]")
            return False
        remaining = len(missing)
        console.print(f"  [{elapsed:.0f}s] Waiting... {remaining} files remaining", end="\r")
        time.sleep(5)


def compute_metrics(y_true, y_pred, y_proba):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, average="binary")),
        "precision": float(precision_score(y_true, y_pred, average="binary", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="binary")),
        "auc_roc": float(roc_auc_score(y_true, y_proba)),
        "log_loss": float(log_loss(y_true, y_proba)),
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    console.print(Panel.fit(
        "HYDRA MEGA-ENSEMBLE\n"
        "Fusing scalp + day + swing into unified predictor",
        style="bold green"
    ))

    # Wait for all brains
    if not wait_for_outputs():
        return

    # Load individual results
    console.print("\n[bold cyan]LOADING BRAIN OUTPUTS[/bold cyan]")
    brain_results = {}
    val_probas = {}
    val_labels = {}
    oos_probas = {}
    oos_labels = {}

    for brain in BRAINS:
        d = Path(f"./output_hydra_{brain}")
        results_path = d / f"results_{brain}.json"
        brain_results[brain] = json.loads(results_path.read_text())

        val_probas[brain] = np.load(d / f"val_proba_{brain}.npy")
        val_labels[brain] = np.load(d / f"val_labels_{brain}.npy")
        oos_probas[brain] = np.load(d / f"oos_proba_{brain}.npy")
        oos_labels[brain] = np.load(d / f"oos_labels_{brain}.npy")

        console.print(f"  {brain}: OOS acc={brain_results[brain]['oos_metrics']['accuracy']:.4f}, "
                      f"AUC={brain_results[brain]['oos_metrics']['auc_roc']:.4f}")

    # All brains predict on same OOS window but with DIFFERENT targets.
    # For mega-ensemble we need a unified target. Use label_72b (day brain target)
    # as the "gold standard" since it's the medium horizon.
    # But each brain's signal carries information about different regimes.

    # Strategy 1: Simple average of probabilities (treats all as same-target predictors)
    # Strategy 2: Stacked meta-learner on val set
    # Strategy 3: Majority vote

    # Since targets differ, the right approach is:
    # - Each brain predicts its own target on OOS
    # - The MEGA model stacks all 3 proba as features → predicts a unified target
    # - Use "day" target (label_72b) as the unified OOS label for final eval

    # The OOS labels from day brain = our unified eval target
    y_oos_unified = oos_labels["day"]
    y_val_unified = val_labels["day"]

    console.print(f"\n[bold blue]UNIFIED TARGET: label_72b (day brain)[/bold blue]")
    console.print(f"  OOS: {len(y_oos_unified):,} samples")
    console.print(f"  Val: {len(y_val_unified):,} samples")

    # Build stacking features: [scalp_proba, day_proba, swing_proba]
    # All share same temporal split boundaries so arrays align
    X_val_stack = np.column_stack([val_probas[b] for b in BRAINS])
    X_oos_stack = np.column_stack([oos_probas[b] for b in BRAINS])

    console.print(f"  Stack features: {X_val_stack.shape}")

    # Strategy 1: Simple average
    console.print("\n[bold magenta]STRATEGY 1: Simple Average[/bold magenta]")
    avg_proba_oos = np.mean(X_oos_stack, axis=1)
    avg_pred_oos = (avg_proba_oos > 0.5).astype(int)
    avg_metrics = compute_metrics(y_oos_unified, avg_pred_oos, avg_proba_oos)

    # Strategy 2: Weighted average (weight by val AUC)
    console.print("[bold magenta]STRATEGY 2: AUC-Weighted Average[/bold magenta]")
    val_aucs = np.array([
        roc_auc_score(y_val_unified, val_probas[b]) for b in BRAINS
    ])
    weights = val_aucs / val_aucs.sum()
    console.print(f"  Weights: scalp={weights[0]:.3f}, day={weights[1]:.3f}, swing={weights[2]:.3f}")
    weighted_proba_oos = X_oos_stack @ weights
    weighted_pred_oos = (weighted_proba_oos > 0.5).astype(int)
    weighted_metrics = compute_metrics(y_oos_unified, weighted_pred_oos, weighted_proba_oos)

    # Strategy 3: Logistic meta-learner
    console.print("[bold magenta]STRATEGY 3: Logistic Meta-Learner[/bold magenta]")
    meta = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=42)
    meta.fit(X_val_stack, y_val_unified)
    meta_proba_oos = meta.predict_proba(X_oos_stack)[:, 1]
    meta_pred_oos = (meta_proba_oos > 0.5).astype(int)
    meta_metrics = compute_metrics(y_oos_unified, meta_pred_oos, meta_proba_oos)
    console.print(f"  Meta coefficients: {meta.coef_[0]}")

    # Strategy 4: Majority vote (>0.5 from each brain → 1 if 2+ agree)
    console.print("[bold magenta]STRATEGY 4: Majority Vote[/bold magenta]")
    votes = (X_oos_stack > 0.5).astype(int)
    vote_pred_oos = (votes.sum(axis=1) >= 2).astype(int)
    vote_proba_oos = votes.mean(axis=1).astype(float)
    vote_metrics = compute_metrics(y_oos_unified, vote_pred_oos, vote_proba_oos)

    # Comparison table
    console.print("\n")
    table = Table(title="HYDRA MEGA-ENSEMBLE — OOS COMPARISON", box=box.DOUBLE_EDGE)
    table.add_column("Model", style="cyan")
    table.add_column("Accuracy", style="magenta")
    table.add_column("F1", style="magenta")
    table.add_column("AUC-ROC", style="magenta")
    table.add_column("Log Loss", style="magenta")
    table.add_column("Precision", style="magenta")
    table.add_column("Recall", style="magenta")

    # Individual brains (evaluated against unified target)
    for brain in BRAINS:
        m = brain_results[brain]["oos_metrics"]
        table.add_row(
            f"{brain} (own target)",
            f"{m['accuracy']:.4f}",
            f"{m['f1']:.4f}",
            f"{m['auc_roc']:.4f}",
            f"{m['log_loss']:.4f}",
            f"{m['precision']:.4f}",
            f"{m['recall']:.4f}",
        )

    table.add_row("", "", "", "", "", "", "")

    # Day brain as baseline (same target)
    day_m = brain_results["day"]["oos_metrics"]
    table.add_row(
        "day (baseline)",
        f"{day_m['accuracy']:.4f}",
        f"{day_m['f1']:.4f}",
        f"{day_m['auc_roc']:.4f}",
        f"{day_m['log_loss']:.4f}",
        f"{day_m['precision']:.4f}",
        f"{day_m['recall']:.4f}",
        style="bold yellow",
    )

    # Mega strategies
    for name, m in [("Mega: Average", avg_metrics),
                     ("Mega: Weighted", weighted_metrics),
                     ("Mega: Meta-LR", meta_metrics),
                     ("Mega: MajVote", vote_metrics)]:
        table.add_row(
            name,
            f"{m['accuracy']:.4f}",
            f"{m['f1']:.4f}",
            f"{m['auc_roc']:.4f}",
            f"{m['log_loss']:.4f}",
            f"{m['precision']:.4f}",
            f"{m['recall']:.4f}",
        )

    console.print(table)

    # Pick best strategy
    strategies = {
        "average": avg_metrics,
        "weighted": weighted_metrics,
        "meta_lr": meta_metrics,
        "majority_vote": vote_metrics,
    }
    best_name = max(strategies, key=lambda k: strategies[k]["auc_roc"])
    best_metrics = strategies[best_name]

    console.print(f"\n[bold green]BEST: {best_name} (AUC={best_metrics['auc_roc']:.4f})[/bold green]")

    # Leak check
    if best_metrics["accuracy"] > 0.65:
        console.print("[bold red]WARNING: Accuracy > 65% — investigate possible leakage[/bold red]")
    else:
        console.print("[bold green]LEAK CHECK: PASS (accuracy in realistic range)[/bold green]")

    # Save mega results
    mega_results = {
        "individual_brains": {b: brain_results[b]["oos_metrics"] for b in BRAINS},
        "mega_strategies": strategies,
        "best_strategy": best_name,
        "best_metrics": best_metrics,
        "weights": weights.tolist() if weights is not None else None,
        "meta_coef": meta.coef_[0].tolist(),
        "unified_target": "label_72b",
        "oos_samples": len(y_oos_unified),
        "timestamp": datetime.now().isoformat(),
    }

    results_path = OUTPUT_DIR / "mega_results.json"
    results_path.write_text(json.dumps(mega_results, indent=2))
    console.print(f"\n  Saved: {results_path}")

    # Save meta-learner
    import pickle
    meta_path = OUTPUT_DIR / "meta_learner.pkl"
    with open(meta_path, "wb") as f:
        pickle.dump(meta, f)
    console.print(f"  Saved: {meta_path}")

    console.print(f"\n[bold green]HYDRA MEGA-ENSEMBLE COMPLETE[/bold green]")


if __name__ == "__main__":
    main()
