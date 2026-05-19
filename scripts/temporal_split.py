#!/usr/bin/env python3
"""Temporal train/val/test split for Dominion dataset v1.

No shuffling. Chronological split to prevent leakage.
"""
import duckdb
from datetime import datetime
from pathlib import Path
import json

# Config
DUCKDB_PATH = Path(__file__).parent.parent / "data" / "dominion.duckdb"
SPLIT_CONFIG = {
    "train_pct": 0.70,
    "val_pct": 0.15,
    "test_pct": 0.15,
}

# Excluded features (leakage-contaminated per audit)
EXCLUDED_FEATURES = [
    "regime_tactical",
    "regime_prob_trend_up",
    "regime_prob_trend_down",
    "regime_prob_ranging",
    "regime_prob_crisis",
]


def compute_split_dates(conn):
    """Compute train/val/test split boundaries."""
    # Get date range
    result = conn.execute("""
        SELECT
            MIN(timestamp) as min_ts,
            MAX(timestamp) as max_ts,
            COUNT(*) as total_rows
        FROM gold_master
    """).fetchone()

    min_ts, max_ts, total_rows = result

    # Compute split row indices
    train_end_idx = int(total_rows * SPLIT_CONFIG["train_pct"])
    val_end_idx = train_end_idx + int(total_rows * SPLIT_CONFIG["val_pct"])

    # Get timestamps at split boundaries
    train_end_ts = conn.execute(f"""
        SELECT timestamp
        FROM (
            SELECT timestamp, ROW_NUMBER() OVER (ORDER BY timestamp) as rn
            FROM gold_master
        )
        WHERE rn = {train_end_idx}
    """).fetchone()[0]

    val_end_ts = conn.execute(f"""
        SELECT timestamp
        FROM (
            SELECT timestamp, ROW_NUMBER() OVER (ORDER BY timestamp) as rn
            FROM gold_master
        )
        WHERE rn = {val_end_idx}
    """).fetchone()[0]

    # Compute actual row counts
    train_rows = conn.execute(f"""
        SELECT COUNT(*) FROM gold_master WHERE timestamp <= '{train_end_ts}'
    """).fetchone()[0]

    val_rows = conn.execute(f"""
        SELECT COUNT(*) FROM gold_master
        WHERE timestamp > '{train_end_ts}' AND timestamp <= '{val_end_ts}'
    """).fetchone()[0]

    test_rows = conn.execute(f"""
        SELECT COUNT(*) FROM gold_master WHERE timestamp > '{val_end_ts}'
    """).fetchone()[0]

    return {
        "total_rows": total_rows,
        "date_range": {"min": str(min_ts), "max": str(max_ts)},
        "train": {
            "date_range": {"start": str(min_ts), "end": str(train_end_ts)},
            "rows": train_rows,
            "pct": round(train_rows / total_rows, 4),
        },
        "val": {
            "date_range": {"start": str(train_end_ts), "end": str(val_end_ts)},
            "rows": val_rows,
            "pct": round(val_rows / total_rows, 4),
        },
        "test": {
            "date_range": {"start": str(val_end_ts), "end": str(max_ts)},
            "rows": test_rows,
            "pct": round(test_rows / total_rows, 4),
        },
    }


def list_available_features(conn):
    """List all feature columns in gold_master."""
    cols = conn.execute("DESCRIBE gold_master").fetchall()

    # Exclude system columns
    system_cols = {"timestamp", "close", "high", "low", "open", "volume", "source", "trust", "anomaly_flag"}
    feature_cols = [col[0] for col in cols if col[0] not in system_cols]

    # Separate safe vs excluded
    safe_features = [f for f in feature_cols if f not in EXCLUDED_FEATURES]
    excluded_found = [f for f in feature_cols if f in EXCLUDED_FEATURES]

    return {
        "total": len(feature_cols),
        "safe": safe_features,
        "excluded": excluded_found,
        "excluded_expected": EXCLUDED_FEATURES,
    }


