#!/usr/bin/env python3
"""Run multiple HYDRA training runs with different configs."""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
try:
    import lightgbm as lgb
    LGBM_AVAILABLE = True
except ImportError:
    LGBM_AVAILABLE = False
    print("⚠️  LightGBM not available, skipping LGBM runs")


def load_dataset(path: str = "data/hydra_full_dataset.parquet", mode: str = "research"):
    """Load dataset and prepare features/labels."""
    print(f"Loading {path}...")
    df = pd.read_parquet(path)

    # Validate shape contract
    expected_cols = 3001
    if df.shape[1] != expected_cols:
        raise ValueError(f"Shape contract violation: expected {expected_cols} cols, got {df.shape[1]}")

    # Validate mode
    if mode not in ['research', 'production', 'smoke']:
        raise ValueError(f"Invalid mode: {mode}. Must be research|production|smoke")

    print(f"✓ Shape validated: {df.shape}")
    print(f"✓ Mode: {mode.upper()}")

    # Get non-null feature columns (exclude time, labels, nulls)
    feature_cols = [c for c in df.columns if not c.startswith(('time', 'Z4_'))]
    feature_cols = [c for c in feature_cols if df[c].notna().sum() > len(df) * 0.5]

    # Use existing labels
    if 'Z4_0000' in df.columns and df['Z4_0000'].notna().sum() > 100:
        label_col = 'Z4_0000'  # 1-bar forward return
        y = (df[label_col] > 0).astype(int)
    elif 'Z4_0002' in df.columns and df['Z4_0002'].notna().sum() > 100:
        label_col = 'Z4_0002'  # 5-bar forward return
        y = (df[label_col] > 0).astype(int)
    else:
        # Simple forward return label
        print("Generating simple forward return labels...")
        if 'A_0004' in df.columns:  # A_close
            fwd_ret = df['A_0004'].pct_change(5).shift(-5)
            y = (fwd_ret > 0).astype(int)
        else:
            raise ValueError("No labels found and no price column")

    X = df[feature_cols].fillna(0)

    print(f"Features: {len(feature_cols)}, Samples: {len(X)}, Label rate: {y.mean():.3f}")

    return X, y, feature_cols


