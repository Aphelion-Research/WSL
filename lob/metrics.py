"""LOB metrics computation: OFI, VPIN, spreads."""
import pandas as pd
import numpy as np
from scipy import stats
from typing import Optional


def compute_ofi(df: pd.DataFrame, window_seconds: int) -> pd.Series:
    """Compute Order Flow Imbalance over time window.

    Classifies trades as buy/sell using tick rule, then aggregates.

    Args:
        df: DataFrame with 'timestamp', 'tick_price', 'bid', 'ask'
        window_seconds: Window size in seconds

    Returns:
        Series of OFI values (buy_vol - sell_vol) per window
    """
    df = df.copy()

    # Classify trades: buy if price >= ask, sell if price <= bid
    df['trade_class'] = 0  # neutral
    df.loc[df['tick_price'] >= df['ask'], 'trade_class'] = 1  # buy
    df.loc[df['tick_price'] <= df['bid'], 'trade_class'] = -1  # sell

    # Assign volume (synthetic: assume 1 unit per tick)
    df['volume'] = 1.0
    df['signed_volume'] = df['volume'] * df['trade_class']

    # Aggregate by time window
    df = df.set_index('timestamp')
    ofi = df['signed_volume'].resample(f'{window_seconds}s').sum()

    return ofi


def compute_vpin(df: pd.DataFrame, buckets_per_day: int = 50) -> pd.Series:
    """Compute VPIN (Volume-Synchronized Probability of Informed Trading).

    Uses bulk volume classification with equal-volume buckets.

    Args:
        df: DataFrame with 'timestamp', 'tick_price'
        buckets_per_day: Number of volume buckets per day

    Returns:
        Series of VPIN values in [0, 1]
    """
    if len(df) < buckets_per_day:
        return pd.Series([0.0] * len(df), index=df['timestamp'])

    df = df.copy()
    df['volume'] = 1.0  # synthetic volume

    # Compute bucket size
    daily_volume = df['volume'].sum()
    bucket_size = daily_volume / buckets_per_day

    if bucket_size == 0:
        return pd.Series([0.0] * len(df), index=df['timestamp'])

    # Bulk volume classification using price changes
    df['price_change'] = df['tick_price'].diff()
    df['price_std'] = df['price_change'].rolling(20).std()

    # Z-score for each price change
    df['z_score'] = df['price_change'] / (df['price_std'] + 1e-9)

    # Buy probability using CDF of standard normal
    df['buy_prob'] = stats.norm.cdf(df['z_score'])
    df['buy_vol'] = df['volume'] * df['buy_prob']
    df['sell_vol'] = df['volume'] * (1 - df['buy_prob'])

    # Create equal-volume buckets
    df['cumvol'] = df['volume'].cumsum()
    df['bucket_id'] = (df['cumvol'] / bucket_size).astype(int)

    # Aggregate by bucket
    bucket_ofi = df.groupby('bucket_id').agg({
        'buy_vol': 'sum',
        'sell_vol': 'sum',
        'volume': 'sum'
    })

    bucket_ofi['ofi_abs'] = (bucket_ofi['buy_vol'] - bucket_ofi['sell_vol']).abs()
    bucket_ofi['vpin_bucket'] = bucket_ofi['ofi_abs'] / (bucket_ofi['volume'] + 1e-9)

    # Rolling average over 50 buckets
    bucket_ofi['vpin'] = bucket_ofi['vpin_bucket'].rolling(50, min_periods=1).mean()

    # Map back to original timestamps
    df = df.merge(bucket_ofi[['vpin']], left_on='bucket_id', right_index=True, how='left')
    df['vpin'] = df['vpin'].fillna(0.0).clip(0, 1)

    return df.set_index('timestamp')['vpin']


