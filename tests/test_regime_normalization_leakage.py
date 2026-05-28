"""
Test: Regime Normalization Leakage
===================================
Verify that future volatility spikes do NOT change earlier features.
"""
import pytest
import numpy as np
import pandas as pd
from hydra.data.features_stationary import compute_regime_probs


def test_regime_normalization_no_future_leakage():
    """Test that adding future vol spike doesn't change past features.

    This test would FAIL with global normalization:
        vol_norm = (vol - np.nanmin(vol)) / (np.nanmax(vol) - np.nanmin(vol))

    Should PASS with rolling normalization:
        vol_q25 = vol_series.shift(1).rolling(252).quantile(0.25)
        vol_q75 = vol_series.shift(1).rolling(252).quantile(0.75)
        vol_norm = (vol - vol_q25) / (vol_q75 - vol_q25)
    """
    # Create price series with stable volatility
    np.random.seed(42)
    n = 1000
    close = 2000 + np.cumsum(np.random.randn(n) * 0.5)

    # Compute regime features on original data
    regime_orig = compute_regime_probs(close, window=50)
    crisis_prob_orig = regime_orig["regime_crisis_prob"]

    # Now add a massive volatility spike at the END (bars 900-950)
    close_with_spike = close.copy()
    close_with_spike[900:950] = close_with_spike[900:950] + np.random.randn(50) * 20  # 40x vol spike

    # Recompute features with spike
    regime_spike = compute_regime_probs(close_with_spike, window=50)
    crisis_prob_spike = regime_spike["regime_crisis_prob"]

    # Check: features BEFORE spike (bars 0-850) should be UNCHANGED
    # With global normalization, they would change because global max changed
    # With rolling normalization, they stay the same

    # Compare features in early period (bars 300-800, well before spike)
    early_period = slice(300, 800)

    # Allow tiny numerical differences but no systematic shift
    diff = np.abs(crisis_prob_orig[early_period] - crisis_prob_spike[early_period])
    max_diff = np.nanmax(diff)

    # With global norm: max_diff would be ~0.5-0.8 (massive shift)
    # With rolling norm: max_diff should be ~0.0 (no shift)
    assert max_diff < 0.01, (
        f"Future vol spike changed past features by {max_diff:.4f}. "
        f"This indicates global normalization leakage."
    )


def test_regime_normalization_uses_past_only():
    """Test that normalization at bar T uses only bars [T-N, T-1]."""
    np.random.seed(42)
    n = 500
    close = 2000 + np.cumsum(np.random.randn(n) * 0.5)

    regime = compute_regime_probs(close, window=50)
    crisis_prob = regime["regime_crisis_prob"]

    # Check that first 252 bars are NaN (not enough history for rolling quantiles)
    assert np.isnan(crisis_prob[:252]).all(), (
        "First 252 bars should be NaN (insufficient history for rolling norm)"
    )

    # Check that features at bar 300 are NOT NaN
    assert not np.isnan(crisis_prob[300]), (
        "Features at bar 300 should be valid (252+ bars of history)"
    )


def test_regime_normalization_robustness():
    """Test that regime features are robust to extreme outliers."""
    np.random.seed(42)
    n = 500
    close = 2000 + np.cumsum(np.random.randn(n) * 0.5)

    # Add single extreme outlier at bar 350
    close_with_outlier = close.copy()
    close_with_outlier[350] = close_with_outlier[350] + 500  # massive spike

    regime = compute_regime_probs(close_with_outlier, window=50)
    crisis_prob = regime["regime_crisis_prob"]

    # Check that outlier doesn't cause NaN propagation
    assert not np.isnan(crisis_prob[360:400]).any(), (
        "Outlier should not cause NaN propagation in later bars"
    )

    # Check that crisis prob is elevated near outlier (expected)
    assert crisis_prob[360] > 0.5, (
        "Crisis probability should be elevated after extreme move"
    )
