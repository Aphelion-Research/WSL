#!/usr/bin/env python3
"""
Export HYDRA dataset to binary format for C++ fast training.

Parquet → Binary (row-major float32, int8 labels)
"""
import polars as pl
import numpy as np
import json
import argparse
from pathlib import Path
from datetime import datetime

# Constants
COMMISSION_PER_1_LOT = 5.00
GOLD_OZ_PER_LOT = 100
HORIZON = 288

def main():
    parser = argparse.ArgumentParser(description='Export HYDRA dataset to binary')
    parser.add_argument('--dataset', type=Path, default=Path('data/hydra_xauusd_m5_master_clean.parquet'))
    parser.add_argument('--schema', type=Path, default=Path('data/hydra_xauusd_m5_master_schema.json'))
    parser.add_argument('--label', default='label_288b')
    parser.add_argument('--top-features', type=int, default=None, help='Limit to top N features by variance')
    parser.add_argument('--output-dir', type=Path, default=Path('data/hydra_binary_288b'))
    parser.add_argument('--verbose', action='store_true')

    args = parser.parse_args()

    print("=" * 80)
    print("HYDRA BINARY EXPORT")
    print("=" * 80)

    # Check inputs
    if not args.dataset.exists():
        raise FileNotFoundError(f"Dataset not found: {args.dataset}")
    if not args.schema.exists():
        raise FileNotFoundError(f"Schema not found: {args.schema}")

    # Load schema
    print(f"\n[SCHEMA]")
    schema = json.loads(args.schema.read_text())
    print(f"✓ Columns: {len(schema['columns'])}")

    # Feature selection
    forbidden_patterns = ['fwd', 'forward', 'future', 'next', 'lead', 'target', 'label', 'y_']

    feature_pool = [
        c['name'] for c in schema['columns']
        if c['role'] == 'feature'
        and c.get('allowed_for_training', False)
        and not c.get('is_forward_looking', False)
    ]

    # Remove forbidden patterns
    feature_pool_before = len(feature_pool)
    feature_pool = [f for f in feature_pool if not any(p in f.lower() for p in forbidden_patterns)]
    forbidden_count = feature_pool_before - len(feature_pool)

    print(f"✓ Feature pool: {len(feature_pool)}")
    if forbidden_count > 0:
        print(f"✓ Blocked {forbidden_count} forbidden features")

    # Load dataset
    print(f"\n[DATASET]")
    print(f"Loading: {args.dataset}")
    df = pl.read_parquet(args.dataset)
    print(f"✓ Shape: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

    # Check time
    t_min = df['time'].min()
    t_max = df['time'].max()
    print(f"✓ Time: {t_min} → {t_max}")

    # Check label
    if args.label not in df.columns:
        raise ValueError(f"Label {args.label} not found")
    print(f"✓ Label: {args.label}")

    # Load close prices
    print(f"\n[CLOSE PRICES]")
    raw_df = pl.read_parquet('data/mt5_history/XAUUSD_M5_dukascopy.parquet')
    close_prices = raw_df.select(['time', 'close'])
    print(f"✓ Loaded {len(close_prices):,} close prices")

    # Merge
    df = df.join(close_prices, on='time', how='left')

    # Convert to pandas for processing
    df_pd = df.to_pandas()

    # Sort by time
    df_pd = df_pd.sort_values('time').reset_index(drop=True)

    # Drop nulls
    rows_before = len(df_pd)
    df_pd = df_pd.dropna(subset=[args.label, 'close'])
    rows_after = len(df_pd)
    print(f"✓ After dropna: {rows_after:,} rows (dropped {rows_before - rows_after})")

    # Feature ranking (optional)
    if args.top_features:
        print(f"\n[FEATURE RANKING]")
        print(f"Ranking features by variance + correlation with label")

        # Take first 80% for ranking (train-like split)
        train_cutoff = int(len(df_pd) * 0.8)
        train_df = df_pd.iloc[:train_cutoff]

        # Compute variance on train only
        X_train = train_df[feature_pool].fillna(0).replace([np.inf, -np.inf], [1e10, -1e10])
        y_train = train_df[args.label].values

        # Remove NaN labels
        valid_train = ~np.isnan(y_train)
        X_train = X_train[valid_train]
        y_train = y_train[valid_train]

        # Variance score
        var_scores = X_train.var().values

        # Correlation score
        corr_scores = np.abs([np.corrcoef(X_train.iloc[:, i].values, y_train)[0, 1] for i in range(len(feature_pool))])
        corr_scores = np.nan_to_num(corr_scores, 0)

        # Combined score: variance * |correlation|
        combined_scores = var_scores * corr_scores

        # Rank
        ranked_indices = np.argsort(combined_scores)[::-1]
        feature_pool = [feature_pool[i] for i in ranked_indices[:args.top_features]]

        print(f"✓ Selected top {len(feature_pool)} features")
        if args.verbose:
            print(f"  Top 20: {feature_pool[:20]}")

    # Extract X, y, close
    print(f"\n[EXTRACT]")
    X = df_pd[feature_pool].fillna(0).replace([np.inf, -np.inf], [1e10, -1e10]).values.astype(np.float32)
    y = df_pd[args.label].values.astype(np.int8)
    close = df_pd['close'].values.astype(np.float64)
    times = df_pd['time'].values

    print(f"✓ X: {X.shape} (float32)")
    print(f"✓ y: {y.shape} (int8)")
    print(f"✓ close: {close.shape} (float64)")

    # Validate
    print(f"\n[VALIDATE]")
    if np.isnan(X).any():
        raise ValueError("X contains NaN after fillna")
    if np.isinf(X).any():
        raise ValueError("X contains Inf after replacement")
    if not np.all((y == 0) | (y == 1)):
        raise ValueError(f"Label not binary: unique values = {np.unique(y)}")
    if np.any(close <= 0):
        raise ValueError("Close contains non-positive values")

    print(f"✓ X: no NaN/Inf")
    print(f"✓ y: binary 0/1")
    print(f"✓ close: all positive")

    # Class balance
    balance = y.mean()
    print(f"✓ Label balance: {balance:.3f}")

    # Write binary files
    print(f"\n[WRITE]")
    args.output_dir.mkdir(exist_ok=True, parents=True)

    X_path = args.output_dir / 'X_float32.bin'
    y_path = args.output_dir / 'y_int8.bin'
    close_path = args.output_dir / 'close_float64.bin'
    meta_path = args.output_dir / 'meta.json'
    features_path = args.output_dir / 'feature_names.txt'

    # Write X (row-major)
    with open(X_path, 'wb') as f:
        X.tofile(f)
    print(f"✓ {X_path} ({X_path.stat().st_size:,} bytes)")

    # Write y
    with open(y_path, 'wb') as f:
        y.tofile(f)
    print(f"✓ {y_path} ({y_path.stat().st_size:,} bytes)")

    # Write close
    with open(close_path, 'wb') as f:
        close.tofile(f)
    print(f"✓ {close_path} ({close_path.stat().st_size:,} bytes)")

    # Write meta
    meta = {
        'timestamp': datetime.now().isoformat(),
        'rows': int(X.shape[0]),
        'cols': int(X.shape[1]),
        'label': args.label,
        'horizon': HORIZON,
        'feature_count': len(feature_pool),
        'time_min': str(t_min),
        'time_max': str(t_max),
        'forbidden_feature_count': forbidden_count,
        'commission_per_lot': COMMISSION_PER_1_LOT,
        'gold_oz_per_lot': GOLD_OZ_PER_LOT,
        'label_balance': float(balance),
        'dataset': str(args.dataset),
        'schema': str(args.schema)
    }

    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"✓ {meta_path}")

    # Write feature names
    with open(features_path, 'w') as f:
        for feat in feature_pool:
            f.write(feat + '\n')
    print(f"✓ {features_path}")

    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"Output dir: {args.output_dir}")
    print(f"Rows: {X.shape[0]:,}")
    print(f"Features: {X.shape[1]:,}")
    print(f"Label: {args.label}")
    print(f"Binary size: {(X_path.stat().st_size + y_path.stat().st_size + close_path.stat().st_size) / 1024 / 1024:.1f} MB")
    print("=" * 80)

if __name__ == '__main__':
    main()
