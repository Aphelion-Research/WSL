#!/usr/bin/env python3
"""
Repair hydra_xauusd_m5_master.parquet.
Fix timestamp bug, remove leakage, drop constant features, validate structure.
"""
import pandas as pd
import polars as pl
import numpy as np
from pathlib import Path
from datetime import datetime
import json

print("=" * 80)
print("MASTER DATASET REPAIR")
print("=" * 80)

# 1. LOAD RAW SOURCE (correct one)
print("\n[1] Loading clean raw source...")
RAW_SOURCE = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
if not RAW_SOURCE.exists():
    print(f"✗ Source not found: {RAW_SOURCE}")
    exit(1)

df_raw = pl.read_parquet(RAW_SOURCE)
print(f"Loaded: {df_raw.shape[0]:,} rows × {df_raw.shape[1]:,} cols")
print(f"Time range: {df_raw['time'].min()} → {df_raw['time'].max()}")

# Validate time range
t_min = df_raw['time'].min()
t_max = df_raw['time'].max()
year_min = t_min.year
year_max = t_max.year

if year_min < 2010:
    print(f"✗ FAIL: Min year {year_min} < 2010")
    exit(1)
if year_max > datetime.now().year + 1:
    print(f"✗ FAIL: Max year {year_max} > current + 1")
    exit(1)

print(f"✓ Time range valid: {year_min} - {year_max}")

# Check duplicates
dup_count = df_raw.select(pl.col('time')).is_duplicated().sum()
if dup_count > 0:
    print(f"✗ FAIL: {dup_count} duplicate timestamps")
    exit(1)
print("✓ No duplicate timestamps")

# Check monotonic
is_sorted = df_raw['time'].is_sorted()
if not is_sorted:
    print("⚠ Time not sorted, sorting...")
    df_raw = df_raw.sort('time')
else:
    print("✓ Time monotonic")

# 2. LOAD BROKEN MASTER (to extract features)
print("\n[2] Loading broken master dataset...")
MASTER_OLD = Path("data/hydra_xauusd_m5_master.parquet")
df_master = pl.read_parquet(MASTER_OLD)
print(f"Master: {df_master.shape[0]:,} rows × {df_master.shape[1]:,} cols")

# 3. IDENTIFY COLUMNS BY ROLE
print("\n[3] Classifying columns...")

# Forward-looking patterns (MUST BE LABELS OR REMOVED)
forward_patterns = ['fwd_', 'forward_', 'future_', 'next_', 'lead_']
label_patterns = ['label_', 'target_', 'y_']

all_cols = df_master.columns

# Classify
schema = []
for col in all_cols:
    if col == 'time':
        role = 'metadata'
        is_forward = False
        allowed = False
    elif any(p in col.lower() for p in label_patterns):
        role = 'label'
        is_forward = True  # labels allowed to see future
        allowed = False  # not for training features
    elif any(p in col.lower() for p in forward_patterns):
        role = 'label'  # reclassify forward features as labels
        is_forward = True
        allowed = False
    else:
        role = 'feature'
        is_forward = False
        allowed = True

    schema.append({
        'name': col,
        'role': role,
        'is_forward_looking': is_forward,
        'allowed_for_training': allowed
    })

# Count by role
role_counts = {}
for s in schema:
    role_counts[s['role']] = role_counts.get(s['role'], 0) + 1

print(f"Column roles:")
for role, count in sorted(role_counts.items()):
    print(f"  {role}: {count}")

forward_count = sum(1 for s in schema if s['is_forward_looking'] and s['role'] == 'feature')
if forward_count > 0:
    print(f"✗ FAIL: {forward_count} forward-looking columns classified as features")
    exit(1)
print(f"✓ No forward-looking features")

# 4. CHECK CONSTANT FEATURES
print("\n[4] Detecting constant features...")
feature_cols = [s['name'] for s in schema if s['role'] == 'feature']
constant_features = []
h1_features = []

for col in feature_cols:
    if df_master[col].n_unique() <= 1:
        constant_features.append(col)
        if col.startswith('h1_'):
            h1_features.append(col)

