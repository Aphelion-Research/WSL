#!/usr/bin/env python3
"""Train single day brain (label_72b) without meta overhead."""
import json
import time
import pickle
import numpy as np
import polars as pl
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import roc_auc_score, accuracy_score, log_loss
from sklearn.feature_selection import mutual_info_classif
from rich.console import Console

console = Console()
OUTPUT_DIR = Path("output_day_brain_simple")
OUTPUT_DIR.mkdir(exist_ok=True)

CONFIG = {
    "dataset": "data/hydra_alpha_dataset.parquet",
    "target": "label_72b",
    "n_features": 400,
    "lgb_params": {
        "objective": "binary",
        "metric": "auc",
        "boosting_type": "gbdt",
        "n_estimators": 500,
        "learning_rate": 0.03,
        "num_leaves": 63,
        "max_depth": -1,
        "min_data_in_leaf": 200,
        "feature_fraction": 0.5,
        "bagging_fraction": 0.7,
        "bagging_freq": 5,
        "lambda_l1": 0.5,
        "lambda_l2": 2.0,
        "verbose": 100,
        "random_state": 42,
        "n_jobs": -1,
    },
    "early_stop": 50,
}


def load_data():
    console.print("\n[cyan]═══ LOAD DATA ═══[/cyan]")
    df = pl.read_parquet(CONFIG["dataset"])

    # Feature cols
    exclude = {"time", "timestamp", "open", "high", "low", "close",
               "tick_volume", "spread", "real_volume"}
    label_cols = {c for c in df.columns if "label" in c.lower()}
    fwd_cols = {c for c in df.columns if "fwd_" in c or "future" in c}
    exclude.update(label_cols)
    exclude.update(fwd_cols)
    feature_cols = [c for c in df.columns if c not in exclude]

    # Filter valid target
    df_clean = df.filter(pl.col(CONFIG["target"]).is_not_null()).sort("time")
    df_clean = df_clean.with_columns([pl.col(c).fill_null(0.0) for c in feature_cols])

    console.print(f"  {len(df_clean):,} rows × {len(feature_cols)} features")

    X = df_clean.select(feature_cols).to_numpy().astype(np.float32)
    y = df_clean[CONFIG["target"]].to_numpy().astype(np.int32)

    return X, y, feature_cols


def select_features(X, y, feature_names, n_select):
    """MI-based feature selection with alpha feature boost."""
    console.print(f"\n[cyan]═══ FEATURE SELECTION (top {n_select}) ═══[/cyan]")

    # Subsample 50k for MI
    n_sample = min(50000, len(X))
    idx = np.random.RandomState(42).choice(len(X), n_sample, replace=False)
    X_sub = X[idx]
    y_sub = y[idx]
    X_clean = np.nan_to_num(X_sub, nan=0.0, posinf=0.0, neginf=0.0)

    mi_scores = mutual_info_classif(X_clean, y_sub, random_state=42, n_neighbors=5)

    # Boost alpha features (tick_*, ll_*, reg_*)
    boosted_scores = mi_scores.copy()
    for i, name in enumerate(feature_names):
        if name.startswith(("tick_", "ll_", "reg_")):
            boosted_scores[i] *= 2.0  # 2x boost for alpha features

    top_idx = np.argsort(boosted_scores)[::-1][:n_select]
    selected = [feature_names[i] for i in top_idx]

    alpha_selected = [f for f in selected if f.startswith(("tick_", "ll_", "reg_"))]
    console.print(f"  Selected: {len(selected)} ({len(alpha_selected)} alpha features)")
    console.print(f"  Top MI: {mi_scores[top_idx[0]]:.4f}")

    return selected, top_idx


def train_model(X, y, feature_idx):
    console.print("\n[cyan]═══ TRAIN ═══[/cyan]")

    X_sel = X[:, feature_idx]

    # Temporal split
    n = len(X_sel)
    train_end = int(n * 0.6)
    val_end = int(n * 0.8)

    X_train = X_sel[:train_end]
    y_train = y[:train_end]
    X_val = X_sel[train_end:val_end]
    y_val = y[train_end:val_end]
    X_oos = X_sel[val_end:]
    y_oos = y[val_end:]

    console.print(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | OOS: {len(X_oos):,}")

    # Train
    train_data = lgb.Dataset(X_train, y_train)
    val_data = lgb.Dataset(X_val, y_val, reference=train_data)

    model = lgb.train(
        CONFIG["lgb_params"],
        train_data,
        valid_sets=[val_data],
    )

    # Evaluate
    proba_val = model.predict(X_val)
    proba_oos = model.predict(X_oos)

    val_auc = roc_auc_score(y_val, proba_val)
    oos_auc = roc_auc_score(y_oos, proba_oos)

    console.print(f"\n  Val AUC: {val_auc:.4f}")
    console.print(f"  OOS AUC: {oos_auc:.4f}")

    return model, val_auc, oos_auc, proba_oos, y_oos


def main():
    start = time.time()

    console.print("\n[bold green]═══ DAY BRAIN (SIMPLE) ═══[/bold green]")
    console.print(f"Target: {CONFIG['target']}")
    console.print(f"Features: {CONFIG['n_features']} (MI + 2x alpha boost)")

    # Load
    X, y, feature_names = load_data()

    # Select
    selected_features, feature_idx = select_features(
        X, y, feature_names, CONFIG["n_features"]
    )

    # Train
    model, val_auc, oos_auc, proba_oos, y_oos = train_model(X, y, feature_idx)

    # Proba stats
    console.print(f"\n[cyan]═══ OOS PROBA DISTRIBUTION ═══[/cyan]")
    console.print(f"  Min: {np.min(proba_oos):.4f}")
    console.print(f"  Max: {np.max(proba_oos):.4f}")
    console.print(f"  Mean: {np.mean(proba_oos):.4f}")
    console.print(f"  >0.55: {np.sum(proba_oos > 0.55):,} ({np.sum(proba_oos > 0.55)/len(proba_oos)*100:.1f}%)")
    console.print(f"  >0.60: {np.sum(proba_oos > 0.60):,} ({np.sum(proba_oos > 0.60)/len(proba_oos)*100:.1f}%)")

    # Save
    model_artifact = {
        "model": model,
        "feature_idx": feature_idx,
        "selected_features": selected_features,
        "target": CONFIG["target"],
        "val_auc": val_auc,
        "oos_auc": oos_auc,
    }

    with open(OUTPUT_DIR / "day_brain_simple.pkl", "wb") as f:
        pickle.dump(model_artifact, f)

    results = {
        "target": CONFIG["target"],
        "n_features": len(selected_features),
        "alpha_features": [f for f in selected_features if f.startswith(("tick_", "ll_", "reg_"))],
        "val_auc": val_auc,
        "oos_auc": oos_auc,
        "proba_min": float(np.min(proba_oos)),
        "proba_max": float(np.max(proba_oos)),
        "proba_mean": float(np.mean(proba_oos)),
        "train_time_s": time.time() - start,
    }

    with open(OUTPUT_DIR / "results_simple.json", "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[green]Model saved: {OUTPUT_DIR}/day_brain_simple.pkl[/green]")
    console.print(f"Time: {time.time() - start:.0f}s")

    # Compare vs mega
    console.print("\n[cyan]═══ VS ALPHA MEGA ═══[/cyan]")
    console.print(f"  Mega meta OOS: 0.5231")
    console.print(f"  Simple day OOS: {oos_auc:.4f}")
    console.print(f"  Delta: {oos_auc - 0.5231:+.4f}")


if __name__ == "__main__":
    main()
