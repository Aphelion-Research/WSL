#!/usr/bin/env python3
"""Build Dominion dataset v1 for machine learning.

Steps:
1. Pivot features from long to wide format
2. Join to gold_master
3. Exclude leakage features
4. Add target variables (forward returns)
5. Drop NaN rows
6. Split by temporal boundaries
7. Save to Parquet
8. Compute hashes
9. Write manifest
"""
import duckdb
import pandas as pd
import hashlib
import json
from pathlib import Path
from datetime import datetime

# Config
REPO_ROOT = Path(__file__).parent.parent
DUCKDB_PATH = REPO_ROOT / "data" / "dominion.duckdb"
OUTPUT_DIR = REPO_ROOT / "data"

# Excluded features (leakage per audit)
EXCLUDED_FEATURES = [
    "regime_tactical",
    "regime_prob_trend_up",
    "regime_prob_trend_down",
    "regime_prob_ranging",
    "regime_prob_crisis",
]

# Split boundaries (from temporal_split.py)
TRAIN_END = "2024-11-15"
VAL_END = "2025-08-18"


def pivot_features(conn):
    """Pivot features from long to wide format."""
    print("Pivoting features table...")

    # Get feature completeness
    print("  Checking feature completeness...")
    completeness = conn.execute("""
        SELECT
            feature_name,
            COUNT(*) as row_count,
            COUNT(DISTINCT timestamp) as unique_timestamps
        FROM features
        WHERE feature_name NOT IN ({})
        GROUP BY feature_name
        HAVING COUNT(DISTINCT timestamp) >= 1000  -- At least 1000 rows (80% of 1256)
        ORDER BY row_count DESC
    """.format(','.join(f"'{f}'" for f in EXCLUDED_FEATURES))).df()

    print(f"  Found {len(completeness)} features with >=1000 timestamps")

    # Get list of feature names (only complete features)
    feature_names = completeness['feature_name'].tolist()

    print(f"  Using {len(feature_names)} complete features")

    # Build dynamic pivot query (quote column names with dots/special chars)
    pivot_cols = [
        f"MAX(CASE WHEN feature_name = '{fname}' THEN feature_value END) as \"{fname}\""
        for fname in feature_names
    ]

    pivot_query = f"""
        SELECT
            timestamp,
            {','.join(pivot_cols)}
        FROM features
        WHERE feature_name NOT IN ({','.join(f"'{f}'" for f in EXCLUDED_FEATURES)})
        GROUP BY timestamp
        ORDER BY timestamp
    """

    print("  Executing pivot (this may take 30-60s)...")
    features_wide = conn.execute(pivot_query).df()
    print(f"  Result: {len(features_wide)} rows, {len(features_wide.columns)} columns")

    return features_wide


def join_to_gold_master(conn, features_wide):
    """Join features to gold_master."""
    print("\nJoining to gold_master...")

    gold = conn.execute("""
        SELECT timestamp, close, high, low, open, volume
        FROM gold_master
        ORDER BY timestamp
    """).df()

    print(f"  Gold master: {len(gold)} rows")

    # Join
    dataset = gold.merge(features_wide, on='timestamp', how='left')
    print(f"  Joined: {len(dataset)} rows, {len(dataset.columns)} columns")

    return dataset


def add_target_variables(dataset):
    """Add forward return targets."""
    print("\nAdding target variables...")

    # 1-day forward return
    dataset['target_return_1'] = dataset['close'].pct_change(1).shift(-1)

    # 5-day forward return
    dataset['target_return_5'] = dataset['close'].pct_change(5).shift(-5)

    # 10-day forward return
    dataset['target_return_10'] = dataset['close'].pct_change(10).shift(-10)

    print(f"  Added: target_return_1, target_return_5, target_return_10")

    return dataset


def drop_nan_rows(dataset):
    """Drop rows with any NaN values."""
    print("\nDropping NaN rows...")

    before = len(dataset)
    dataset_clean = dataset.dropna()
    after = len(dataset_clean)
    dropped = before - after

    print(f"  Before: {before} rows")
    print(f"  After: {after} rows")
    print(f"  Dropped: {dropped} rows ({dropped/before:.1%})")

    return dataset_clean


def temporal_split(dataset):
    """Split by temporal boundaries."""
    print("\nSplitting by temporal boundaries...")

    # Convert timestamp to datetime if string
    if dataset['timestamp'].dtype == 'object':
        dataset['timestamp'] = pd.to_datetime(dataset['timestamp'])

    train = dataset[dataset['timestamp'] <= TRAIN_END].copy()
    val = dataset[(dataset['timestamp'] > TRAIN_END) & (dataset['timestamp'] <= VAL_END)].copy()
    test = dataset[dataset['timestamp'] > VAL_END].copy()

    print(f"  Train: {len(train)} rows ({len(train)/len(dataset):.1%})")
    print(f"  Val: {len(val)} rows ({len(val)/len(dataset):.1%})")
    print(f"  Test: {len(test)} rows ({len(test)/len(dataset):.1%})")

    return train, val, test


