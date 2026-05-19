"""LOB CLI commands."""
import sys
import json
import duckdb
from pathlib import Path
from lob.config import DUCKDB_PATH
from lob.schema import init_lob_schema
from lob.ingestion import prepare_lob_data
from lob.metrics import compute_all_metrics


def cmd_compute():
    """Compute LOB metrics and store to DuckDB."""
    print("Initializing LOB schema...")
    init_lob_schema(DUCKDB_PATH)

    print("Loading tick data...")
    df = prepare_lob_data(DUCKDB_PATH, limit=10000)

    if df.empty:
        print("ERROR: No tick data available")
        return 1

    print(f"Computing metrics for {len(df)} ticks...")
    metrics = compute_all_metrics(df)

    print("Storing metrics to DuckDB...")
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Clear existing metrics
    conn.execute("DELETE FROM lob_metrics")

    # Insert new metrics
    conn.execute("""
        INSERT INTO lob_metrics
        SELECT * FROM metrics
    """, {"metrics": metrics})

    rows_inserted = conn.execute("SELECT COUNT(*) FROM lob_metrics").fetchone()[0]
    conn.close()

    print(f"✓ Stored {rows_inserted} metric rows to lob_metrics")
    return 0


def cmd_metrics(top_k: int = 20):
    """Show latest LOB metrics.

    Args:
        top_k: Number of recent rows to show
    """
    conn = duckdb.connect(str(DUCKDB_PATH))

    result = conn.execute(f"""
        SELECT timestamp, spread, ofi_1s, ofi_5s, vpin, depth_imbalance
        FROM lob_metrics
        ORDER BY timestamp DESC
        LIMIT {top_k}
    """).fetchdf()

    conn.close()

    if result.empty:
        print("No metrics available. Run 'python -m lob.cli compute' first.")
        return 1

    print(result.to_string(index=False))
    return 0


def cmd_vpin():
    """Show current VPIN and alert if toxic."""
    conn = duckdb.connect(str(DUCKDB_PATH))

    result = conn.execute("""
        SELECT timestamp, vpin
        FROM lob_metrics
        ORDER BY timestamp DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    if not result:
        print("No VPIN data available")
        return 1

    timestamp, vpin = result
    print(f"Latest VPIN: {vpin:.4f} (timestamp: {timestamp})")

    if vpin > 0.7:
        print("⚠️  ALERT: Toxic flow detected (VPIN > 0.7)")
    elif vpin > 0.5:
        print("⚠️  WARNING: Elevated informed trading (VPIN > 0.5)")
    else:
        print("✓ Normal flow")

    return 0


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m lob.cli <command>")
        print("Commands: compute, metrics, vpin")
        return 1

    command = sys.argv[1]

    if command == "compute":
        return cmd_compute()
    elif command == "metrics":
        top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        return cmd_metrics(top_k)
    elif command == "vpin":
        return cmd_vpin()
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
