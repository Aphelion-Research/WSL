"""DuckDB schema for LOB tables."""
import duckdb
from pathlib import Path


def init_lob_schema(db_path: Path) -> None:
    """Initialize LOB tables in DuckDB.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(str(db_path))

    # LOB snapshots table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lob_snapshots (
            snapshot_id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            bids_json VARCHAR,
            asks_json VARCHAR,
            mid_price DOUBLE,
            spread DOUBLE,
            total_bid_depth DOUBLE,
            total_ask_depth DOUBLE
        )
    """)

    # LOB events table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lob_events (
            event_id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            event_type VARCHAR,
            side VARCHAR,
            price DOUBLE,
            size DOUBLE,
            source VARCHAR
        )
    """)

    # LOB metrics table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS lob_metrics (
            timestamp TIMESTAMP NOT NULL,
            spread DOUBLE,
            effective_spread DOUBLE,
            roll_spread DOUBLE,
            corwin_schultz_spread DOUBLE,
            ofi_1s DOUBLE,
            ofi_5s DOUBLE,
            ofi_1m DOUBLE,
            vpin DOUBLE,
            depth_imbalance DOUBLE,
            depth_weighted_mid DOUBLE,
            bid_depth DOUBLE,
            ask_depth DOUBLE,
            PRIMARY KEY (timestamp)
        )
    """)

    conn.close()
