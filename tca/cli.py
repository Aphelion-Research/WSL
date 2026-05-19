"""TCA CLI commands."""
import sys
import json
import duckdb
from pathlib import Path
from tca.config import DUCKDB_PATH
from tca.schema import init_tca_schema
from tca.analytics import regime_breakdown, waterfall_summary


def cmd_analyze(trade_id: str):
    """Show attribution breakdown for trade.

    Args:
        trade_id: Trade ID
    """
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Get trade
    trade = conn.execute("""
        SELECT * FROM tca_trades WHERE trade_id = ?
    """, [trade_id]).fetchone()

    if not trade:
        print(f"Trade not found: {trade_id}")
        return 1

    # Get attribution
    attr = conn.execute("""
        SELECT * FROM tca_attribution WHERE trade_id = ?
    """, [trade_id]).fetchone()

    conn.close()

    print(f"\n=== TCA Analysis: {trade_id} ===")
    print(f"Timestamp: {trade[1]}")
    print(f"Side: {trade[3]}")
    print(f"Filled: {trade[8]:.2f} / {trade[7]:.2f}")
    print(f"\nCost Attribution (bps):")
    print(f"  Decision: {attr[1]:+.2f}")
    print(f"  Timing:   {attr[2]:+.2f}")
    print(f"  Impact:   {attr[3]:+.2f}")
    print(f"  Opportunity: {attr[4]:+.2f}")
    print(f"  ─────────────────")
    print(f"  Total:    {attr[5]:+.2f}")

    return 0


def cmd_report(since_days: int = 30):
    """Aggregate TCA stats.

    Args:
        since_days: Days to look back
    """
    print(f"\n=== TCA Report (last {since_days} days) ===\n")

    # Regime breakdown
    df = regime_breakdown(DUCKDB_PATH)

    if not df.empty:
        print("Cost by Regime:")
        print(df.to_string(index=False))
    else:
        print("No data available")

    return 0


def cmd_heatmap():
    """Print time-of-day cost heatmap."""
    from tca.analytics import time_of_day_heatmap

    heatmap = time_of_day_heatmap(DUCKDB_PATH)

    if heatmap.empty:
        print("No data for heatmap")
        return 1

    print("\n=== Cost Heatmap (hour × day) ===")
    print(heatmap.to_string())

    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m tca.cli <command>")
        print("Commands: analyze, report, heatmap")
        return 1

    command = sys.argv[1]

    if command == "analyze":
        if len(sys.argv) < 4 or sys.argv[2] != '--trade-id':
            print("Usage: python -m tca.cli analyze --trade-id <ID>")
            return 1
        return cmd_analyze(sys.argv[3])

    elif command == "report":
        since_days = 30
        if len(sys.argv) > 3 and sys.argv[2] == '--since':
            since_days = int(sys.argv[3].rstrip('d'))
        return cmd_report(since_days)

    elif command == "heatmap":
        return cmd_heatmap()

    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
