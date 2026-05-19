"""Benchmark comparison logic."""
import duckdb
import pandas as pd
from pathlib import Path
from typing import Dict, Optional


def load_sim_benchmark(db_path: Path, trade_timestamp: pd.Timestamp, strategy_type: str) -> Optional[float]:
    """Load benchmark cost from sim_performance.

    Args:
        db_path: DuckDB path
        trade_timestamp: Trade timestamp
        strategy_type: 'vwap' or 'twap'

    Returns:
        Benchmark cost in bps, or None if not found
    """
    conn = duckdb.connect(str(db_path))

    # Find closest strategy run
    result = conn.execute("""
        SELECT s.strategy_id, p.arrival_cost_bps
        FROM sim_strategies s
        JOIN sim_performance p ON s.strategy_id = p.strategy_id
        WHERE s.strategy_type = ?
          AND s.start_time <= ?
          AND s.end_time >= ?
        ORDER BY ABS(EXTRACT(EPOCH FROM (s.start_time - ?)))
        LIMIT 1
    """, [strategy_type, trade_timestamp, trade_timestamp, trade_timestamp]).fetchone()

    conn.close()

    return result[1] if result else None


def compute_benchmark_comparison(
    avg_fill_cost_bps: float,
    vwap_cost_bps: Optional[float],
    twap_cost_bps: Optional[float],
    regime: str,
    hour_of_day: int
) -> Dict:
    """Compute benchmark comparison metrics.

    Args:
        avg_fill_cost_bps: Actual fill cost
        vwap_cost_bps: VWAP benchmark cost
        twap_cost_bps: TWAP benchmark cost
        regime: Current regime
        hour_of_day: Hour (0-23)

    Returns:
        Dict with benchmark comparisons
    """
    vs_vwap_bps = (avg_fill_cost_bps - vwap_cost_bps) if vwap_cost_bps is not None else 0.0
    vs_twap_bps = (avg_fill_cost_bps - twap_cost_bps) if twap_cost_bps is not None else 0.0

    return {
        'vwap_cost_bps': vwap_cost_bps or 0.0,
        'twap_cost_bps': twap_cost_bps or 0.0,
        'vs_vwap_bps': vs_vwap_bps,
        'vs_twap_bps': vs_twap_bps,
        'regime': regime,
        'hour_of_day': hour_of_day
    }
