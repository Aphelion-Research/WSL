"""Tests for execution features."""
import pytest
import pandas as pd
import numpy as np
from exec_features.spread_features import compute_spread_features
from exec_features.depth_features import compute_depth_features
from exec_features.flow_features import compute_flow_features
from exec_features.store import compute_all_features
from exec_features.ic_tracker import compute_ic, compute_forward_returns


def test_spread_features_count():
    """Test spread features returns 10 columns."""
    df = pd.DataFrame({
        'bid': [2000.0] * 100,
        'ask': [2001.0] * 100,
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min')
    })

    features = compute_spread_features(df)
    assert len(features.columns) == 10


def test_depth_features_count():
    """Test depth features returns 10 columns."""
    df = pd.DataFrame({
        'bid': [2000.0] * 100,
        'ask': [2001.0] * 100,
        'bid_size': [10.0] * 100,
        'ask_size': [10.0] * 100
    })

    features = compute_depth_features(df)
    assert len(features.columns) == 10


def test_flow_features_count():
    """Test flow features returns 10 columns."""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='1min'),
        'volume': [1.0] * 100
    })

    ofi_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'ofi_1s': 0.0,
        'ofi_5s': 0.0,
        'ofi_1m': 0.0
    })

    features = compute_flow_features(df, ofi_df)
    assert len(features.columns) == 10


def test_compute_all_features():
    """Test compute_all_features integrates all groups."""
    df = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=50, freq='1min'),
        'bid': [2000.0] * 50,
        'ask': [2001.0] * 50,
        'bid_size': [10.0] * 50,
        'ask_size': [10.0] * 50,
        'volume': [1.0] * 50
    })

    features = compute_all_features(df)

    # Should have timestamp + 50 features
    assert 'timestamp' in features.columns
    assert len(features.columns) >= 51  # timestamp + 50 features


def test_ic_bounded():
    """Test IC is in [-1, 1]."""
    feature_series = pd.Series(np.random.randn(100))
    forward_returns = pd.Series(np.random.randn(100))

    ic = compute_ic(feature_series, forward_returns, window=20)

    assert ic.min() >= -1.0
    assert ic.max() <= 1.0


def test_forward_returns():
    """Test forward returns computes correctly."""
    prices = pd.Series([100, 101, 102, 103, 104])

    fwd_returns = compute_forward_returns(prices, horizon_minutes=1)

    # fwd_returns[0] = (prices[1] - prices[0]) / prices[0] = 1/100 = 0.01
    assert abs(fwd_returns.iloc[0] - 0.01) < 0.001