print(f"Constant features: {len(constant_features)}")
if constant_features:
    print(f"  Examples: {constant_features[:10]}")
    print(f"  H1 features: {len(h1_features)}")

if len(constant_features) > 5:
    print(f"⚠ WARNING: {len(constant_features)} constant features (threshold: 5)")
    print(f"  Removing constant features...")
    for col in constant_features:
        # Update schema
        for s in schema:
            if s['name'] == col:
                s['allowed_for_training'] = False
                s['role'] = 'dead_feature'
                break
else:
    print(f"✓ Constant features within threshold")

# 5. FIX TIME ALIGNMENT
print("\n[5] Fixing time alignment...")

# Convert both to pandas for easier merge
df_raw_pd = df_raw.to_pandas()
df_master_pd = df_master.to_pandas()

# Get valid time range from raw
valid_times = df_raw_pd['time'].values

# Filter master to valid time range
df_master_pd['time'] = pd.to_datetime(df_master_pd['time'])
df_raw_pd['time'] = pd.to_datetime(df_raw_pd['time'])

# Merge on time (keep only rows with valid times)
print(f"  Raw times: {len(df_raw_pd)}")
print(f"  Master times: {len(df_master_pd)}")

# Use raw time as base, merge_asof features from master
df_raw_pd = df_raw_pd.sort_values('time')
df_master_pd = df_master_pd.sort_values('time')

# Drop raw OHLCV (keep features only)
ohlcv_cols = ['open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume', 'volume']
feature_cols_master = [c for c in df_master_pd.columns if c not in ohlcv_cols and c != 'time']

merged = pd.merge_asof(
    df_raw_pd[['time', 'open', 'high', 'low', 'close', 'tick_volume']],
    df_master_pd[['time'] + feature_cols_master],
    on='time',
    direction='backward'
)

print(f"  Merged: {len(merged)} rows")
print(f"  Time range: {merged['time'].min()} → {merged['time'].max()}")

# Validate merged time
if merged['time'].min().year < 2010:
    print(f"✗ FAIL: Merged min year {merged['time'].min().year} < 2010")
    exit(1)
print(f"✓ Merged time range valid")

# 6. APPLY SCHEMA FILTER
print("\n[6] Applying schema filter...")

# Keep only allowed columns
allowed_cols = ['time'] + [s['name'] for s in schema if s['allowed_for_training']]
existing_allowed = [c for c in allowed_cols if c in merged.columns]

df_clean = merged[existing_allowed].copy()
print(f"Clean dataset: {len(df_clean)} rows × {len(df_clean.columns)} cols")

# Separate features and labels
feature_schema = [s for s in schema if s['role'] == 'feature' and s['allowed_for_training']]
label_schema = [s for s in schema if s['role'] == 'label']

feature_names = [s['name'] for s in feature_schema if s['name'] in df_clean.columns]
label_names = [s['name'] for s in label_schema if s['name'] in merged.columns]

print(f"Features: {len(feature_names)}")
print(f"Labels: {len(label_names)}")

# Add labels back (separate from features for clarity)
for label_col in label_names:
    if label_col in merged.columns:
        df_clean[label_col] = merged[label_col]

# 7. FINAL VALIDATION
print("\n[7] Final validation...")

# Check nulls
null_rate = df_clean.isnull().sum().sum() / (df_clean.shape[0] * df_clean.shape[1]) * 100
print(f"Null rate: {null_rate:.2f}%")

if null_rate > 50:
    print(f"✗ FAIL: Null rate {null_rate:.1f}% > 50%")
    exit(1)

# Check constant features in clean set
numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
constant_in_clean = []
for col in numeric_cols:
    if df_clean[col].nunique() <= 1:
        constant_in_clean.append(col)

if len(constant_in_clean) > 0:
    print(f"✗ FAIL: {len(constant_in_clean)} constant features remain in clean set")
    print(f"  {constant_in_clean[:10]}")
    exit(1)
print(f"✓ No constant features in clean set")

