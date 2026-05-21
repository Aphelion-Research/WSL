#!/usr/bin/env python3
"""Hyperparameter optimization overnight."""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_selected.parquet")
OUTPUT = Path("runs/hyperopt_results.csv")

LABEL = 'label_12b'


def hyperopt_lightgbm():
    """Hyperparameter search for LightGBM."""
    try:
        import lightgbm as lgb
        from sklearn.model_selection import ParameterGrid
    except ImportError:
        print("LightGBM not available")
        return

    print("Loading dataset...")
    df = pd.read_parquet(DATASET)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    df = df[df[LABEL].notna()].copy()
    y = df[LABEL].astype(int).values
    X = df[feature_cols].values

    print(f"Dataset: {len(X)} rows × {len(feature_cols)} features")

    # Train/val split (chronological)
    split = int(len(X) * 0.8)
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    scaler = RobustScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    # Parameter grid
    param_grid = {
        'n_estimators': [200, 500, 1000],
        'learning_rate': [0.01, 0.03, 0.05],
        'max_depth': [8, 10, 12, 15],
        'num_leaves': [31, 64, 127],
        'min_child_samples': [10, 20, 50],
    }

    print(f"\nSearching {len(list(ParameterGrid(param_grid)))} combinations...")

    results = []
    for i, params in enumerate(ParameterGrid(param_grid)):
        if i % 10 == 0:
            print(f"  Progress: {i}/{len(list(ParameterGrid(param_grid)))}")

        model = lgb.LGBMClassifier(**params, n_jobs=-1, verbosity=-1, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict_proba(X_val)[:, 1]
        auc = roc_auc_score(y_val, y_pred)

        results.append({**params, 'auc': auc})

    results_df = pd.DataFrame(results).sort_values('auc', ascending=False)
    results_df.to_csv(OUTPUT, index=False)

    print("\n" + "="*60)
    print("TOP 10 PARAMETER COMBINATIONS")
    print("="*60)
    print(results_df.head(10).to_string(index=False))
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    hyperopt_lightgbm()
