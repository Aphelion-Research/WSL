"""Test data contract validation."""
import pytest
import pandas as pd
import numpy as np
from research_core.data_contracts import (
    validate_features,
    validate_ohlcv,
    validate_timestamps,
    check_forbidden_columns,
    ValidationError,
)


def test_forbidden_columns_rejected():
    """Forbidden feature columns should be rejected."""
    df = pd.DataFrame({
        "feature_1": [1, 2, 3],
        "fwd_return": [0.01, -0.02, 0.03],  # FORBIDDEN
    }, index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    with pytest.raises(ValidationError, match="Found forbidden patterns"):
        check_forbidden_columns(df)


def test_forbidden_columns_with_label_allowed():
    """Label column allowed when explicitly permitted."""
    df = pd.DataFrame({
        "feature_1": [1, 2, 3],
        "label": [1, 0, 1],
    }, index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    # Should pass with allow_label=True
    result = check_forbidden_columns(df, allow_label=True)
    assert result["clean"]

    # Should fail with allow_label=False
    with pytest.raises(ValidationError):
        check_forbidden_columns(df, allow_label=False)


def test_non_monotonic_timestamps_rejected():
    """Non-monotonic timestamps should be rejected."""
    df = pd.DataFrame({
        "feature_1": [1, 2, 3],
    }, index=pd.to_datetime(["2024-01-01 10:00", "2024-01-01 09:00", "2024-01-01 11:00"]))

    with pytest.raises(ValidationError, match="monotonic"):
        validate_timestamps(df)


def test_duplicate_timestamps_rejected():
    """Duplicate timestamps should be rejected."""
    df = pd.DataFrame({
        "feature_1": [1, 2, 3],
    }, index=pd.to_datetime(["2024-01-01 10:00", "2024-01-01 10:00", "2024-01-01 11:00"]))

    with pytest.raises(ValidationError, match="duplicate"):
        validate_timestamps(df)


def test_valid_timestamps_pass():
    """Valid monotonic unique timestamps should pass."""
    df = pd.DataFrame({
        "feature_1": [1, 2, 3],
    }, index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    result = validate_timestamps(df)
    assert result["monotonic"]
    assert result["duplicates"] == 0
    assert len(result["errors"]) == 0


def test_missing_ohlcv_columns():
    """Missing required OHLCV columns should be rejected."""
    df = pd.DataFrame({
        "open": [100, 101, 102],
        "close": [101, 102, 103],
        # Missing high, low, spread
    }, index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    with pytest.raises(ValidationError, match="Missing required"):
        validate_ohlcv(df)


def test_valid_ohlcv_pass():
    """Valid OHLCV DataFrame should pass."""
    df = pd.DataFrame({
        "open": [100, 101, 102],
        "high": [101, 102, 103],
        "low": [99, 100, 101],
        "close": [101, 102, 103],
        "spread": [0.3, 0.3, 0.3],
    }, index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    result = validate_ohlcv(df)
    assert result["has_required"]
    assert len(result["missing"]) == 0


def test_comprehensive_feature_validation():
    """Full feature validation workflow."""
    df = pd.DataFrame({
        "rsi_14": [50, 55, 60],
        "atr_3h_pct": [0.01, 0.02, 0.015],
    }, index=pd.date_range("2024-01-01", periods=3, freq="1H"))

    result = validate_features(df, allow_label=False, check_bfill=False)
    assert result["timestamps"]["monotonic"]
    assert result["columns"]["clean"]
