"""Order Flow Imbalance (OFI) calculations."""
import pandas as pd
import numpy as np


def compute_ofi_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute OFI at multiple time windows.

    Args:
        df: DataFrame with 'timestamp', 'bid', 'ask', 'bid_size', 'ask_size'

    Returns:
        DataFrame with OFI features
    """
    df = df.copy()

    # Compute OFI components (Chordia et al. 2002)
    df['bid_prev'] = df['bid'].shift(1)
    df['ask_prev'] = df['ask'].shift(1)
    df['bid_size_prev'] = df['bid_size'].shift(1).fillna(0)
    df['ask_size_prev'] = df['ask_size'].shift(1).fillna(0)

    # OFI bid component
    df['ofi_bid'] = 0.0
    mask_bid_up = df['bid'] >= df['bid_prev']
    mask_bid_down = df['bid'] < df['bid_prev']

    df.loc[mask_bid_up, 'ofi_bid'] = df.loc[mask_bid_up, 'bid_size'] - df.loc[mask_bid_up, 'bid_size_prev']
    df.loc[mask_bid_down, 'ofi_bid'] = -df.loc[mask_bid_down, 'bid_size_prev']

    # OFI ask component
    df['ofi_ask'] = 0.0
    mask_ask_down = df['ask'] <= df['ask_prev']
    mask_ask_up = df['ask'] > df['ask_prev']

    df.loc[mask_ask_down, 'ofi_ask'] = df.loc[mask_ask_down, 'ask_size_prev'] - df.loc[mask_ask_down, 'ask_size']
    df.loc[mask_ask_up, 'ofi_ask'] = df.loc[mask_ask_up, 'ask_size']

    # Total OFI
    df['ofi_raw'] = df['ofi_bid'] - df['ofi_ask']

    # Aggregate to time windows
    df = df.set_index('timestamp')

    ofi_1s = df['ofi_raw'].resample('1s').sum()
    ofi_5s = df['ofi_raw'].resample('5s').sum()
    ofi_1m = df['ofi_raw'].resample('60s').sum()

    # Combine
    result = pd.DataFrame({
        'ofi_1s': ofi_1s,
        'ofi_5s': ofi_5s,
        'ofi_1m': ofi_1m
    }).fillna(0)

    return result.reset_index()
