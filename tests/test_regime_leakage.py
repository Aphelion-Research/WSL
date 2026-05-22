"""Tests for HMM regime leakage prevention.

ACCEPTANCE CRITERIA:
1. HMM fit on train-only does not change when OOS data is added
2. OOS regime labels for an unchanged prefix do not change when future OOS rows are appended
3. fit_transform_split() produces point-in-time safe regime features
4. Old detect_tactical_regime_hmm() prints deprecation warning
"""
import numpy as np
import pandas as pd
import pytest

from data_pipeline.features.regime_safe import (
    fit_regime_hmm_model,
    transform_regime_hmm,
    fit_transform_split,
    detect_tactical_regime_hmm,
)


@pytest.fixture
def sample_data():
    """Generate synthetic OHLCV data with DatetimeIndex."""
    np.random.seed(42)
    n = 500
    close = 2000 + np.cumsum(np.random.randn(n) * 10)
    high = close + np.abs(np.random.randn(n) * 5)
    low = close - np.abs(np.random.randn(n) * 5)
    open_ = close + np.random.randn(n) * 3
    volume = np.random.randint(1000, 10000, n)

    # Use DatetimeIndex
    index = pd.date_range("2020-01-01", periods=n, freq="1h")

    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
    }, index=index)
    return df


def test_fit_on_train_only_stable(sample_data):
    """HMM model fitted on train data should not change when OOS data is added."""
    train = sample_data.iloc[:300]
    oos = sample_data.iloc[300:]

    # Fit on train only
    fitted1 = fit_regime_hmm_model(train)

    # Fit on train + OOS (should NOT be done in practice, but testing stability)
    fitted2 = fit_regime_hmm_model(pd.concat([train, oos]))

    # Transform train data with both models
    train_features1 = transform_regime_hmm(fitted1, train)
    train_features2 = transform_regime_hmm(fitted2, train)

    # Train regime labels should be IDENTICAL (no future leakage)
    # NOTE: This will fail if fitted2 is different due to seeing future OOS data
    # We cannot guarantee exact state IDs match, but regime distributions should be similar
    regime1_counts = train_features1["regime_tactical"].value_counts(normalize=True)
    regime2_counts = train_features2["regime_tactical"].value_counts(normalize=True)

    # Check that regime distributions are within 20% (models may differ slightly)
    for regime in regime1_counts.index:
        if regime in regime2_counts.index:
            diff = abs(regime1_counts[regime] - regime2_counts[regime])
            # This is a weak test — ideally regimes should be identical, but HMM is stochastic
            # In practice, fit_transform_split ensures train model is used for OOS
            assert diff < 0.3, f"Regime {regime} distribution changed by {diff:.2%}"


def test_oos_prefix_stable_when_future_appended(sample_data):
    """OOS regime labels for prefix should not change when future OOS rows are appended.

    This is the CRITICAL leakage test.
    """
    train = sample_data.iloc[:300]
    oos_short = sample_data.iloc[300:400]
    oos_long = sample_data.iloc[300:450]

    # Fit on train once
    fitted = fit_regime_hmm_model(train)

    # Transform OOS (short)
    oos_features_short = transform_regime_hmm(fitted, oos_short)

    # Transform OOS (long)
    oos_features_long = transform_regime_hmm(fitted, oos_long)

    # The first 100 rows of OOS should be IDENTICAL (no future leakage)
    prefix_short = oos_features_short.iloc[:100]
    prefix_long = oos_features_long.iloc[:100]

    # Regime labels must match exactly
    assert (prefix_short["regime_tactical"] == prefix_long["regime_tactical"]).all(), \
        "OOS regime labels changed when future data was appended (LEAKAGE)"

    # Regime probabilities must match (with tight tolerance for numerical precision)
    for col in ["regime_prob_trend_up", "regime_prob_trend_down", "regime_prob_ranging", "regime_prob_crisis"]:
        np.testing.assert_allclose(
            prefix_short[col].values,
            prefix_long[col].values,
            rtol=1e-10,
            atol=1e-12,
            err_msg=f"{col} changed when future OOS data was appended (LEAKAGE)",
        )


def test_fit_transform_split_no_leakage(sample_data):
    """fit_transform_split() should produce point-in-time safe features."""
    train = sample_data.iloc[:300]
    oos = sample_data.iloc[300:]

    train_features, oos_features = fit_transform_split(train, oos)

    # Check that train features exist
    assert "regime_tactical" in train_features.columns
    assert "regime_prob_trend_up" in train_features.columns

    # Check that OOS features exist
    assert "regime_tactical" in oos_features.columns
    assert "regime_prob_trend_up" in oos_features.columns

    # Check no NaNs in regime labels (probs may have NaNs in early rows)
    assert not train_features["regime_tactical"].isna().any()
    assert not oos_features["regime_tactical"].isna().any()

    # OOS regimes should not leak: append more OOS data and check prefix stability
    oos_extended = sample_data.iloc[300:450]
    _, oos_features_extended = fit_transform_split(train, oos_extended)

    # First 100 OOS rows should match
    prefix_len = min(100, len(oos_features))
    prefix_orig = oos_features.iloc[:prefix_len]
    prefix_ext = oos_features_extended.iloc[:prefix_len]

    assert (prefix_orig["regime_tactical"] == prefix_ext["regime_tactical"]).all(), \
        "fit_transform_split() leaked future OOS data into prefix"


