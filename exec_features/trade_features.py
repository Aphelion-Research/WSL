"""Trade pattern features (10)."""
import pandas as pd
import numpy as np


def compute_trade_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 10 trade pattern features.

    Args:
        df: DataFrame with trade data

    Returns:
        DataFrame with trade features
    """
    features = pd.DataFrame(index=df.index)

    volume = df.get('volume', pd.Series([1.0] * len(df)))
    price = (df['bid'] + df['ask']) / 2
    price_change = price.diff().abs()

    features['trade_arrival_rate'] = 60.0  # placeholder: trades per minute
    features['trade_inter_duration'] = 1.0  # placeholder: seconds between trades

    avg_size = volume.rolling(20, min_periods=1).mean()
    features['trade_size_momentum'] = (volume / (avg_size + 1e-9)).fillna(1.0)
    features['trade_block_flag'] = (volume > 5 * avg_size).astype(int)

    features['trade_aggressive_buy_rate'] = 0.5  # placeholder
    features['trade_aggressive_sell_rate'] = 0.5  # placeholder
    features['trade_direction_run'] = 0  # placeholder
    features['trade_volume_clock_speed'] = 1.0  # placeholder
    features['trade_price_impact_per_trade'] = (price_change / (volume + 1e-9)).fillna(0)
    features['trade_tick_rule_accuracy'] = 0.8  # placeholder

    return features
