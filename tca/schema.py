"""DuckDB schema for TCA."""
import duckdb
from pathlib import Path


def init_tca_schema(db_path: Path) -> None:
    """Initialize TCA tables.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(str(db_path))

    # Trades table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tca_trades (
            trade_id VARCHAR PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol VARCHAR DEFAULT 'XAUUSD',
            side VARCHAR NOT NULL,
            decision_price DOUBLE NOT NULL,
            arrival_price DOUBLE NOT NULL,
            avg_fill_price DOUBLE NOT NULL,
            quantity_target DOUBLE NOT NULL,
            quantity_filled DOUBLE NOT NULL,
            regime VARCHAR
        )
    """)

    # Attribution table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tca_attribution (
            trade_id VARCHAR PRIMARY KEY,
            decision_cost_bps DOUBLE,
            timing_cost_bps DOUBLE,
            impact_cost_bps DOUBLE,
            opportunity_cost_bps DOUBLE,
            total_cost_bps DOUBLE
        )
    """)

    # Benchmarks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tca_benchmarks (
            trade_id VARCHAR PRIMARY KEY,
            vwap_cost_bps DOUBLE,
            twap_cost_bps DOUBLE,
            vs_vwap_bps DOUBLE,
            vs_twap_bps DOUBLE,
            regime VARCHAR,
            hour_of_day INTEGER
        )
    """)

    conn.close()