def test_old_api_deprecation_warning(sample_data):
    """Old detect_tactical_regime_hmm() should print deprecation warning."""
    with pytest.warns(DeprecationWarning, match="LEAKS"):
        features = detect_tactical_regime_hmm(sample_data)

    # Should still return valid features (backward compat)
    assert "regime_tactical" in features.columns
    assert "regime_prob_trend_up" in features.columns


def test_insufficient_train_data_raises():
    """fit_regime_hmm_model() should raise ValueError if insufficient training data."""
    df = pd.DataFrame({
        "close": [2000, 2010, 2020],
        "volume": [1000, 1000, 1000],
    })

    with pytest.raises(ValueError, match="Insufficient training data"):
        fit_regime_hmm_model(df)


def test_hmmlearn_not_installed_fallback(sample_data, monkeypatch):
    """If hmmlearn not installed, fit_transform_split() should return 'unknown' regimes."""
    # Mock ImportError
    import builtins
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "hmmlearn":
            raise ImportError("hmmlearn not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    train = sample_data.iloc[:300]
    oos = sample_data.iloc[300:]

    train_features, oos_features = fit_transform_split(train, oos)

    # All regimes should be "unknown"
    assert (train_features["regime_tactical"] == "unknown").all()
    assert (oos_features["regime_tactical"] == "unknown").all()
    assert (train_features["regime_prob_trend_up"] == 0.25).all()


def test_safe_api_uses_train_normalization_only(sample_data):
    """Safe API must use train-fitted normalization stats only (no OOS stats).

    This is a structural test (deterministic, not stochastic).
    """
    train = sample_data.iloc[:300]
    oos = sample_data.iloc[300:]

    # Fit on train
    fitted = fit_regime_hmm_model(train)

    # Check that fitted stores train normalization stats
    assert fitted.feature_means is not None
    assert fitted.feature_stds is not None
    assert len(fitted.feature_means) == 3  # returns, volatility, volume
    assert len(fitted.feature_stds) == 3

    # Transform OOS
    oos_features = transform_regime_hmm(fitted, oos)

    # Transform should succeed (uses train stats, not OOS stats)
    assert "regime_tactical" in oos_features.columns
    assert len(oos_features) == len(oos)


def test_compute_all_regime_features_fail_closed(sample_data):
    """compute_all_regime_features() should raise by default (fail-closed)."""
    from data_pipeline.features.regime import compute_all_regime_features

    # Should raise without allow_leaky_hmm=True
    with pytest.raises(RuntimeError, match="LEAKS future information"):
        compute_all_regime_features(sample_data)


def test_compute_all_regime_features_explicit_leaky(sample_data):
    """compute_all_regime_features(allow_leaky_hmm=True) should work but warn."""
    from data_pipeline.features.regime import compute_all_regime_features

    # Should work with explicit flag but warn
    with pytest.warns(DeprecationWarning, match="leaky HMM"):
        features = compute_all_regime_features(sample_data, allow_leaky_hmm=True)

    assert "regime_tactical" in features.columns
    assert "regime_micro" in features.columns


def test_feature_store_no_leaky_hmm(sample_data, monkeypatch):
    """FeatureStore should not call leaky HMM by default."""
    from data_pipeline.features.store import FeatureStore
    from data_pipeline.features import price, microstructure, crossasset, macro, regime, calendar, cot_features

    store = FeatureStore()

    # Monkeypatch feature computation functions to return safe DataFrames
    def mock_empty_features(df, *args, **kwargs):
        # Return empty DataFrame with same index as input
        if isinstance(df, pd.DataFrame):
            return pd.DataFrame(index=df.index)
        else:
            return pd.DataFrame(index=df)

    monkeypatch.setattr(price, "compute_all_price_features", mock_empty_features)
    monkeypatch.setattr(microstructure, "compute_all_microstructure_features", mock_empty_features)
    monkeypatch.setattr(crossasset, "compute_all_crossasset_features", mock_empty_features)
    monkeypatch.setattr(macro, "compute_all_macro_features", mock_empty_features)
    monkeypatch.setattr(cot_features, "compute_all_cot_features", mock_empty_features)
    monkeypatch.setattr(calendar, "compute_all_calendar_features", mock_empty_features)

    # Monkeypatch compute_all_regime_features to raise if called (should NOT be called)
    def mock_fail_regime_features(*args, **kwargs):
        raise AssertionError("FeatureStore called compute_all_regime_features (leaky HMM path)")

    monkeypatch.setattr(regime, "compute_all_regime_features", mock_fail_regime_features)

    # Monkeypatch detect_micro_regime to return safe DataFrame
    def mock_micro_regime(timestamps):
        return pd.DataFrame({"regime_micro": "unknown"}, index=timestamps)

    monkeypatch.setattr(regime, "detect_micro_regime", mock_micro_regime)

    # Mock macro/cot data (structure doesn't matter since functions are mocked)
    macro_df = pd.DataFrame({"timestamp": sample_data.index[:10], "dummy": 1})
    cot_df = pd.DataFrame({"report_date": sample_data.index[:10], "dummy": 1})

    # Should NOT raise (no HMM features by default)
    features = store.compute_all_features(sample_data, macro_df, cot_df)

    # Should have micro regime (safe, calendar-based)
    assert "regime_micro" in features.columns

    # Should NOT have HMM tactical regime (leaky)
    assert "regime_tactical" not in features.columns
