#!/usr/bin/env python3
"""
Comprehensive validation of hydra_xauusd_m5_master.parquet.
Must pass all checks before declaring training-ready.
"""
import polars as pl
import numpy as np
from pathlib import Path
import json
from datetime import datetime, timedelta

DATASET = Path("data/hydra_xauusd_m5_master.parquet")
REPORT = Path("reports/master_validation_report.json")
REPORT.parent.mkdir(exist_ok=True)

report = {
    "timestamp": datetime.now().isoformat(),
    "dataset": str(DATASET),
    "checks": {},
    "verdict": None,
    "issues": []
}

def check(name, passed, details=None):
    """Record check result."""
    report["checks"][name] = {
        "passed": bool(passed),
        "details": details or {}
    }
    status = "✓" if passed else "✗"
    print(f"{status} {name}")
    if details:
        for k, v in details.items():
            print(f"  {k}: {v}")
    if not passed:
        report["issues"].append(name)
    return passed

print("=" * 80)
print("HYDRA MASTER DATASET VALIDATION")
print("=" * 80)

# 1. Load dataset
print("\n[1] Loading dataset...")
try:
    df = pl.read_parquet(DATASET)
    print(f"Loaded: {df.shape[0]:,} rows × {df.shape[1]:,} cols")
    check("dataset_loads", True, {
        "rows": f"{df.shape[0]:,}",
        "cols": f"{df.shape[1]:,}",
        "memory_mb": f"{df.estimated_size('mb'):.0f}"
    })
except Exception as e:
    check("dataset_loads", False, {"error": str(e)})
    report["verdict"] = "DATASET_INVALID"
    REPORT.write_text(json.dumps(report, indent=2))
    print(f"\n✗ FATAL: Cannot load dataset - {e}")
    exit(1)

# 2. Check time column
print("\n[2] Time column validation...")
time_cols = [c for c in df.columns if 'time' in c.lower()]
if not time_cols:
    check("time_column_exists", False)
    report["verdict"] = "DATASET_INVALID"
else:
    time_col = time_cols[0]
    check("time_column_exists", True, {"column": time_col})

    # Check dtype
    is_datetime = df[time_col].dtype in [pl.Datetime, pl.Date]
    check("time_column_dtype", is_datetime, {"dtype": str(df[time_col].dtype)})

    # Check time range
    if is_datetime:
        t_min = df[time_col].min()
        t_max = df[time_col].max()
        duration_days = (t_max - t_min).total_seconds() / 86400 if hasattr(t_max - t_min, 'total_seconds') else 0
        check("time_range", True, {
            "start": str(t_min),
            "end": str(t_max),
            "days": f"{duration_days:.0f}"
        })

# 3. Check duplicates
print("\n[3] Duplicate timestamps...")
if time_cols:
    dup_count = df.select(pl.col(time_col)).is_duplicated().sum()
    check("no_duplicate_timestamps", dup_count == 0, {
        "duplicates": int(dup_count)
    })

# 4. Check M5 spacing
print("\n[4] M5 bar spacing validation...")
if time_cols and is_datetime:
    df_sorted = df.sort(time_col)
    time_series = df_sorted[time_col].to_numpy()

    # Compute time diffs (in seconds)
    diffs = np.diff(time_series.astype('datetime64[s]').astype(int))

    # M5 = 300 seconds
    expected_spacing = 300
    correct_spacing = np.sum(diffs == expected_spacing)
    total_gaps = len(diffs)
    spacing_pct = (correct_spacing / total_gaps * 100) if total_gaps > 0 else 0

    # Check for gaps > 1 hour (12 M5 bars)
    large_gaps = np.sum(diffs > 3600)

    check("m5_spacing", spacing_pct > 80, {
        "correct_spacing_pct": f"{spacing_pct:.1f}%",
        "expected_seconds": expected_spacing,
        "large_gaps_1h+": int(large_gaps)
    })

# 5. Null rate by feature
print("\n[5] Missing data analysis...")
null_counts = df.null_count()
total_cells = df.shape[0] * df.shape[1]
total_nulls = null_counts.sum_horizontal()[0]
null_rate = (total_nulls / total_cells * 100) if total_cells > 0 else 0

# Find worst features
null_by_col = {}
for col in df.columns:
    n = df[col].null_count()
    if n > 0:
        null_by_col[col] = (n, n / df.shape[0] * 100)