def validate_split(split_info):
    """Validate split meets requirements."""
    issues = []

    # Check percentages
    total_pct = split_info["train"]["pct"] + split_info["val"]["pct"] + split_info["test"]["pct"]
    if abs(total_pct - 1.0) > 0.01:
        issues.append(f"Split percentages don't sum to 1.0: {total_pct}")

    # Check train >= 60%
    if split_info["train"]["pct"] < 0.60:
        issues.append(f"Train split too small: {split_info['train']['pct']} < 0.60")

    # Check val, test >= 10% each
    if split_info["val"]["pct"] < 0.10:
        issues.append(f"Val split too small: {split_info['val']['pct']} < 0.10")
    if split_info["test"]["pct"] < 0.10:
        issues.append(f"Test split too small: {split_info['test']['pct']} < 0.10")

    # Check chronological order
    train_end = datetime.fromisoformat(split_info["train"]["date_range"]["end"])
    val_start = datetime.fromisoformat(split_info["val"]["date_range"]["start"])
    val_end = datetime.fromisoformat(split_info["val"]["date_range"]["end"])
    test_start = datetime.fromisoformat(split_info["test"]["date_range"]["start"])

    if train_end != val_start:
        issues.append(f"Train end != Val start: {train_end} != {val_start}")
    if val_end != test_start:
        issues.append(f"Val end != Test start: {val_end} != {test_start}")

    return issues


def main():
    """Compute and validate temporal split."""
    print("Temporal Split for Dominion Dataset v1")
    print("=" * 60)

    # Connect to DuckDB
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Compute split
    print("\nComputing split boundaries...")
    split_info = compute_split_dates(conn)

    # List features
    print("\nInventorying features...")
    feature_info = list_available_features(conn)

    # Validate
    print("\nValidating split...")
    issues = validate_split(split_info)

    # Print results
    print("\n" + "=" * 60)
    print("SPLIT SUMMARY")
    print("=" * 60)

    print(f"\nTotal rows: {split_info['total_rows']}")
    print(f"Date range: {split_info['date_range']['min']} to {split_info['date_range']['max']}")

    print(f"\nTRAIN:")
    print(f"  Rows: {split_info['train']['rows']} ({split_info['train']['pct']:.1%})")
    print(f"  Dates: {split_info['train']['date_range']['start']} to {split_info['train']['date_range']['end']}")

    print(f"\nVAL:")
    print(f"  Rows: {split_info['val']['rows']} ({split_info['val']['pct']:.1%})")
    print(f"  Dates: {split_info['val']['date_range']['start']} to {split_info['val']['date_range']['end']}")

    print(f"\nTEST:")
    print(f"  Rows: {split_info['test']['rows']} ({split_info['test']['pct']:.1%})")
    print(f"  Dates: {split_info['test']['date_range']['start']} to {split_info['test']['date_range']['end']}")

    print(f"\n" + "=" * 60)
    print("FEATURES")
    print("=" * 60)
    print(f"\nTotal feature columns: {feature_info['total']}")
    print(f"Safe features: {len(feature_info['safe'])}")
    print(f"Excluded (leakage): {len(feature_info['excluded'])}")

    if feature_info['excluded']:
        print(f"\nExcluded features found in dataset:")
        for feat in feature_info['excluded']:
            print(f"  - {feat}")

    missing_excluded = set(EXCLUDED_FEATURES) - set(feature_info['excluded'])
    if missing_excluded:
        print(f"\nExpected exclusions not in dataset (OK if never added):")
        for feat in missing_excluded:
            print(f"  - {feat}")

    # Validation
    print(f"\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)

    if issues:
        print("\n❌ VALIDATION FAILED:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    else:
        print("\n✓ All validation checks passed")

    # Save to file
    output_path = Path(__file__).parent.parent / "reports" / "temporal_split_v1.json"
    output_data = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "split": split_info,
        "features": feature_info,
        "validation": {"passed": len(issues) == 0, "issues": issues},
    }

    output_path.write_text(json.dumps(output_data, indent=2))
    print(f"\n✓ Split info saved to: {output_path}")

    return 0


if __name__ == "__main__":
    exit(main())
