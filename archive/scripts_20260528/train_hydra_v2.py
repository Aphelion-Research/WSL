#!/usr/bin/env python3
"""HYDRA V2 — Train on alpha dataset with tick microstructure.

Runs AFTER build_alpha_dataset.py creates data/hydra_alpha_dataset.parquet.

Architecture:
    1. Regime gate (predict tradeability from vol/spread/flow features)
    2. 3 direction brains (scalp/day/swing) with feature groups:
       - Scalp: tick micro + short-term technicals
       - Day: lead-lag + medium technicals + regime
       - Swing: macro + COT + long-term cross-asset
    3. Meta-stacker: brain probas + regime gate + top features
    4. Confidence threshold optimization

Evaluation: accuracy + AUC on ALL bars, then on GATED bars only.
"""
import json
import time
import pickle
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import polars as pl
import lightgbm as lgb
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    roc_auc_score, log_loss
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

warnings.filterwarnings("ignore")
console = Console()

OUTPUT_DIR = Path("./output_hydra_v2")
OUTPUT_DIR.mkdir(exist_ok=True)

DATASET_PATH = Path("data/hydra_alpha_dataset.parquet")


def get_feature_groups(df):
    """Categorize features into groups for brain-specific selection."""
    cols = set(df.columns)
    base = {"time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume", "timestamp"}
    labels = {c for c in cols if "label" in c or "fwd" in c}
    exclude = base | labels

    tick = [c for c in cols - exclude if c.startswith("tick_")]
    leadlag = [c for c in cols - exclude if c.startswith("ll_")]
    regime = [c for c in cols - exclude if c.startswith("reg_")]
    macro = [c for c in cols - exclude if c.startswith("macro_")]
    cross_asset = [c for c in cols - exclude if any(c.startswith(p) for p in (
        "eurusd", "gbpusd", "usdchf", "usdjpy", "silver", "copper", "dxy",
        "spx", "nasdaq", "vix", "tlt", "hyg", "wti", "btc", "gvz",
        "gold_silver", "gold_copper", "oil_gold", "btc_gold",
        "corr_", "risk_on", "dollar_composite", "commodity",
        "cot_", "gld_", "yield_", "real_yield", "breakeven",
    ))]
    technical = [c for c in cols - exclude - set(tick) - set(leadlag) - set(regime)
                 - set(macro) - set(cross_asset)]

    return {
        "tick": sorted(tick),
        "leadlag": sorted(leadlag),
        "regime": sorted(regime),
        "macro": sorted(macro),
        "cross_asset": sorted(cross_asset),
        "technical": sorted(technical),
    }


