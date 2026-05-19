"""Order flow features (10)."""
import pandas as pd
import numpy as np


def compute_flow_features(df: pd.DataFrame, ofi_df: pd.DataFrame) -> pd.DataFrame:
    """Compute 10 order flow features.

    Args:
        df: DataFrame with price/volume data
        ofi_df: DataFrame with pre-computed OFI values

    Returns:
        DataFrame with flow features
    """
    features = pd.DataFrame(index=df.index)

    # Merge OFI data
    if not ofi_df.empty and 'ofi_1s' in ofi_df.columns:
        merged = df.merge(ofi_df[['timestamp', 'ofi_1s', 'ofi_5s', 'ofi_1m']], on='timestamp', how='left')
        features['flow_ofi_1s'] = merged['ofi_1s'].fillna(0)
        features['flow_ofi_5s'] = merged['ofi_5s'].fillna(0)
        features['flow_ofi_1m'] = merged['ofi_1m'].fillna(0)
    else:
        features['flow_ofi_1s'] = 0.0
        features['flow_ofi_5s'] = 0.0
        features['flow_ofi_1m'] = 0.0

    # Volume features
    volume = df.get('volume', pd.Series([1.0] * len(df)))
    features['flow_signed_volume'] = features['flow_ofi_1s']  # simplified
    features['flow_buy_sell_ratio'] = 0.5  # placeholder
    features['flow_vpin'] = 0.3  # placeholder

    features['flow_trade_size_avg'] = volume.rolling(20, min_periods=1).mean().fillna(1.0)
    features['flow_trade_size_std'] = volume.rolling(20, min_periods=1).std().fillna(0.0)
    features['flow_trade_size_skew'] = volume.rolling(50, min_periods=1).skew().fillna(0.0)
    features['flow_volume_surge'] = (volume / (volume.rolling(60, min_periods=1).mean() + 1e-9)).fillna(1.0)

    return features
