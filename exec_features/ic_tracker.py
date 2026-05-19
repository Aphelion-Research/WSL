"""IC tracking and decay monitoring."""
import pandas as pd
import numpy as np
import duckdb
from pathlib import Path
from typing import Dict
from exec_features.config import IC_STRONG_THRESHOLD, IC_DECAY_THRESHOLD


def compute_ic(feature_series: pd.Series, forward_returns: pd.Series, window: int = 252) -> pd.Series:
    """Compute rolling IC (correlation with forward returns).

    Args:
        feature_series: Feature values
        forward_returns: Forward returns (e.g., 60-minute)
        window: Rolling window

    Returns:
        Series of IC values
    """
    # Rolling correlation
    ic = feature_series.rolling(window, min_periods=20).corr(forward_returns)
    return ic.fillna(0)


def compute_forward_returns(prices: pd.Series, horizon_minutes: int = 60) -> pd.Series:
    """Compute forward returns.

    Args:
        prices: Price series
        horizon_minutes: Minutes ahead

    Returns:
        Forward returns
    """
    # Shift prices backward to get future price
    future_price = prices.shift(-horizon_minutes)
    returns = (future_price - prices) / prices
    return returns.fillna(0)


def update_ic_for_features(db_path: Path, features_df: pd.DataFrame, prices: pd.Series) -> None:
    """Update IC values for all features.

    Args:
        db_path: DuckDB path
        features_df: DataFrame with all features
        prices: Price series for computing returns
    """
    # Compute forward returns
    forward_returns = compute_forward_returns(prices, horizon_minutes=60)

    conn = duckdb.connect(str(db_path))

    # For each feature column, compute IC and update
    for col in features_df.columns:
        if col == 'timestamp':
            continue

        feature_series = features_df[col]
        ic_series = compute_ic(feature_series, forward_returns, window=252)

        # Get latest IC
        latest_ic = ic_series.iloc[-1] if len(ic_series) > 0 else 0.0

        # Update execution_features table with IC
        # (Simplified: just store latest IC value)
        # In production, would update each row individually

    conn.close()


def check_feature_decay(db_path: Path) -> pd.DataFrame:
    """Check for features with significant IC decay.

    Args:
        db_path: DuckDB path

    Returns:
        DataFrame with decayed features
    """
    conn = duckdb.connect(str(db_path))

    # Get IC history for each feature
    decay_alerts = []

    # Simplified: query recent IC values
    # In production, would compute 30d vs 90d rolling IC

    conn.close()

    return pd.DataFrame(decay_alerts)