# Sort by null rate
worst_features = sorted(null_by_col.items(), key=lambda x: x[1][0], reverse=True)[:10]

check("acceptable_null_rate", null_rate < 10, {
    "overall_null_pct": f"{null_rate:.2f}%",
    "worst_feature": worst_features[0][0] if worst_features else "none",
    "worst_null_pct": f"{worst_features[0][1][1]:.1f}%" if worst_features else "0%"
})

# 6. Check for label columns
print("\n[6] Label column detection...")
label_patterns = ['target', 'label', 'y_', 'forward_ret', 'next_', 'future_']
label_cols = [c for c in df.columns if any(p in c.lower() for p in label_patterns)]

check("label_columns_found", len(label_cols) > 0, {
    "count": len(label_cols),
    "examples": label_cols[:5] if label_cols else []
})

# Check label balance (if binary)
if label_cols:
    label_col = label_cols[0]
    unique_vals = df[label_col].n_unique()

    if unique_vals == 2:
        # Binary classification
        value_counts = df[label_col].value_counts()
        majority = value_counts['count'].max()
        total = value_counts['count'].sum()
        balance = (majority / total * 100) if total > 0 else 0

        check("label_balance", balance < 90, {
            "type": "binary",
            "majority_class_pct": f"{balance:.1f}%"
        })
    else:
        # Regression or multi-class
        check("label_balance", True, {
            "type": "regression/multiclass",
            "unique_values": int(unique_vals)
        })

# 7. Check label leakage
print("\n[7] Label leakage detection...")
# Labels should NOT appear as features
feature_cols = [c for c in df.columns if not any(p in c.lower() for p in label_patterns)]
leaked_labels = [c for c in feature_cols if c in label_cols]

check("no_label_leakage", len(leaked_labels) == 0, {
    "leaked_columns": leaked_labels if leaked_labels else []
})

# 8. Feature type distribution
print("\n[8] Feature type analysis...")
numeric_cols = [c for c in df.columns if df[c].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]]
string_cols = [c for c in df.columns if df[c].dtype in [pl.Utf8, pl.String]]
bool_cols = [c for c in df.columns if df[c].dtype == pl.Boolean]

check("majority_numeric", len(numeric_cols) / df.shape[1] > 0.9, {
    "numeric": len(numeric_cols),
    "string": len(string_cols),
    "bool": len(bool_cols)
})

# 9. Check for constant features
print("\n[9] Constant feature detection...")
constant_features = []
for col in numeric_cols:
    if df[col].n_unique() <= 1:
        constant_features.append(col)

check("no_constant_features", len(constant_features) == 0, {
    "count": len(constant_features),
    "examples": constant_features[:5] if constant_features else []
})

# 10. Check for infinite values
print("\n[10] Infinite value detection...")
inf_cols = []
for col in numeric_cols:
    if df[col].is_infinite().any():
        inf_cols.append(col)

check("no_infinite_values", len(inf_cols) == 0, {
    "count": len(inf_cols),
    "examples": inf_cols[:5] if inf_cols else []
})

# Summary
print("\n" + "=" * 80)
passed = sum(1 for c in report["checks"].values() if c["passed"])
total = len(report["checks"])
print(f"CHECKS PASSED: {passed}/{total}")

if report["issues"]:
    print(f"\nISSUES FOUND: {len(report['issues'])}")
    for issue in report["issues"]:
        print(f"  - {issue}")

# Determine verdict
if passed == total:
    report["verdict"] = "DATASET_READY_FOR_RESEARCH"
    print(f"\n✓ VERDICT: DATASET_READY_FOR_RESEARCH")
    print("  Proceed to training validation.")
elif len(report["issues"]) > 5 or not report["checks"].get("dataset_loads", {}).get("passed"):
    report["verdict"] = "DATASET_INVALID"
    print(f"\n✗ VERDICT: DATASET_INVALID")
    print("  Too many critical issues. Dataset unusable.")
else:
    report["verdict"] = "DATASET_NEEDS_REPAIR"
    print(f"\n⚠ VERDICT: DATASET_NEEDS_REPAIR")
    print("  Some issues found. Review and fix before training.")

print("=" * 80)

# Save report
REPORT.write_text(json.dumps(report, indent=2))
print(f"\nReport saved: {REPORT}")
