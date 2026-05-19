"""DuckDB schema for execution features."""
import duckdb
from pathlib import Path


def init_exec_features_schema(db_path: Path) -> None:
    """Initialize execution features tables.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(str(db_path))

    # Execution features table (extends existing features table concept)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS execution_features (
            timestamp TIMESTAMP NOT NULL,
            feature_name VARCHAR NOT NULL,
            feature_value DOUBLE,
            ic_60 DOUBLE,
            ic_updated_at TIMESTAMP,
            regime VARCHAR,
            PRIMARY KEY (timestamp, feature_name)
        )
    """)

    # Feature decay alerts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feature_decay_alerts (
            feature_name VARCHAR NOT NULL,
            old_ic DOUBLE,
            new_ic DOUBLE,
            drop_pct DOUBLE,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            severity VARCHAR
        )
    """)

    conn.close()
