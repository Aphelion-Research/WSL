"""VPIN calculation (Volume-Synchronized PIN)."""
import pandas as pd
import numpy as np
from scipy import stats


def compute_vpin_detailed(df: pd.DataFrame, buckets_per_day: int = 50) -> pd.DataFrame:
    """Compute VPIN using bulk volume classification.

    Args:
        df: DataFrame with 'timestamp', 'tick_price', 'volume'
        buckets_per_day: Number of volume buckets per day

    Returns:
        DataFrame with 'timestamp', 'vpin' columns
    """
    if len(df) < buckets_per_day:
        result = pd.DataFrame({
            'timestamp': df['timestamp'],
            'vpin': 0.0
        })
        return result

    df = df.copy()

    # Ensure volume column exists
    if 'volume' not in df.columns:
        df['volume'] = 1.0

    # Compute bucket size
    daily_volume = df['volume'].sum()
    bucket_size = daily_volume / buckets_per_day

    if bucket_size == 0:
        result = pd.DataFrame({
            'timestamp': df['timestamp'],
            'vpin': 0.0
        })
        return result

    # Bulk volume classification using price changes
    df['price_change'] = df['tick_price'].diff().fillna(0)
    df['price_std'] = df['price_change'].rolling(20, min_periods=1).std().fillna(1.0)

    # Z-score for each price change
    df['z_score'] = df['price_change'] / (df['price_std'] + 1e-9)

    # Buy probability using CDF of standard normal
    df['buy_prob'] = stats.norm.cdf(df['z_score'])
    df['buy_vol'] = df['volume'] * df['buy_prob']
    df['sell_vol'] = df['volume'] * (1 - df['buy_prob'])

    # Create equal-volume buckets
    df['cumvol'] = df['volume'].cumsum()
    df['bucket_id'] = (df['cumvol'] / (bucket_size + 1e-9)).astype(int)

    # Aggregate by bucket
    bucket_agg = df.groupby('bucket_id').agg({
        'buy_vol': 'sum',
        'sell_vol': 'sum',
        'volume': 'sum'
    })

    bucket_agg['ofi_abs'] = (bucket_agg['buy_vol'] - bucket_agg['sell_vol']).abs()
    bucket_agg['vpin_bucket'] = bucket_agg['ofi_abs'] / (bucket_agg['volume'] + 1e-9)

    # Rolling average over 50 buckets
    bucket_agg['vpin'] = bucket_agg['vpin_bucket'].rolling(50, min_periods=1).mean()

    # Map back to original timestamps
    df = df.merge(bucket_agg[['vpin']], left_on='bucket_id', right_index=True, how='left')
    df['vpin'] = df['vpin'].fillna(0.0).clip(0, 1)

    result = df[['timestamp', 'vpin']].copy()
    return result
