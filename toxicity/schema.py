"""DuckDB schema for toxicity monitor."""
import duckdb
from pathlib import Path


def init_toxicity_schema(db_path: Path) -> None:
    """Initialize toxicity tables.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(str(db_path))

    # Toxicity metrics table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS toxicity_metrics (
            timestamp TIMESTAMP PRIMARY KEY,
            vpin DOUBLE,
            ofi_1s DOUBLE,
            ofi_5s DOUBLE,
            ofi_1m DOUBLE,
            adverse_selection_bps DOUBLE,
            effective_spread_bps DOUBLE,
            realized_spread_bps DOUBLE,
            price_impact_bps DOUBLE,
            toxicity_score DOUBLE
        )
    """)

    # Alerts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS toxicity_alerts (
            alert_id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            alert_type VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            metric_value DOUBLE,
            threshold DOUBLE,
            description VARCHAR
        )
    """)

    conn.close()
