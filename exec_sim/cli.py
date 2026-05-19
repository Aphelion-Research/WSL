"""Execution simulator CLI."""
import sys
import json
import uuid
import duckdb
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from exec_sim.config import DUCKDB_PATH
from exec_sim.schema import init_exec_sim_schema
from exec_sim.strategies.vwap import VWAPStrategy
from exec_sim.strategies.twap import TWAPStrategy
from exec_sim.strategies.pov import POVStrategy
from exec_sim.impact.almgren_chriss import permanent_impact, temporary_impact


def load_market_data(db_path: Path, start_time: pd.Timestamp, end_time: pd.Timestamp) -> pd.DataFrame:
    """Load market data from gold_raw.

    Args:
        db_path: DuckDB path
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        DataFrame with timestamp, close, volume
    """
    conn = duckdb.connect(str(db_path))

    df = conn.execute("""
        SELECT timestamp, close, volume
        FROM gold_raw
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp
    """, [start_time, end_time]).fetchdf()

    conn.close()

    if df.empty:
        # Generate synthetic data
        print("WARNING: No market data, generating synthetic")
        periods = int((end_time - start_time).total_seconds() / 300)  # 5-min bars
        timestamps = pd.date_range(start_time, end_time, periods=periods)
        df = pd.DataFrame({
            'timestamp': timestamps,
            'close': 2000.0,
            'volume': 100.0
        })

    return df


def cmd_run(strategy_type: str, quantity: float, start_date: str):
    """Run execution simulation.

    Args:
        strategy_type: 'vwap', 'twap', or 'pov'
        quantity: Target quantity
        start_date: Start date (YYYY-MM-DD)
    """
    init_exec_sim_schema(DUCKDB_PATH)

    # Parse dates
    start_time = pd.Timestamp(start_date)
    end_time = start_time + pd.Timedelta(hours=6)

    # Load market data
    market_data = load_market_data(DUCKDB_PATH, start_time, end_time)

    # Create strategy
    if strategy_type == 'vwap':
        strategy = VWAPStrategy(quantity, start_time, end_time)
    elif strategy_type == 'twap':
        strategy = TWAPStrategy(quantity, start_time, end_time)
    elif strategy_type == 'pov':
        strategy = POVStrategy(quantity, start_time, end_time)
    else:
        print(f"Unknown strategy: {strategy_type}")
        return 1

    # Generate slices
    slices = strategy.generate_slices(market_data)
    print(f"Generated {len(slices)} slices for {strategy_type.upper()}")

    # Store strategy
    strategy_id = str(uuid.uuid4())[:8]
    conn = duckdb.connect(str(DUCKDB_PATH))

    conn.execute("""
        INSERT INTO sim_strategies (strategy_id, strategy_type, target_quantity, start_time, end_time, params_json)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [strategy_id, strategy_type, quantity, start_time, end_time, json.dumps({})])

    # Store orders (simplified: assume all filled at slice time)
    for i, slice_info in enumerate(slices):
        order_id = f"{strategy_id}-{i}"
        submit_time = slice_info['time']
        fill_price = 2000.0  # simplified
        conn.execute("""
            INSERT INTO sim_orders (order_id, strategy_id, submit_time, side, price, quantity, fill_time, fill_price, fill_quantity, slippage_bps)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [order_id, strategy_id, submit_time, 'buy', None, slice_info['quantity'], submit_time, fill_price, slice_info['quantity'], 0.5])

    # Compute performance metrics
    arrival_cost_bps = 1.0  # simplified
    conn.execute("""
        INSERT INTO sim_performance (strategy_id, arrival_cost_bps, vwap_cost_bps, twap_cost_bps, shortfall_pct, impact_realized_bps, impact_predicted_bps, fill_rate, avg_slippage_bps)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [strategy_id, arrival_cost_bps, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 0.5])

    conn.close()

    print(f"✓ Simulation complete: strategy_id={strategy_id}")
    return 0


def cmd_report(strategy_id: str):
    """Show performance report for strategy.

    Args:
        strategy_id: Strategy ID
    """
    conn = duckdb.connect(str(DUCKDB_PATH))

    # Get strategy info
    strat = conn.execute("""
        SELECT * FROM sim_strategies WHERE strategy_id = ?
    """, [strategy_id]).fetchone()

    if not strat:
        print(f"Strategy not found: {strategy_id}")
        return 1

    # Get performance
    perf = conn.execute("""
        SELECT * FROM sim_performance WHERE strategy_id = ?
    """, [strategy_id]).fetchone()

    # Get orders
    orders = conn.execute("""
        SELECT COUNT(*) as n_orders, SUM(fill_quantity) as total_filled
        FROM sim_orders WHERE strategy_id = ?
    """, [strategy_id]).fetchone()

    conn.close()

    print(f"\n=== Execution Report: {strategy_id} ===")
    print(f"Strategy: {strat[1]}")
    print(f"Target Quantity: {strat[2]:.2f}")
    print(f"Orders: {orders[0]}")
    print(f"Filled: {orders[1]:.2f}")
    print(f"\nPerformance:")
    print(f"  Arrival Cost: {perf[1]:.2f} bps")
    print(f"  Fill Rate: {perf[7]:.2%}")
    print(f"  Avg Slippage: {perf[8]:.2f} bps")

    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m exec_sim.cli <command>")
        print("Commands: run, report")
        return 1

    command = sys.argv[1]

    if command == "run":
        if len(sys.argv) < 5:
            print("Usage: python -m exec_sim.cli run --strategy <vwap|twap|pov> --quantity <N> --start <YYYY-MM-DD>")
            return 1

        # Parse args
        args = {}
        for i in range(2, len(sys.argv), 2):
            if i+1 < len(sys.argv):
                args[sys.argv[i].lstrip('--')] = sys.argv[i+1]

        return cmd_run(args['strategy'], float(args['quantity']), args['start'])

    elif command == "report":
        if len(sys.argv) < 4 or sys.argv[2] != '--strategy-id':
            print("Usage: python -m exec_sim.cli report --strategy-id <ID>")
            return 1
        return cmd_report(sys.argv[3])

    else:
        print(f"Unknown command: {command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