def main():
    total_start = time.time()

    console.print(Panel.fit(
        "[bold]HYDRA V2 — ALPHA TRAINING[/bold]\n"
        "Tick microstructure + Lead-lag + Regime gating\n"
        "3 brains → meta-stacker → confidence gate",
        style="bold green"
    ))

    # ═══ LOAD ═══
    console.print("\n[bold cyan]═══ LOAD ═══[/bold cyan]")
    if not DATASET_PATH.exists():
        console.print(f"[red]Dataset not found: {DATASET_PATH}[/red]")
        console.print("[yellow]Run: python scripts/build_alpha_dataset.py[/yellow]")
        return

    df = pl.read_parquet(DATASET_PATH)
    console.print(f"  {df.shape[0]:,} rows x {df.shape[1]:,} cols")

    groups = get_feature_groups(df)
    console.print(f"  Feature groups:")
    for name, cols in groups.items():
        console.print(f"    {name}: {len(cols)}")

    # ═══ PREP ═══
    console.print("\n[bold cyan]═══ PREP ═══[/bold cyan]")

    unified_target = "label_72b"
    df_clean = df.drop_nulls(subset=[unified_target]).sort("time")

    # All features (excluding base + labels)
    all_features = sorted(set(sum(groups.values(), [])))
    console.print(f"  Total features: {len(all_features)}")

    # Fill nulls and clip
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in all_features])
    float_cols = [c for c in all_features if df_clean[c].dtype in (pl.Float32, pl.Float64)]
    df_clean = df_clean.with_columns([pl.col(c).clip(-1e6, 1e6) for c in float_cols])

    X = df_clean.select(all_features).to_numpy().astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    y = df_clean[unified_target].to_numpy().astype(np.int32)
    n = len(X)
    console.print(f"  Samples: {n:,} | Target dist: {dict(zip(*np.unique(y, return_counts=True)))}")

    # Feature index maps
    feat_to_idx = {c: i for i, c in enumerate(all_features)}

    # ═══ SPLIT ═══
    console.print("\n[bold cyan]═══ TEMPORAL SPLIT (60/20/20) ═══[/bold cyan]")
    train_end = int(0.60 * n)
    val_end = int(0.80 * n)
    train_idx = np.arange(0, train_end)
    val_idx = np.arange(train_end, val_end)
    oos_idx = np.arange(val_end, n)
    console.print(f"  Train: {len(train_idx):,} | Val: {len(val_idx):,} | OOS: {len(oos_idx):,}")

    # ═══ BRAIN TRAINING ═══
    console.print("\n[bold red]═══ BRAIN TRAINING ═══[/bold red]")

    brain_configs = {
        "scalp": {
            "target": "label_12b",
            "features": groups["tick"] + groups["technical"][:100] + groups["regime"],
            "params": {
                "objective": "binary", "metric": "auc",
                "boosting_type": "gbdt", "learning_rate": 0.03,
                "num_leaves": 63, "min_data_in_leaf": 100,
                "feature_fraction": 0.6, "bagging_fraction": 0.8,
                "bagging_freq": 5, "lambda_l1": 0.1, "lambda_l2": 1.0,
                "verbose": -1, "n_jobs": -1,
            },
            "rounds": 3000,
            "early_stop": 100,
        },
        "day": {
            "target": "label_72b",
            "features": groups["tick"] + groups["leadlag"] + groups["regime"] + groups["cross_asset"][:100] + groups["technical"][:80],
            "params": {
                "objective": "binary", "metric": "auc",
                "boosting_type": "gbdt", "learning_rate": 0.02,
                "num_leaves": 127, "min_data_in_leaf": 200,
                "feature_fraction": 0.5, "bagging_fraction": 0.7,
                "bagging_freq": 5, "lambda_l1": 0.5, "lambda_l2": 2.0,
                "verbose": -1, "n_jobs": -1,
            },
            "rounds": 3000,
            "early_stop": 150,
        },
        "swing": {
            "target": "label_288b",
            "features": groups["macro"] + groups["cross_asset"] + groups["leadlag"] + groups["regime"],
            "params": {
                "objective": "binary", "metric": "auc",
                "boosting_type": "gbdt", "learning_rate": 0.01,
                "num_leaves": 255, "min_data_in_leaf": 500,
                "feature_fraction": 0.4, "bagging_fraction": 0.6,
                "bagging_freq": 5, "lambda_l1": 1.0, "lambda_l2": 5.0,
                "verbose": -1, "n_jobs": -1,
            },
            "rounds": 3000,
            "early_stop": 200,
        },
    }

    brain_models = {}
    brain_results = {}

    for brain_name, cfg in brain_configs.items():
        console.print(f"\n  [bold yellow]── {brain_name.upper()} ({cfg['target']}) ──[/bold yellow]")

        # Get feature indices for this brain
        brain_feat = [f for f in cfg["features"] if f in feat_to_idx]
        brain_idx = [feat_to_idx[f] for f in brain_feat]
        console.print(f"    Features: {len(brain_feat)}")

        X_brain = X[:, brain_idx]

        # Get target
        if cfg["target"] in df_clean.columns:
            y_brain = df_clean[cfg["target"]].fill_null(0).to_numpy().astype(np.int32)
        else:
            y_brain = y

        # Train
        d_train = lgb.Dataset(X_brain[train_idx], label=y_brain[train_idx])
        d_val = lgb.Dataset(X_brain[val_idx], label=y_brain[val_idx], reference=d_train)

        start = time.time()
        model = lgb.train(
            cfg["params"], d_train, num_boost_round=cfg["rounds"],
            valid_sets=[d_train, d_val], valid_names=["train", "val"],
            callbacks=[lgb.early_stopping(cfg["early_stop"], verbose=False), lgb.log_evaluation(500)],
        )
        train_time = time.time() - start

        # Predict
        proba_val = model.predict(X_brain[val_idx])
        proba_oos = model.predict(X_brain[oos_idx])

        auc_val = roc_auc_score(y_brain[val_idx], proba_val)
        auc_oos = roc_auc_score(y_brain[oos_idx], proba_oos)
        acc_oos = accuracy_score(y_brain[oos_idx], (proba_oos > 0.5).astype(int))

        console.print(f"    Time: {train_time:.0f}s | Best iter: {model.best_iteration}")
        console.print(f"    Val AUC: {auc_val:.4f} | OOS AUC: {auc_oos:.4f} | OOS Acc: {acc_oos:.4f}")

        # Feature importance
        imp = model.feature_importance(importance_type="gain")
        top_feat = sorted(zip(brain_feat, imp), key=lambda x: -x[1])[:10]
        console.print(f"    Top features: {[f[0] for f in top_feat[:5]]}")

        brain_models[brain_name] = {"model": model, "feature_idx": brain_idx, "features": brain_feat}
        brain_results[brain_name] = {
            "val_auc": auc_val, "oos_auc": auc_oos, "oos_acc": acc_oos,
            "best_iter": model.best_iteration, "train_time": train_time,
            "proba_val": proba_val, "proba_oos": proba_oos,
            "top_features": [(f, float(g)) for f, g in top_feat],
        }

    # ═══ META-STACKER ═══
    console.print("\n[bold red]═══ META-STACKER ═══[/bold red]")

    # Stack features
    stack_val = np.column_stack([brain_results[b]["proba_val"] for b in brain_configs])
    stack_oos = np.column_stack([brain_results[b]["proba_oos"] for b in brain_configs])

    # Add disagreement + max/min
    disagree_val = np.std(stack_val, axis=1, keepdims=True)
    disagree_oos = np.std(stack_oos, axis=1, keepdims=True)
    max_val = np.max(stack_val, axis=1, keepdims=True)
    max_oos = np.max(stack_oos, axis=1, keepdims=True)

    # Add top regime features
    regime_idx = [feat_to_idx[f] for f in groups["regime"] if f in feat_to_idx]
    tick_top_idx = [feat_to_idx[f] for f in groups["tick"][:20] if f in feat_to_idx]

    X_meta_val = np.column_stack([stack_val, disagree_val, max_val, X[val_idx][:, regime_idx + tick_top_idx]])
    X_meta_oos = np.column_stack([stack_oos, disagree_oos, max_oos, X[oos_idx][:, regime_idx + tick_top_idx]])

    console.print(f"  Meta features: {X_meta_val.shape[1]}")

    # Train on val → test on OOS (or split val in half)
    meta_split = len(val_idx) // 2
    meta_params = {
        "objective": "binary", "metric": "auc",
        "boosting_type": "gbdt", "learning_rate": 0.01,
        "num_leaves": 15, "min_data_in_leaf": 500,
        "feature_fraction": 0.8, "bagging_fraction": 0.8,
        "bagging_freq": 3, "lambda_l1": 2.0, "lambda_l2": 10.0,
        "verbose": -1,
    }

    y_val = y[val_idx]
    meta_d_train = lgb.Dataset(X_meta_val[:meta_split], label=y_val[:meta_split])
    meta_d_val = lgb.Dataset(X_meta_val[meta_split:], label=y_val[meta_split:], reference=meta_d_train)

    meta_model = lgb.train(
        meta_params, meta_d_train, num_boost_round=1000,
        valid_sets=[meta_d_train, meta_d_val], valid_names=["train", "val"],
        callbacks=[lgb.early_stopping(50, verbose=False), lgb.log_evaluation(200)],
    )

    meta_proba_oos = meta_model.predict(X_meta_oos)
    meta_auc = roc_auc_score(y[oos_idx], meta_proba_oos)
    meta_acc = accuracy_score(y[oos_idx], (meta_proba_oos > 0.5).astype(int))
    console.print(f"  Meta OOS AUC: {meta_auc:.4f} | Acc: {meta_acc:.4f}")

    # ═══ CONFIDENCE GATING ═══
    console.print("\n[bold green]═══ CONFIDENCE GATING ═══[/bold green]")

    y_oos = y[oos_idx]

    # Test confidence thresholds
    console.print("  Direction confidence gating:")
    for conf in [0.50, 0.52, 0.55, 0.58, 0.60, 0.65, 0.70]:
        mask = (meta_proba_oos > conf) | (meta_proba_oos < (1 - conf))
        if mask.sum() < 50:
            continue
        g_acc = accuracy_score(y_oos[mask], (meta_proba_oos[mask] > 0.5).astype(int))
        g_auc = roc_auc_score(y_oos[mask], meta_proba_oos[mask]) if len(np.unique(y_oos[mask])) > 1 else 0.5
        console.print(f"    conf>{conf:.2f}: acc={g_acc:.4f} auc={g_auc:.4f} trades={mask.sum():,} ({mask.mean():.0%})")

    # Brain agreement gating
    console.print("\n  Brain agreement gating:")
    for agree_thresh in [2, 3]:
        brain_preds = np.column_stack([(brain_results[b]["proba_oos"] > 0.5).astype(int) for b in brain_configs])
        agreement = brain_preds.sum(axis=1)
        mask = (agreement >= agree_thresh) | (agreement <= (3 - agree_thresh))
        if mask.sum() < 50:
            continue
        g_acc = accuracy_score(y_oos[mask], (meta_proba_oos[mask] > 0.5).astype(int))
        g_auc = roc_auc_score(y_oos[mask], meta_proba_oos[mask]) if len(np.unique(y_oos[mask])) > 1 else 0.5
        console.print(f"    agree>={agree_thresh}/3: acc={g_acc:.4f} auc={g_auc:.4f} trades={mask.sum():,} ({mask.mean():.0%})")

    # ═══ FINAL TABLE ═══
    console.print("\n")
    table = Table(title="HYDRA V2 — FINAL RESULTS", box=box.DOUBLE_EDGE)
    table.add_column("Model", style="cyan")
    table.add_column("OOS AUC", style="magenta")
    table.add_column("OOS Acc", style="yellow")
    table.add_column("Detail", style="green")

    for b in brain_configs:
        r = brain_results[b]
        table.add_row(f"{b} brain", f"{r['oos_auc']:.4f}", f"{r['oos_acc']:.4f}", brain_configs[b]["target"])

    table.add_row("", "", "", "")
    table.add_row("META (stacked)", f"{meta_auc:.4f}", f"{meta_acc:.4f}", "All brains + regime + tick")
    console.print(table)

    # ═══ SAVE ═══
    console.print("\n[bold green]═══ SAVE ═══[/bold green]")

    model_artifact = {
        "brain_models": {b: brain_models[b] for b in brain_configs},
        "meta_model": meta_model,
        "all_features": all_features,
        "feature_groups": {k: v for k, v in groups.items()},
        "brain_configs": brain_configs,
        "results": {
            "brain_results": {b: {k: v for k, v in r.items() if k not in ("proba_val", "proba_oos")}
                            for b, r in brain_results.items()},
            "meta_auc": meta_auc,
            "meta_acc": meta_acc,
        },
    }

    model_path = OUTPUT_DIR / "hydra_v2_model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model_artifact, f)

    results = {
        "timestamp": datetime.now().isoformat(),
        "total_time_s": time.time() - total_start,
        "dataset": str(DATASET_PATH),
        "n_samples": n,
        "n_features": len(all_features),
        "brain_results": {b: {"oos_auc": r["oos_auc"], "oos_acc": r["oos_acc"],
                              "best_iter": r["best_iter"], "top_features": r["top_features"]}
                         for b, r in brain_results.items()},
        "meta_auc": meta_auc,
        "meta_acc": meta_acc,
    }
    results_path = OUTPUT_DIR / "results_v2.json"
    results_path.write_text(json.dumps(results, indent=2, default=str))

    console.print(f"  Model: {model_path}")
    console.print(f"  Results: {results_path}")

    total_time = time.time() - total_start
    console.print(Panel.fit(
        f"[bold green]HYDRA V2 COMPLETE[/bold green]\n\n"
        f"Meta OOS AUC: {meta_auc:.4f}\n"
        f"Time: {total_time:.0f}s\n"
        f"Model: {model_path}",
        style="bold green"
    ))


if __name__ == "__main__":
    main()
