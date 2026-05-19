"""TCA analytics and reporting."""
import pandas as pd
import duckdb
from pathlib import Path
from typing import Dict


def regime_breakdown(db_path: Path) -> pd.DataFrame:
    """Compute average cost by regime.

    Args:
        db_path: DuckDB path

    Returns:
        DataFrame with regime-level statistics
    """
    conn = duckdb.connect(str(db_path))

    df = conn.execute("""
        SELECT
            t.regime,
            COUNT(*) as n_trades,
            AVG(a.total_cost_bps) as avg_cost_bps,
            STDDEV(a.total_cost_bps) as std_cost_bps
        FROM tca_trades t
        JOIN tca_attribution a ON t.trade_id = a.trade_id
        WHERE t.regime IS NOT NULL
        GROUP BY t.regime
        ORDER BY avg_cost_bps DESC
    """).fetchdf()

    conn.close()
    return df


def time_of_day_heatmap(db_path: Path) -> pd.DataFrame:
    """Compute cost heatmap by hour.

    Args:
        db_path: DuckDB path

    Returns:
        DataFrame with hour × day_of_week
    """
    conn = duckdb.connect(str(db_path))

    df = conn.execute("""
        SELECT
            EXTRACT(HOUR FROM t.timestamp) as hour,
            EXTRACT(DOW FROM t.timestamp) as day_of_week,
            AVG(a.total_cost_bps) as avg_cost_bps
        FROM tca_trades t
        JOIN tca_attribution a ON t.trade_id = a.trade_id
        GROUP BY hour, day_of_week
        ORDER BY hour, day_of_week
    """).fetchdf()

    conn.close()

    # Pivot to heatmap format
    if not df.empty:
        heatmap = df.pivot(index='hour', columns='day_of_week', values='avg_cost_bps')
        return heatmap
    return pd.DataFrame()


def waterfall_summary(db_path: Path, trade_id: str) -> Dict:
    """Get waterfall breakdown for single trade.

    Args:
        db_path: DuckDB path
        trade_id: Trade ID

    Returns:
        Dict with waterfall components
    """
    conn = duckdb.connect(str(db_path))

    result = conn.execute("""
        SELECT decision_cost_bps, timing_cost_bps, impact_cost_bps, opportunity_cost_bps, total_cost_bps
        FROM tca_attribution
        WHERE trade_id = ?
    """, [trade_id]).fetchone()

    conn.close()

    if not result:
        return {}

    return {
        'decision': result[0],
        'timing': result[1],
        'impact': result[2],
        'opportunity': result[3],
        'total': result[4]
    }