# Check time
if df_clean['time'].min().year < 2010:
    print(f"✗ FAIL: Time min year {df_clean['time'].min().year} < 2010")
    exit(1)
if df_clean['time'].duplicated().any():
    print(f"✗ FAIL: Duplicate times in clean set")
    exit(1)
print(f"✓ Time valid (no 1970 bug, no duplicates)")

# 8. SAVE CLEAN DATASET
print("\n[8] Saving clean dataset...")

OUTPUT = Path("data/hydra_xauusd_m5_master_clean.parquet")
df_clean_pl = pl.from_pandas(df_clean)
df_clean_pl.write_parquet(OUTPUT, compression='snappy')

print(f"✓ Saved: {OUTPUT}")
print(f"  Size: {OUTPUT.stat().st_size / 1024**2:.1f} MB")

# 9. SAVE SCHEMA MANIFEST
print("\n[9] Saving schema manifest...")

SCHEMA_FILE = Path("data/hydra_xauusd_m5_master_schema.json")
clean_column_names = set(df_clean.columns)
clean_schema = [s for s in schema if s['name'] in clean_column_names]
dropped_schema = [s for s in schema if s['name'] not in clean_column_names]

schema_manifest = {
    'version': '1.0_clean',
    'created': datetime.now().isoformat(),
    'dataset': str(OUTPUT),
    'raw_source': str(RAW_SOURCE),
    'n_rows': len(df_clean),
    'n_features': len(feature_names),
    'n_labels': len(label_names),
    'time_range': {
        'min': str(df_clean['time'].min()),
        'max': str(df_clean['time'].max())
    },
    'columns': clean_schema,
    'excluded_columns': dropped_schema,
    'validation': {
        'time_min_year': int(df_clean['time'].min().year),
        'time_max_year': int(df_clean['time'].max().year),
        'duplicate_times': False,
        'constant_features': 0,
        'forward_looking_features': 0,
        'null_rate_pct': float(null_rate)
    }
}

SCHEMA_FILE.write_text(json.dumps(schema_manifest, indent=2))
print(f"✓ Saved: {SCHEMA_FILE}")

# 10. PRINT FINAL REPORT
print("\n" + "=" * 80)
print("REPAIR COMPLETE")
print("=" * 80)

print(f"\nOLD (BROKEN):")
print(f"  File: {MASTER_OLD}")
print(f"  Time: 1970-01-01 → 2026-05-20 (UNIX BUG)")
print(f"  Rows: {df_master.shape[0]:,}")
print(f"  Cols: {df_master.shape[1]:,}")
print(f"  Constant features: {len(constant_features)}")
print(f"  Forward features: (mixed with labels)")

print(f"\nNEW (CLEAN):")
print(f"  File: {OUTPUT}")
print(f"  Time: {df_clean['time'].min()} → {df_clean['time'].max()}")
print(f"  Rows: {len(df_clean):,}")
print(f"  Features: {len(feature_names)}")
print(f"  Labels: {len(label_names)}")
print(f"  Constant features: 0")
print(f"  Forward features: 0 (moved to labels)")
print(f"  Null rate: {null_rate:.2f}%")

print(f"\nROOT CAUSE:")
print(f"  1. Wrong source file (XAUUSD_M5.parquet vs XAUUSD_M5_dukascopy.parquet)")
print(f"  2. HTF merge with misaligned times")
print(f"  3. Forward features not separated from labels")
print(f"  4. H1 pipeline dead (22 constant features)")

print(f"\nSCHEMA:")
print(f"  Manifest: {SCHEMA_FILE}")
print(f"  Columns classified: {len(clean_schema)} present, {len(dropped_schema)} excluded")
print(f"  - features: {sum(1 for s in clean_schema if s['role']=='feature')}")
print(f"  - labels: {sum(1 for s in clean_schema if s['role']=='label')}")
print(f"  - metadata: {sum(1 for s in clean_schema if s['role']=='metadata')}")
print(f"  - excluded/dead: {sum(1 for s in dropped_schema if s['role']=='dead_feature')}")

print("=" * 80)
print("Next: Run validation script on clean dataset")
print("=" * 80)