def save_to_parquet(train, val, test):
    """Save splits to Parquet."""
    print("\nSaving to Parquet...")

    train_path = OUTPUT_DIR / "train_v1.parquet"
    val_path = OUTPUT_DIR / "val_v1.parquet"
    test_path = OUTPUT_DIR / "test_v1.parquet"

    train.to_parquet(train_path, index=False)
    val.to_parquet(val_path, index=False)
    test.to_parquet(test_path, index=False)

    print(f"  Train: {train_path} ({train_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  Val: {val_path} ({val_path.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"  Test: {test_path} ({test_path.stat().st_size / 1024 / 1024:.1f} MB)")

    return train_path, val_path, test_path


def compute_hash(df):
    """Compute SHA-256 hash of dataframe."""
    csv_str = df.to_csv(index=False)
    return hashlib.sha256(csv_str.encode()).hexdigest()


def compute_feature_stats(train):
    """Compute feature statistics on train set only."""
    print("\nComputing feature stats (train only)...")

    # Exclude system columns
    system_cols = ['timestamp', 'close', 'high', 'low', 'open', 'volume',
                   'target_return_1', 'target_return_5', 'target_return_10']
    feature_cols = [col for col in train.columns if col not in system_cols]

    stats = train[feature_cols].describe().T
    stats['missing_pct'] = train[feature_cols].isna().mean()

    print(f"  Computed stats for {len(feature_cols)} features")

    return stats


def write_manifest(train, val, test, train_path, val_path, test_path):
    """Write dataset manifest."""
    print("\nWriting manifest...")

    # Compute hashes
    print("  Computing hashes (may take 30s)...")
    train_hash = compute_hash(train)
    val_hash = compute_hash(val)
    test_hash = compute_hash(test)

    # Feature list
    system_cols = ['timestamp', 'close', 'high', 'low', 'open', 'volume',
                   'target_return_1', 'target_return_5', 'target_return_10']
    feature_cols = [col for col in train.columns if col not in system_cols]

    manifest = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "description": "Dominion dataset v1 for ML training",

        "split_boundaries": {
            "train_end": TRAIN_END,
            "val_end": VAL_END,
        },

        "row_counts": {
            "train": len(train),
            "val": len(val),
            "test": len(test),
            "total": len(train) + len(val) + len(test),
        },

        "column_counts": {
            "total": len(train.columns),
            "features": len(feature_cols),
            "ohlcv": 5,
            "targets": 3,
            "timestamp": 1,
        },

        "features": {
            "total": len(feature_cols),
            "excluded_leakage": EXCLUDED_FEATURES,
            "categories": {
                "price": [f for f in feature_cols if f.startswith('return_') or f.startswith('log_return_')],
                "volatility": [f for f in feature_cols if 'vol' in f.lower() or 'std' in f],
                "microstructure": [f for f in feature_cols if any(x in f for x in ['spread', 'depth', 'vpin', 'ofi'])],
                "macro": [f for f in feature_cols if any(x in f for x in ['dxy', 'vix', 'fed', 'cpi'])],
                "regime": [f for f in feature_cols if f.startswith('regime_micro')],
                "other": [],  # Computed below
            }
        },

        "hashes": {
            "train": train_hash,
            "val": val_hash,
            "test": test_hash,
        },

        "files": {
            "train": str(train_path),
            "val": str(val_path),
            "test": str(test_path),
        },

        "data_quality": {
            "nan_rows_dropped": 1256 - (len(train) + len(val) + len(test)),  # Total gold_master rows - clean rows
            "features_with_nans": 0,  # All NaN rows dropped
            "feature_completeness_threshold": 1000,  # Min timestamps per feature
        }
    }

    # Compute "other" category
    categorized = set()
    for cat_name, cat_features in manifest['features']['categories'].items():
        if cat_name != 'other':
            categorized.update(cat_features)
    manifest['features']['categories']['other'] = [f for f in feature_cols if f not in categorized]

    # Save
    manifest_path = REPO_ROOT / "reports" / "dataset_v1_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"  Manifest: {manifest_path}")

    return manifest


def main():
    """Build dataset v1."""
    print("=" * 60)
    print("Building Dominion Dataset v1")
    print("=" * 60)

    # Connect
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Build dataset
    features_wide = pivot_features(conn)
    dataset = join_to_gold_master(conn, features_wide)
    dataset = add_target_variables(dataset)
    dataset = drop_nan_rows(dataset)

    # Split
    train, val, test = temporal_split(dataset)

    # Save
    train_path, val_path, test_path = save_to_parquet(train, val, test)

    # Stats
    stats = compute_feature_stats(train)
    stats_path = OUTPUT_DIR / "train_v1_feature_stats.csv"
    stats.to_csv(stats_path)
    print(f"  Feature stats: {stats_path}")

    # Manifest
    manifest = write_manifest(train, val, test, train_path, val_path, test_path)

    # Summary
    print("\n" + "=" * 60)
    print("DATASET V1 COMPLETE")
    print("=" * 60)
    print(f"\nTotal rows: {len(train) + len(val) + len(test)}")
    print(f"Total features: {manifest['column_counts']['features']}")
    print(f"Train: {len(train)} rows ({len(train)/(len(train)+len(val)+len(test)):.1%})")
    print(f"Val: {len(val)} rows ({len(val)/(len(train)+len(val)+len(test)):.1%})")
    print(f"Test: {len(test)} rows ({len(test)/(len(train)+len(val)+len(test)):.1%})")

    print(f"\nFeature categories:")
    for cat, feats in manifest['features']['categories'].items():
        print(f"  {cat}: {len(feats)} features")

    print(f"\nFiles:")
    print(f"  {train_path}")
    print(f"  {val_path}")
    print(f"  {test_path}")
    print(f"  {stats_path}")
    print(f"  reports/dataset_v1_manifest.json")

    print("\n✓ Dataset ready for training")

    return 0


if __name__ == "__main__":
    exit(main())
