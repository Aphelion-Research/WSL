"""Spread dynamics features (10)."""
import pandas as pd
import numpy as np


def compute_spread_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 10 spread features.

    Args:
        df: DataFrame with 'bid', 'ask', 'timestamp'

    Returns:
        DataFrame with spread features
    """
    features = pd.DataFrame(index=df.index)

    # Basic spread
    spread = (df['ask'] - df['bid'])
    mid = (df['bid'] + df['ask']) / 2

    features['spread_quoted_bps'] = (spread / mid * 10000).fillna(0)
    features['spread_pct_rank'] = features['spread_quoted_bps'].rolling(60, min_periods=1).rank(pct=True).fillna(0.5)
    features['spread_effective_1m'] = features['spread_quoted_bps'].rolling(60, min_periods=1).mean().fillna(0)

    # Roll spread (simplified)
    price_changes = mid.diff()
    features['spread_roll_20'] = 2 * np.sqrt(np.abs(price_changes.rolling(20).cov(price_changes.shift(1)))).fillna(0) / mid * 10000

    # Corwin-Schultz (placeholder)
    features['spread_corwin_schultz'] = features['spread_quoted_bps']

    # Dynamics
    features['spread_direction'] = np.sign(spread.diff()).fillna(0)
    features['spread_momentum'] = (spread - spread.rolling(20, min_periods=1).mean()).fillna(0) / mid * 10000
    features['spread_volatility'] = spread.rolling(20, min_periods=1).std().fillna(0) / mid * 10000
    features['spread_percentile_intraday'] = spread.rank(pct=True).fillna(0.5)
    features['spread_regime_wide'] = (features['spread_pct_rank'] > 0.75).astype(int)

    return features
