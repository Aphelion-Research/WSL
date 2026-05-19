#!/usr/bin/env python3
"""Train baseline models for Dominion dataset v1.

Models:
1. Ridge Regression (alpha=1.0)
2. Random Forest (n_estimators=100, max_depth=10)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import json
from datetime import datetime

# Add scripts dir to path
import sys
sys.path.insert(0, str(Path(__file__).parent))
from metrics import compute_all_metrics, print_metrics, evaluate_model

# Config
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"


def load_data():
    """Load train, val, test sets."""
    print("Loading data...")

    train = pd.read_parquet(DATA_DIR / "train_v1.parquet")
    val = pd.read_parquet(DATA_DIR / "val_v1.parquet")
    test = pd.read_parquet(DATA_DIR / "test_v1.parquet")

    print(f"  Train: {len(train)} rows")
    print(f"  Val: {len(val)} rows")
    print(f"  Test: {len(test)} rows")

    return train, val, test


def prepare_features(df, target_col='target_return_1'):
    """Prepare features and target."""
    # Exclude system columns
    exclude_cols = ['timestamp', 'close', 'high', 'low', 'open', 'volume',
                    'target_return_1', 'target_return_5', 'target_return_10']

    feature_cols = [col for col in df.columns if col not in exclude_cols]
    X = df[feature_cols].values
    y = df[target_col].values

    return X, y, feature_cols


def train_ridge(X_train, y_train, X_val, y_val):
    """Train Ridge regression."""
    print("\n" + "=" * 60)
    print("Training Ridge Regression (alpha=1.0)")
    print("=" * 60)

    # Standardize
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)

    # Train
    model = Ridge(alpha=1.0)
    model.fit(X_train_scaled, y_train)

    # Predict
    train_pred = model.predict(X_train_scaled)
    val_pred = model.predict(X_val_scaled)

    return model, scaler, train_pred, val_pred


def train_random_forest(X_train, y_train, X_val, y_val):
    """Train Random Forest."""
    print("\n" + "=" * 60)
    print("Training Random Forest (n_estimators=100, max_depth=10)")
    print("=" * 60)

    # Train
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train)

    # Predict
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)

    return model, train_pred, val_pred


def compute_strategy_returns(predictions, actuals, threshold=0.0):
    """Compute strategy returns from predictions.

    Strategy: Long if pred > threshold, short if pred < -threshold, flat otherwise.
    """
    positions = np.where(predictions > threshold, 1,
                         np.where(predictions < -threshold, -1, 0))

    strategy_returns = positions * actuals

    return strategy_returns, positions


def main():
    """Train baselines and compute metrics."""
    print("=" * 60)
    print("Baseline Models for Dominion Dataset v1")
    print("=" * 60)

    # Load
    train, val, test = load_data()

    # Prepare
    X_train, y_train, feature_cols = prepare_features(train)
    X_val, y_val, _ = prepare_features(val)

    print(f"\nFeatures: {len(feature_cols)}")
    print(f"Samples: Train={len(X_train)}, Val={len(X_val)}")

    # Ridge
    ridge_model, ridge_scaler, ridge_train_pred, ridge_val_pred = train_ridge(
        X_train, y_train, X_val, y_val
    )

    # Ridge metrics (train)
    ridge_train_returns, ridge_train_positions = compute_strategy_returns(ridge_train_pred, y_train)
    ridge_train_metrics = compute_all_metrics(
        predictions=pd.Series(ridge_train_pred),
        actuals=pd.Series(y_train),
        returns=pd.Series(ridge_train_returns),
        positions=pd.Series(ridge_train_positions),
    )
    ridge_train_metrics['model'] = 'Ridge'
    ridge_train_metrics['split'] = 'train'

    # Ridge metrics (val)
    ridge_val_returns, ridge_val_positions = compute_strategy_returns(ridge_val_pred, y_val)
    ridge_val_metrics = compute_all_metrics(
        predictions=pd.Series(ridge_val_pred),
        actuals=pd.Series(y_val),
        returns=pd.Series(ridge_val_returns),
        positions=pd.Series(ridge_val_positions),
    )
    ridge_val_metrics['model'] = 'Ridge'
    ridge_val_metrics['split'] = 'val'

    print_metrics(ridge_train_metrics, title="Ridge - Train Set")
    print_metrics(ridge_val_metrics, title="Ridge - Val Set")

    # Random Forest
    rf_model, rf_train_pred, rf_val_pred = train_random_forest(
        X_train, y_train, X_val, y_val
    )

    # RF metrics (train)
    rf_train_returns, rf_train_positions = compute_strategy_returns(rf_train_pred, y_train)
    rf_train_metrics = compute_all_metrics(
        predictions=pd.Series(rf_train_pred),
        actuals=pd.Series(y_train),
        returns=pd.Series(rf_train_returns),
        positions=pd.Series(rf_train_positions),
    )
    rf_train_metrics['model'] = 'RandomForest'
    rf_train_metrics['split'] = 'train'

    # RF metrics (val)
    rf_val_returns, rf_val_positions = compute_strategy_returns(rf_val_pred, y_val)
    rf_val_metrics = compute_all_metrics(
        predictions=pd.Series(rf_val_pred),
        actuals=pd.Series(y_val),
        returns=pd.Series(rf_val_returns),
        positions=pd.Series(rf_val_positions),
    )
    rf_val_metrics['model'] = 'RandomForest'
    rf_val_metrics['split'] = 'val'

    print_metrics(rf_train_metrics, title="RandomForest - Train Set")
    print_metrics(rf_val_metrics, title="RandomForest - Val Set")

    # Compare
    print("\n" + "=" * 60)
    print("COMPARISON (Val Set)")
    print("=" * 60)

    comparison = pd.DataFrame([
        {
            'Model': 'Ridge',
            'IC': ridge_val_metrics['ic'],
            'Sharpe': ridge_val_metrics['sharpe'],
            'Max DD': ridge_val_metrics['max_drawdown'],
            'Turnover': ridge_val_metrics['turnover'],
        },
        {
            'Model': 'RandomForest',
            'IC': rf_val_metrics['ic'],
            'Sharpe': rf_val_metrics['sharpe'],
            'Max DD': rf_val_metrics['max_drawdown'],
            'Turnover': rf_val_metrics['turnover'],
        }
    ])

    print(comparison.to_string(index=False))

    # Evaluate
    ridge_ratings = evaluate_model(ridge_val_metrics)
    rf_ratings = evaluate_model(rf_val_metrics)

    print("\n" + "=" * 60)
    print("RATINGS (Val Set)")
    print("=" * 60)
    print(f"\nRidge:")
    for metric, rating in ridge_ratings.items():
        print(f"  {metric}: {rating}")

    print(f"\nRandomForest:")
    for metric, rating in rf_ratings.items():
        print(f"  {metric}: {rating}")

    # Save results
    results = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "dataset": "dataset_v1",
        "models": {
            "ridge": {
                "train": ridge_train_metrics,
                "val": ridge_val_metrics,
                "ratings": ridge_ratings,
            },
            "random_forest": {
                "train": rf_train_metrics,
                "val": rf_val_metrics,
                "ratings": rf_ratings,
            }
        }
    }

    # Convert NaN/inf to None for JSON
    def clean_for_json(obj):
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(v) for v in obj]
        elif isinstance(obj, float):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return obj
        else:
            return obj

    results = clean_for_json(results)

    results_path = REPO_ROOT / "reports" / "baseline_results_v1.json"
    results_path.write_text(json.dumps(results, indent=2))

    print(f"\n✓ Results saved: {results_path}")

    return 0


if __name__ == "__main__":
    exit(main())