def compute_roll_spread(prices: pd.Series, window: int = 20) -> pd.Series:
    """Compute Roll (1984) implicit spread estimate.

    Roll spread = 2 * sqrt(max(-cov(Δp_t, Δp_{t-1}), 0))

    Args:
        prices: Price series
        window: Rolling window size

    Returns:
        Series of Roll spread estimates
    """
    delta_p = prices.diff()

    # Rolling covariance of consecutive changes
    # Cov(X, Y) with Y = X.shift(1)
    def roll_cov(x):
        if len(x) < 2:
            return 0.0
        cov = np.cov(x[:-1], x[1:])[0, 1]
        return 2 * np.sqrt(max(-cov, 0))

    roll = delta_p.rolling(window).apply(roll_cov, raw=True)
    return roll.fillna(0.0)


def compute_corwin_schultz_spread(df: pd.DataFrame) -> pd.Series:
    """Compute Corwin-Schultz (2012) spread from OHLC.

    Requires columns: high, low

    Args:
        df: DataFrame with 'high', 'low' columns

    Returns:
        Series of CS spread estimates
    """
    if 'high' not in df.columns or 'low' not in df.columns:
        # Fallback: use bid/ask if available
        if 'bid' in df.columns and 'ask' in df.columns:
            return (df['ask'] - df['bid'])
        return pd.Series([0.0] * len(df), index=df.index)

    # Corwin-Schultz algorithm
    df = df.copy()
    df['hl_ratio'] = np.log(df['high'] / df['low']) ** 2

    # Beta: sum of squared log HL ratios over 2 days
    df['beta'] = df['hl_ratio'].rolling(2).sum()

    # Gamma: log ratio of 2-day max/min
    df['high_2d'] = df['high'].rolling(2).max()
    df['low_2d'] = df['low'].rolling(2).min()
    df['gamma'] = np.log(df['high_2d'] / df['low_2d']) ** 2

    # Alpha estimate
    sqrt_2 = np.sqrt(2)
    df['alpha'] = (np.sqrt(2 * df['beta']) - np.sqrt(df['beta'])) / (3 - 2 * sqrt_2)
    df['alpha'] -= np.sqrt(df['gamma'] / (3 - 2 * sqrt_2))

    # Spread estimate
    df['cs_spread'] = 2 * (np.exp(df['alpha']) - 1) / (1 + np.exp(df['alpha']))
    df['cs_spread'] = df['cs_spread'].fillna(0.0).clip(0, 1)

    return df['cs_spread']


def compute_all_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all LOB metrics.

    Args:
        df: DataFrame with LOB data

    Returns:
        DataFrame with all metrics
    """
    metrics = pd.DataFrame(index=df['timestamp'])

    # Basic spread
    metrics['spread'] = df['ask'] - df['bid']
    metrics['effective_spread'] = metrics['spread']  # simplified

    # Roll spread
    metrics['roll_spread'] = compute_roll_spread(df['tick_price'])

    # Corwin-Schultz spread (requires OHLC, fallback to bid-ask)
    metrics['corwin_schultz_spread'] = compute_corwin_schultz_spread(df)

    # OFI at multiple windows
    metrics['ofi_1s'] = compute_ofi(df, 1).reindex(df['timestamp']).fillna(0.0).values
    metrics['ofi_5s'] = compute_ofi(df, 5).reindex(df['timestamp']).fillna(0.0).values
    metrics['ofi_1m'] = compute_ofi(df, 60).reindex(df['timestamp']).fillna(0.0).values

    # VPIN
    vpin_series = compute_vpin(df)
    metrics['vpin'] = vpin_series.reindex(df['timestamp']).fillna(0.0).values

    # Depth metrics (from LOB state if available)
    if 'bid_size' in df.columns and 'ask_size' in df.columns:
        bid_depth = df['bid_size']
        ask_depth = df['ask_size']
        metrics['bid_depth'] = bid_depth
        metrics['ask_depth'] = ask_depth
        metrics['depth_imbalance'] = (bid_depth - ask_depth) / (bid_depth + ask_depth + 1e-9)
        metrics['depth_weighted_mid'] = (df['bid'] * ask_depth + df['ask'] * bid_depth) / (bid_depth + ask_depth + 1e-9)
    else:
        metrics['bid_depth'] = 0.0
        metrics['ask_depth'] = 0.0
        metrics['depth_imbalance'] = 0.0
        metrics['depth_weighted_mid'] = df['tick_price']

    metrics['timestamp'] = df['timestamp'].values

    return metrics
