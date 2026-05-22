#!/usr/bin/env python3
"""
Validate hydra_xauusd_m5_master_clean.parquet using schema manifest.
Structural validation only — no training yet.
"""
import polars as pl
import json
from pathlib import Path
from datetime import datetime

DATASET = Path("data/hydra_xauusd_m5_master_clean.parquet")
SCHEMA = Path("data/hydra_xauusd_m5_master_schema.json")

print("=" * 80)
print("CLEAN DATASET STRUCTURAL VALIDATION")
print("=" * 80)

# Load schema
if not SCHEMA.exists():
    print(f"✗ FAIL: Schema not found: {SCHEMA}")
    exit(1)

schema = json.loads(SCHEMA.read_text())
print(f"\nSchema version: {schema['version']}")
print(f"Created: {schema['created']}")

# Load dataset
if not DATASET.exists():
    print(f"✗ FAIL: Dataset not found: {DATASET}")
    exit(1)

df = pl.read_parquet(DATASET)
print(f"\nDataset: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

# Checks
checks_passed = 0
checks_total = 0

def check(name, condition, details=""):
    global checks_passed, checks_total
    checks_total += 1
    status = "✓" if condition else "✗"
    print(f"{status} {name}")
    if details:
        print(f"  {details}")
    if condition:
        checks_passed += 1
    return condition

# 1. Time column
print("\n[1] Time validation...")
time_col = 'time'
check("time_column_exists", time_col in df.columns)

if time_col in df.columns:
    t_min = df[time_col].min()
    t_max = df[time_col].max()

    check("time_min_year_valid", t_min.year >= 2010,
          f"Min: {t_min} (year {t_min.year})")

    check("time_max_year_valid", t_max.year <= datetime.now().year + 1,
          f"Max: {t_max} (year {t_max.year})")

    dup_count = df.select(pl.col(time_col)).is_duplicated().sum()
    check("no_duplicate_timestamps", dup_count == 0,
          f"Duplicates: {dup_count}")

    check("time_monotonic", df[time_col].is_sorted(),
          "Time is sorted ascending")

# 2. Schema alignment
print("\n[2] Schema validation...")
expected_cols = set(s['name'] for s in schema['columns'])
actual_cols = set(df.columns)

missing = expected_cols - actual_cols
extra = actual_cols - expected_cols

check("no_missing_columns", len(missing) == 0,
      f"Missing: {list(missing)[:5] if missing else 'none'}")

check("no_extra_columns", len(extra) == 0,
      f"Extra: {list(extra)[:5] if extra else 'none'}")

# 3. Feature/label separation
print("\n[3] Feature/label separation...")
feature_cols = [s['name'] for s in schema['columns'] if s['role'] == 'feature' and s['allowed_for_training']]
label_cols = [s['name'] for s in schema['columns'] if s['role'] == 'label']

feature_cols_exist = [c for c in feature_cols if c in df.columns]
label_cols_exist = [c for c in label_cols if c in df.columns]

check("features_present", len(feature_cols_exist) > 0,
      f"Features: {len(feature_cols_exist)}")

check("labels_present", len(label_cols_exist) > 0,
      f"Labels: {len(label_cols_exist)}")

# Check no forward-looking in features
forward_in_features = [
    s['name'] for s in schema['columns']
    if s['role'] == 'feature' and s['is_forward_looking'] and s['name'] in df.columns
]

check("no_forward_looking_features", len(forward_in_features) == 0,
      f"Forward features: {forward_in_features if forward_in_features else 'none'}")

# 4. Constant features
print("\n[4] Constant features check...")
numeric_cols = [c for c in df.columns if df[c].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]]
constant_features = []

for col in numeric_cols:
    if col == 'time':
        continue
    if df[col].n_unique() <= 1:
        constant_features.append(col)

check("no_constant_features", len(constant_features) <= 5,
      f"Constant: {len(constant_features)} (threshold: 5)")

if constant_features:
    print(f"  Examples: {constant_features[:10]}")

# 5. Null rate
print("\n[5] Missing data...")
total_cells = df.shape[0] * df.shape[1]
null_counts = df.null_count()
total_nulls = null_counts.sum_horizontal()[0]
null_rate = (total_nulls / total_cells * 100) if total_cells > 0 else 0

check("acceptable_null_rate", null_rate < 10,
      f"Null rate: {null_rate:.2f}%")

# 6. Infinite values
print("\n[6] Infinite values...")
inf_cols = []
for col in numeric_cols:
    if col == 'time':
        continue
    if df[col].is_infinite().any():
        inf_cols.append(col)

check("no_infinite_values", len(inf_cols) == 0,
      f"Columns with inf: {len(inf_cols)}")

# 7. Schema manifest validation
print("\n[7] Schema manifest checks...")
check("schema_validation_passed",
      schema['validation']['time_min_year'] >= 2010,
      f"Min year: {schema['validation']['time_min_year']}")

check("no_duplicate_times_schema",
      not schema['validation']['duplicate_times'],
      "Duplicate times: False")

check("constant_features_schema",
      schema['validation']['constant_features'] == 0,
      f"Constant: {schema['validation']['constant_features']}")

check("forward_features_schema",
      schema['validation']['forward_looking_features'] == 0,
      f"Forward: {schema['validation']['forward_looking_features']}")

# Summary
print("\n" + "=" * 80)
print(f"CHECKS PASSED: {checks_passed}/{checks_total}")
print("=" * 80)

if checks_passed == checks_total:
    verdict = "MASTER_CLEAN_READY_FOR_RESEARCH"
    print(f"\n✓ VERDICT: {verdict}")
    print("  All structural checks passed.")
    print("  Dataset ready for training validation.")
    exit(0)
elif checks_passed >= checks_total * 0.8:
    verdict = "MASTER_STILL_NEEDS_REPAIR"
    print(f"\n⚠ VERDICT: {verdict}")
    print("  Some checks failed. Review and fix.")
    exit(1)
else:
    verdict = "MASTER_INVALID"
    print(f"\n✗ VERDICT: {verdict}")
    print("  Too many failures. Dataset unusable.")
    exit(1)
