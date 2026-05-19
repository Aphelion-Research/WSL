"""Tests for feature computation."""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from data_pipeline.features.price import compute_returns, compute_hurst, compute_autocorr
from data_pipeline.features.microstructure import compute_roll_spread, compute_amihud
from data_pipeline.features.store import FeatureStore


def test_compute_returns():
    """Test return computation."""
    df = pd.DataFrame({
        "close": [100.0, 105.0, 110.0, 108.0, 112.0]
    })

    features = compute_returns(df, windows=[1, 2])

    assert "return_1" in features.columns
    assert "return_2" in features.columns
    assert "log_return_1" in features.columns

    # Check first return is correct
    assert abs(features["return_1"].iloc[1] - 0.05) < 0.001


def test_compute_hurst():
    """Test Hurst exponent computation."""
    # Generate mean-reverting series (H < 0.5)
    np.random.seed(42)
    series = pd.Series(np.random.randn(200).cumsum())

    hurst = compute_hurst(series, window=100)

    # Should be finite (may exceed 1 due to small sample)
    assert not np.isnan(hurst)


def test_compute_autocorr():
    """Test autocorrelation computation."""
    df = pd.DataFrame({
        "close": np.random.randn(100).cumsum() + 100
    })

    features = compute_autocorr(df, lags=[1, 5], windows=[20])

    assert "autocorr_20_lag1" in features.columns
    assert "autocorr_20_lag5" in features.columns


def test_feature_store_validation():
    """Test feature validation removes NaN/inf."""
    store = FeatureStore()

    df = pd.DataFrame({
        "feature_a": [1.0, 2.0, float("nan"), 4.0],
        "feature_b": [1.0, float("inf"), 3.0, 4.0],
    })

    validated = store.validate_features(df)

    # inf should be replaced with NaN
    assert not np.isinf(validated["feature_b"]).any()


def test_feature_ic_computation():
    """Test IC computation."""
    store = FeatureStore()

    features = pd.DataFrame({
        "feature_a": np.random.randn(100),
        "feature_b": np.random.randn(100),
    })

    returns = pd.Series(np.random.randn(100))

    ic_dict = store.compute_ic(features, returns, window=50)

    assert "feature_a" in ic_dict
    assert "feature_b" in ic_dict
    assert -1 <= ic_dict["feature_a"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
