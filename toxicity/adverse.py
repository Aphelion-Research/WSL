"""Adverse selection metrics."""
import pandas as pd
import numpy as np


def compute_adverse_selection(df: pd.DataFrame, horizon_min: int = 5) -> pd.DataFrame:
    """Compute adverse selection metrics.

    Args:
        df: DataFrame with 'timestamp', 'fill_price', 'mid_price', 'side'
        horizon_min: Minutes ahead for realized spread

    Returns:
        DataFrame with adverse selection metrics
    """
    df = df.copy()

    # Effective spread: 2 * side * (fill_price - mid_t)
    df['side_mult'] = df['side'].map({'buy': 1.0, 'sell': -1.0}).fillna(1.0)
    df['effective_spread_bps'] = 2 * df['side_mult'] * (df['fill_price'] - df['mid_price']) / df['mid_price'] * 10000

    # Future mid price (for realized spread)
    df = df.set_index('timestamp')
    df['mid_future'] = df['mid_price'].shift(-horizon_min)
    df = df.reset_index()

    # Realized spread: 2 * side * (fill_price - mid_{t+5min})
    df['realized_spread_bps'] = 2 * df['side_mult'] * (df['fill_price'] - df['mid_future']) / df['mid_future'] * 10000

    # Price impact: 2 * side * (mid_{t+5min} - mid_t)
    df['price_impact_bps'] = 2 * df['side_mult'] * (df['mid_future'] - df['mid_price']) / df['mid_price'] * 10000

    # Adverse selection = effective - realized
    df['adverse_selection_bps'] = df['effective_spread_bps'] - df['realized_spread_bps']

    # Fill NaN with 0
    df = df.fillna(0)

    return df[['timestamp', 'effective_spread_bps', 'realized_spread_bps', 'price_impact_bps', 'adverse_selection_bps']]


def compute_toxicity_score(vpin: float, ofi: float, adverse_sel: float,
                          vpin_hist: pd.Series, ofi_hist: pd.Series, adverse_hist: pd.Series) -> float:
    """Compute composite toxicity score.

    Args:
        vpin: Current VPIN value
        ofi: Current OFI value
        adverse_sel: Current adverse selection
        vpin_hist: Historical VPIN values (for percentile ranking)
        ofi_hist: Historical OFI values
        adverse_hist: Historical adverse selection values

    Returns:
        Toxicity score in [0, 1]
    """
    # Percentile rank each component
    vpin_pct = (vpin_hist < vpin).mean() if len(vpin_hist) > 0 else 0.5
    ofi_pct = (ofi_hist.abs() < abs(ofi)).mean() if len(ofi_hist) > 0 else 0.5
    adverse_pct = (adverse_hist < adverse_sel).mean() if len(adverse_hist) > 0 else 0.5

    # Weighted average
    score = 0.4 * vpin_pct + 0.3 * ofi_pct + 0.3 * adverse_pct

    return np.clip(score, 0, 1)
