"""
Tests for Leakage Validation Module
====================================
"""
import pytest
import numpy as np
import pandas as pd
from utils.leakage_validation import (
    check_timestamps_monotonic,
    check_forbidden_columns,
    check_embargo_sufficient,
    check_fold_boundaries,
    check_config_contamination,
    validate_pipeline
)


def test_timestamps_monotonic_pass():
    """Test monotonic timestamps pass."""
    df = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods=100, freq="5min"),
        "close": np.random.randn(100)
    })
    valid, msg = check_timestamps_monotonic(df)
    assert valid
    assert msg is None


def test_timestamps_monotonic_fail():
    """Test non-monotonic timestamps fail."""
    df = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods=100, freq="5min"),
        "close": np.random.randn(100)
    })
    # Swap two timestamps
    df.loc[50, "ts"], df.loc[51, "ts"] = df.loc[51, "ts"], df.loc[50, "ts"]

    valid, msg = check_timestamps_monotonic(df)
    assert not valid
    assert "Non-monotonic" in msg


def test_forbidden_columns_pass():
    """Test valid feature names pass."""
    features = ["ema_9", "rsi_14", "volume_ratio", "atr_pct"]
    valid, forbidden = check_forbidden_columns(features)
    assert valid
    assert len(forbidden) == 0


def test_forbidden_columns_fail():
    """Test forbidden feature names fail."""
    features = ["ema_9", "fwd_return_12", "next_close", "target_label", "pnl"]
    valid, forbidden = check_forbidden_columns(features)
    assert not valid
    assert "fwd_return_12" in forbidden
    assert "next_close" in forbidden
    assert "target_label" in forbidden
    assert "pnl" in forbidden


def test_embargo_sufficient_pass():
    """Test sufficient embargo passes."""
    valid, msg = check_embargo_sufficient(
        embargo_bars=252,
        label_horizon_bars=12,
        max_hold_bars=96
    )
    assert valid
    assert msg is None


def test_embargo_sufficient_fail():
    """Test insufficient embargo fails."""
    valid, msg = check_embargo_sufficient(
        embargo_bars=10,
        label_horizon_bars=12,
        max_hold_bars=96
    )
    assert not valid
    assert "too small" in msg


def test_fold_boundaries_pass():
    """Test valid fold boundaries pass."""
    df = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods=1000, freq="5min"),
        "close": np.random.randn(1000)
    })
    fold = {
        "test_idx": np.arange(500, 700)  # ends at 700, data ends at 999, 299 bar buffer
    }
    valid, msg = check_fold_boundaries(df, fold, label_horizon_bars=252)
    assert valid
    assert msg is None


def test_fold_boundaries_fail():
    """Test fold extending past data end fails."""
    df = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods=1000, freq="5min"),
        "close": np.random.randn(1000)
    })
    fold = {
        "test_idx": np.arange(500, 990)  # ends at 990, only 9 bar buffer
    }
    valid, msg = check_fold_boundaries(df, fold, label_horizon_bars=252)
    assert not valid
    assert "extends too close" in msg


def test_config_contamination_pass():
    """Test config selected before test period passes."""
    valid, msg = check_config_contamination(
        config_selection_period="2023-2024",
        test_period="2025-2026"
    )
    assert valid
    assert msg is None


def test_config_contamination_fail():
    """Test config selected on test data fails."""
    valid, msg = check_config_contamination(
        config_selection_period="2025-2026",
        test_period="2026"
    )
    assert not valid
    assert "CONTAMINATED" in msg


def test_validate_pipeline_pass():
    """Test full pipeline validation passes."""
    df = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods=10000, freq="5min"),
        "close": np.cumsum(np.random.randn(10000)),
        "ema_9": np.random.randn(10000),
        "rsi_14": np.random.randn(10000),
    })

    feature_cols = ["ema_9", "rsi_14"]
    fold = {
        "train_idx": np.arange(0, 5000),
        "val_idx": np.arange(5300, 7000),
        "test_idx": np.arange(7300, 9000),
        "embargo_bars": 252
    }

    results = validate_pipeline(
        df=df,
        feature_cols=feature_cols,
        fold=fold,
        label_horizon_bars=12,
        max_hold_bars=96,
        config_selection_period="2024",
        test_period="2025"
    )

    assert results["is_valid"]
    assert len(results["errors"]) == 0


def test_validate_pipeline_fail_multiple():
    """Test pipeline validation catches multiple issues."""
    # Non-monotonic timestamps
    df = pd.DataFrame({
        "ts": pd.date_range("2020-01-01", periods=1000, freq="5min"),
        "close": np.random.randn(1000),
        "ema_9": np.random.randn(1000),
        "fwd_return": np.random.randn(1000),  # forbidden
    })
    df.loc[50, "ts"], df.loc[51, "ts"] = df.loc[51, "ts"], df.loc[50, "ts"]

    feature_cols = ["ema_9", "fwd_return"]  # includes forbidden
    fold = {
        "train_idx": np.arange(0, 500),
        "test_idx": np.arange(500, 990),  # too close to end
        "embargo_bars": 5  # insufficient
    }

    results = validate_pipeline(
        df=df,
        feature_cols=feature_cols,
        fold=fold,
        label_horizon_bars=12,
        max_hold_bars=96,
        config_selection_period="2025",  # contaminated
        test_period="2025"
    )

    assert not results["is_valid"]
    assert len(results["errors"]) >= 3
    assert any("Non-monotonic" in e for e in results["errors"])
    assert any("Forbidden" in e for e in results["errors"])
    assert any("too small" in e for e in results["errors"])
