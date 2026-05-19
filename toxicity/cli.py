"""Toxicity monitor CLI."""
import sys
import duckdb
import pandas as pd
from pathlib import Path
from toxicity.config import DUCKDB_PATH, VPIN_THRESHOLD_HIGH
from toxicity.schema import init_toxicity_schema
from toxicity.alerts import generate_alerts, store_alerts


def cmd_compute():
    """Compute toxicity metrics from LOB data."""
    print("Initializing toxicity schema...")
    init_toxicity_schema(DUCKDB_PATH)

    # Load LOB metrics
    conn = duckdb.connect(str(DUCKDB_PATH))

    lob_metrics = conn.execute("""
        SELECT timestamp, vpin, ofi_1s, ofi_5s, ofi_1m, depth_imbalance
        FROM lob_metrics
        ORDER BY timestamp
    """).fetchdf()

    if lob_metrics.empty:
        print("ERROR: No LOB metrics available. Run 'python -m lob.cli compute' first.")
        return 1

    print(f"Computing toxicity metrics for {len(lob_metrics)} rows...")

    # Simplified: use LOB metrics directly
    # In full implementation, would compute adverse selection from fills
    lob_metrics['adverse_selection_bps'] = 0.0
    lob_metrics['effective_spread_bps'] = 0.0
    lob_metrics['realized_spread_bps'] = 0.0
    lob_metrics['price_impact_bps'] = 0.0

    # Compute toxicity score (simplified)
    from toxicity.adverse import compute_toxicity_score

    scores = []
    for i, row in lob_metrics.iterrows():
        hist_window = lob_metrics.iloc[max(0, i-252):i]
        score = compute_toxicity_score(
            vpin=row['vpin'],
            ofi=row['ofi_1m'],
            adverse_sel=row['adverse_selection_bps'],
            vpin_hist=hist_window['vpin'] if len(hist_window) > 0 else pd.Series([0.5]),
            ofi_hist=hist_window['ofi_1m'] if len(hist_window) > 0 else pd.Series([0.0]),
            adverse_hist=hist_window['adverse_selection_bps'] if len(hist_window) > 0 else pd.Series([0.0])
        )
        scores.append(score)

    lob_metrics['toxicity_score'] = scores

    # Store metrics row-by-row
    conn.execute("DELETE FROM toxicity_metrics")
    for _, row in lob_metrics.iterrows():
        conn.execute("""
            INSERT INTO toxicity_metrics (timestamp, vpin, ofi_1s, ofi_5s, ofi_1m,
                                         adverse_selection_bps, effective_spread_bps, realized_spread_bps,
                                         price_impact_bps, toxicity_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [row['timestamp'], row['vpin'], row['ofi_1s'], row['ofi_5s'], row['ofi_1m'],
              row['adverse_selection_bps'], row['effective_spread_bps'], row['realized_spread_bps'],
              row['price_impact_bps'], row['toxicity_score']])

    rows_stored = conn.execute("SELECT COUNT(*) FROM toxicity_metrics").fetchone()[0]
    conn.close()

    print(f"✓ Stored {rows_stored} toxicity metrics")

    # Generate alerts
    alerts = generate_alerts(lob_metrics, DUCKDB_PATH)
    if alerts:
        store_alerts(alerts, DUCKDB_PATH)
        print(f"✓ Generated {len(alerts)} alerts")

    return 0


def cmd_status():
    """Show current toxicity status."""
    conn = duckdb.connect(str(DUCKDB_PATH))

    result = conn.execute("""
        SELECT timestamp, vpin, ofi_1m, toxicity_score
        FROM toxicity_metrics
        ORDER BY timestamp DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    if not result:
        print("No toxicity data available")
        return 1

    timestamp, vpin, ofi_1m, score = result

    print(f"\n=== Toxicity Status ===")
    print(f"Timestamp: {timestamp}")
    print(f"VPIN: {vpin:.4f}")
    print(f"OFI (1m): {ofi_1m:+.2f}")
    print(f"Toxicity Score: {score:.4f}")

    if vpin > VPIN_THRESHOLD_HIGH:
        print("\n⚠️  ALERT: Toxic flow detected (VPIN > 0.7)")
    elif score > 0.6:
        print("\n⚠️  WARNING: Elevated toxicity")
    else:
        print("\n✓ Normal flow")

    return 0


def cmd_alerts(since_days: int = 7):
    """Show recent alerts.

    Args:
        since_days: Days to look back
    """
    conn = duckdb.connect(str(DUCKDB_PATH))

    alerts = conn.execute(f"""
        SELECT timestamp, alert_type, severity, description
        FROM toxicity_alerts
        WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '{since_days} days'
        ORDER BY timestamp DESC
    """).fetchdf()

    conn.close()

    if alerts.empty:
        print(f"No alerts in last {since_days} days")
        return 0

    print(f"\n=== Toxicity Alerts (last {since_days} days) ===\n")
    print(alerts.to_string(index=False))

    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m toxicity.cli <command>")
        print("Commands: compute, status, alerts")
        return 1

    command = sys.argv[1]

    if command == "compute":
        return cmd_compute()
    elif command == "status":
        return cmd_status()
    elif command == "alerts":
        since_days = 7
        if len(sys.argv) > 3 and sys.argv[2] == '--since':
            since_days = int(sys.argv[3].rstrip('d'))
        return cmd_alerts(since_days)
    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
