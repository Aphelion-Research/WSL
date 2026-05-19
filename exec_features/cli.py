"""Execution features CLI."""
import sys
import duckdb
import pandas as pd
from pathlib import Path
from exec_features.config import DUCKDB_PATH, IC_STRONG_THRESHOLD
from exec_features.schema import init_exec_features_schema
from exec_features.store import compute_all_features, store_features


def load_lob_data(db_path: Path, limit: int = 1000) -> pd.DataFrame:
    """Load LOB data for feature computation.

    Args:
        db_path: DuckDB path
        limit: Row limit

    Returns:
        DataFrame with LOB data
    """
    conn = duckdb.connect(str(db_path))

    # Load from lob_metrics
    df = conn.execute(f"""
        SELECT m.timestamp, m.spread, m.ofi_1s, m.ofi_5s, m.ofi_1m, m.vpin,
               m.depth_imbalance, m.bid_depth, m.ask_depth
        FROM lob_metrics m
        ORDER BY m.timestamp
        LIMIT {limit}
    """).fetchdf()

    conn.close()

    if df.empty:
        print("WARNING: No LOB data, generating synthetic")
        timestamps = pd.date_range('2024-01-01', periods=100, freq='1min')
        df = pd.DataFrame({
            'timestamp': timestamps,
            'spread': 0.5,
            'ofi_1s': 0.0,
            'ofi_5s': 0.0,
            'ofi_1m': 0.0,
            'vpin': 0.3,
            'depth_imbalance': 0.0,
            'bid_depth': 10.0,
            'ask_depth': 10.0
        })

    # Add required columns for feature computation
    df['bid'] = 2000.0
    df['ask'] = 2000.5
    df['bid_size'] = df.get('bid_depth', 10.0)
    df['ask_size'] = df.get('ask_depth', 10.0)
    df['volume'] = 1.0

    return df


def cmd_compute():
    """Compute all 50 execution features."""
    print("Initializing exec features schema...")
    init_exec_features_schema(DUCKDB_PATH)

    print("Loading LOB data...")
    df = load_lob_data(DUCKDB_PATH, limit=10000)

    print(f"Computing 50 features for {len(df)} rows...")
    ofi_df = df[['timestamp', 'ofi_1s', 'ofi_5s', 'ofi_1m']] if 'ofi_1s' in df.columns else pd.DataFrame()
    features = compute_all_features(df, ofi_df)

    print("Storing features...")
    rows = store_features(features, DUCKDB_PATH)

    print(f"✓ Stored {rows} feature values ({len(features)} timestamps × {len(features.columns)-1} features)")
    return 0


def cmd_top(min_ic: float = IC_STRONG_THRESHOLD):
    """Show top features by IC.

    Args:
        min_ic: Minimum |IC| threshold
    """
    conn = duckdb.connect(str(DUCKDB_PATH))

    df = conn.execute(f"""
        SELECT feature_name, AVG(ic_60) as avg_ic, COUNT(*) as n_obs
        FROM execution_features
        WHERE ABS(ic_60) >= {min_ic}
        GROUP BY feature_name
        ORDER BY ABS(avg_ic) DESC
        LIMIT 20
    """).fetchdf()

    conn.close()

    if df.empty:
        print(f"No features with |IC| >= {min_ic}")
        return 0

    print(f"\n=== Top Features (|IC| >= {min_ic}) ===\n")
    print(df.to_string(index=False))

    return 0


def cmd_decay():
    """Check for features with IC decay."""
    from exec_features.ic_tracker import check_feature_decay

    df = check_feature_decay(DUCKDB_PATH)

    if df.empty:
        print("No significant IC decay detected")
        return 0

    print("\n=== Feature Decay Alerts ===\n")
    print(df.to_string(index=False))

    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m exec_features.cli <command>")
        print("Commands: compute, top, decay")
        return 1

    command = sys.argv[1]

    if command == "compute":
        return cmd_compute()
    elif command == "top":
        min_ic = IC_STRONG_THRESHOLD
        if len(sys.argv) > 3 and sys.argv[2] == '--min-ic':
            min_ic = float(sys.argv[3])
        return cmd_top(min_ic)
    elif command == "decay":
        return cmd_decay()
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
