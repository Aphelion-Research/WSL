"""DuckDB schema for execution simulator."""
import duckdb
from pathlib import Path


def init_exec_sim_schema(db_path: Path) -> None:
    """Initialize execution simulator tables.

    Args:
        db_path: Path to DuckDB database
    """
    conn = duckdb.connect(str(db_path))

    # Strategies table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_strategies (
            strategy_id VARCHAR PRIMARY KEY,
            strategy_type VARCHAR NOT NULL,
            target_quantity DOUBLE NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP NOT NULL,
            params_json VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Orders table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_orders (
            order_id VARCHAR PRIMARY KEY,
            strategy_id VARCHAR NOT NULL,
            submit_time TIMESTAMP NOT NULL,
            side VARCHAR NOT NULL,
            price DOUBLE,
            quantity DOUBLE NOT NULL,
            fill_time TIMESTAMP,
            fill_price DOUBLE,
            fill_quantity DOUBLE,
            slippage_bps DOUBLE
        )
    """)

    # Performance table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_performance (
            strategy_id VARCHAR PRIMARY KEY,
            arrival_cost_bps DOUBLE,
            vwap_cost_bps DOUBLE,
            twap_cost_bps DOUBLE,
            shortfall_pct DOUBLE,
            impact_realized_bps DOUBLE,
            impact_predicted_bps DOUBLE,
            fill_rate DOUBLE,
            avg_slippage_bps DOUBLE
        )
    """)

    conn.close()
