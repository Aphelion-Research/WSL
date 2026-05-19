"""Depth/book features (10)."""
import pandas as pd
import numpy as np


def compute_depth_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute 10 depth features.

    Args:
        df: DataFrame with 'bid', 'ask', 'bid_size', 'ask_size'

    Returns:
        DataFrame with depth features
    """
    features = pd.DataFrame(index=df.index)

    bid_depth = df['bid_size']
    ask_depth = df['ask_size']
    total_depth = bid_depth + ask_depth

    features['depth_total_bid'] = bid_depth
    features['depth_total_ask'] = ask_depth
    features['depth_imbalance'] = ((bid_depth - ask_depth) / (total_depth + 1e-9)).fillna(0)
    features['depth_ratio'] = (bid_depth / (ask_depth + 1e-9)).fillna(1.0)
    features['depth_weighted_mid'] = ((df['bid'] * ask_depth + df['ask'] * bid_depth) / (total_depth + 1e-9)).fillna((df['bid'] + df['ask']) / 2)
    features['depth_top_bid_size'] = bid_depth
    features['depth_top_ask_size'] = ask_depth
    features['depth_book_pressure'] = (bid_depth - ask_depth).fillna(0)
    features['depth_at_1bps'] = total_depth  # simplified
    features['depth_momentum'] = features['depth_imbalance'].diff(5).fillna(0)

    return features