def train_single_run(
    X, y,
    run_id: int,
    model_type: str,
    n_iterations: int,
    params: dict,
    random_seed: int
):
    """Train single run and return metrics."""
    print(f"\n{'='*80}")
    print(f"RUN {run_id}: {model_type}, seed={random_seed}, iters={n_iterations}")
    print(f"{'='*80}")

    start_time = time.time()

    # Split data
    train_end = int(len(X) * 0.7)
    val_end = int(len(X) * 0.85)

    X_train, y_train = X.iloc[:train_end], y[:train_end]
    X_val, y_val = X.iloc[train_end:val_end], y[train_end:val_end]
    X_test, y_test = X.iloc[val_end:], y[val_end:]

    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Scale features
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    # Train model
    if model_type == 'rf':
        model = RandomForestClassifier(
            n_estimators=n_iterations,
            max_depth=params.get('max_depth', 10),
            min_samples_split=params.get('min_samples_split', 20),
            random_state=random_seed,
            n_jobs=-1
        )
        model.fit(X_train_scaled, y_train)

    elif model_type == 'gbm':
        model = GradientBoostingClassifier(
            n_estimators=n_iterations,
            max_depth=params.get('max_depth', 5),
            learning_rate=params.get('learning_rate', 0.1),
            subsample=params.get('subsample', 0.8),
            random_state=random_seed
        )
        model.fit(X_train_scaled, y_train)

    elif model_type == 'lgbm':
        if not LGBM_AVAILABLE:
            print("⚠️  LightGBM not available, skipping")
            return None
        model = lgb.LGBMClassifier(
            n_estimators=n_iterations,
            max_depth=params.get('max_depth', 8),
            learning_rate=params.get('learning_rate', 0.05),
            subsample=params.get('subsample', 0.8),
            colsample_bytree=params.get('colsample_bytree', 0.8),
            random_state=random_seed,
            n_jobs=-1,
            verbose=-1
        )
        model.fit(X_train_scaled, y_train)

    # Predict
    y_train_pred = model.predict(X_train_scaled)
    y_val_pred = model.predict(X_val_scaled)
    y_test_pred = model.predict(X_test_scaled)

    y_train_proba = model.predict_proba(X_train_scaled)[:, 1]
    y_val_proba = model.predict_proba(X_val_scaled)[:, 1]
    y_test_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Metrics
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score

    train_acc = accuracy_score(y_train, y_train_pred)
    val_acc = accuracy_score(y_val, y_val_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    train_f1 = f1_score(y_train, y_train_pred, zero_division=0)
    val_f1 = f1_score(y_val, y_val_pred, zero_division=0)
    test_f1 = f1_score(y_test, y_test_pred, zero_division=0)

    train_auc = roc_auc_score(y_train, y_train_proba) if len(np.unique(y_train)) > 1 else 0
    val_auc = roc_auc_score(y_val, y_val_proba) if len(np.unique(y_val)) > 1 else 0
    test_auc = roc_auc_score(y_test, y_test_proba) if len(np.unique(y_test)) > 1 else 0

    elapsed = time.time() - start_time

    results = {
        'run_id': run_id,
        'model_type': model_type,
        'n_iterations': n_iterations,
        'random_seed': random_seed,
        'params': params,
        'train_acc': train_acc,
        'val_acc': val_acc,
        'test_acc': test_acc,
        'train_f1': train_f1,
        'val_f1': val_f1,
        'test_f1': test_f1,
        'train_auc': train_auc,
        'val_auc': val_auc,
        'test_auc': test_auc,
        'train_size': len(X_train),
        'val_size': len(X_val),
        'test_size': len(X_test),
        'elapsed_seconds': elapsed,
        'timestamp': datetime.now().isoformat()
    }

    print(f"\nResults:")
    print(f"  Train: Acc={train_acc:.4f}, F1={train_f1:.4f}, AUC={train_auc:.4f}")
    print(f"  Val:   Acc={val_acc:.4f}, F1={val_f1:.4f}, AUC={val_auc:.4f}")
    print(f"  Test:  Acc={test_acc:.4f}, F1={test_f1:.4f}, AUC={test_auc:.4f}")
    print(f"  Time: {elapsed:.1f}s")

    return results


def main(dataset_path: str = "data/hydra_full_dataset.parquet", mode: str = "research", num_runs: int = 3):
    """Run training runs with different configs."""

    print(f"{'='*80}")
    print(f"HYDRA TRAINING")
    print(f"{'='*80}")
    print(f"Dataset: {dataset_path}")
    print(f"Mode: {mode.upper()}")
    print(f"Runs: {num_runs}")
    print(f"{'='*80}\n")

    # Load data once
    X, y, feature_cols = load_dataset(dataset_path, mode=mode)

    # Define configs (use first N based on num_runs)
    all_configs = [
        {'run_id': 1, 'model_type': 'rf', 'params': {'max_depth': 10, 'min_samples_split': 20}, 'seed': 42},
        {'run_id': 2, 'model_type': 'rf', 'params': {'max_depth': 15, 'min_samples_split': 10}, 'seed': 43},
        {'run_id': 3, 'model_type': 'rf', 'params': {'max_depth': 8, 'min_samples_split': 30}, 'seed': 44},

        {'run_id': 4, 'model_type': 'gbm', 'params': {'max_depth': 5, 'learning_rate': 0.1, 'subsample': 0.8}, 'seed': 45},
        {'run_id': 5, 'model_type': 'gbm', 'params': {'max_depth': 4, 'learning_rate': 0.05, 'subsample': 0.9}, 'seed': 46},
        {'run_id': 6, 'model_type': 'gbm', 'params': {'max_depth': 6, 'learning_rate': 0.15, 'subsample': 0.7}, 'seed': 47},

        {'run_id': 7, 'model_type': 'lgbm', 'params': {'max_depth': 8, 'learning_rate': 0.05, 'subsample': 0.8, 'colsample_bytree': 0.8}, 'seed': 48},
        {'run_id': 8, 'model_type': 'lgbm', 'params': {'max_depth': 10, 'learning_rate': 0.03, 'subsample': 0.9, 'colsample_bytree': 0.9}, 'seed': 49},
        {'run_id': 9, 'model_type': 'lgbm', 'params': {'max_depth': 6, 'learning_rate': 0.08, 'subsample': 0.7, 'colsample_bytree': 0.7}, 'seed': 50},
        {'run_id': 10, 'model_type': 'lgbm', 'params': {'max_depth': 12, 'learning_rate': 0.02, 'subsample': 0.85, 'colsample_bytree': 0.85}, 'seed': 51},
    ]

    configs = all_configs[:num_runs]

    # Run all configs
    all_results = []

    for config in configs:
        try:
            result = train_single_run(
                X, y,
                run_id=config['run_id'],
                model_type=config['model_type'],
                n_iterations=100,
                params=config['params'],
                random_seed=config['seed']
            )
            if result is not None:
                all_results.append(result)
        except Exception as e:
            print(f"\n❌ Run {config['run_id']} FAILED: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Save results
    results_df = pd.DataFrame(all_results)
    output_path = f"runs/multi_training_{mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    Path(output_path).parent.mkdir(exist_ok=True, parents=True)
    results_df.to_csv(output_path, index=False)

    # Save metadata
    metadata = {
        'mode': mode.upper(),
        'dataset_path': dataset_path,
        'num_runs': num_runs,
        'timestamp': datetime.now().isoformat(),
        'leakage_validation': 'BASIC_CHECK_ONLY',
        'status': 'RESEARCH_EXPERIMENT' if mode == 'research' else mode.upper()
    }
    metadata_path = output_path.replace('.csv', '_metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY OF ALL RUNS")
    print(f"{'='*80}")
    print(results_df[['run_id', 'model_type', 'test_acc', 'test_f1', 'test_auc', 'elapsed_seconds']].to_string(index=False))

    print(f"\n\nBest test accuracy: Run {results_df.loc[results_df['test_acc'].idxmax(), 'run_id']}, {results_df['test_acc'].max():.4f}")
    print(f"Best test F1:       Run {results_df.loc[results_df['test_f1'].idxmax(), 'run_id']}, {results_df['test_f1'].max():.4f}")
    print(f"Best test AUC:      Run {results_df.loc[results_df['test_auc'].idxmax(), 'run_id']}, {results_df['test_auc'].max():.4f}")

    print(f"\n\nResults saved to: {output_path}")

    return results_df


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Run multiple HYDRA training runs')
    parser.add_argument('--dataset', default='data/hydra_full_dataset.parquet')
    parser.add_argument('--mode', default='research', choices=['research', 'production', 'smoke'])
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--iterations', type=int, default=100, help='n_estimators for tree models')

    args = parser.parse_args()

    # Validate dataset shape before starting
    df_test = pd.read_parquet(args.dataset)
    if df_test.shape[1] != 3001:
        print(f"❌ SHAPE VIOLATION: Dataset has {df_test.shape[1]} cols, expected 3001")
        sys.exit(1)

    main(dataset_path=args.dataset, mode=args.mode, num_runs=args.runs)
