"""Parity tests for vectorized features_stationary.py functions.

Compares vectorized implementations against reference scalar implementations
on deterministic toy arrays.
"""
import numpy as np
import pytest


# --- Reference (slow) implementations ---

def ref_rolling_zscore(close, windows):
    features = {}
    for w in windows:
        zscore = np.full(len(close), np.nan, dtype=np.float32)
        for i in range(w, len(close)):
            window = close[i-w:i]
            mean = window.mean()
            std = window.std()
            if std > 1e-10:
                z = (close[i] - mean) / std
                zscore[i] = np.clip(z, -5.0, 5.0)
        features[f"rolling_zscore_{w}"] = zscore
    return features


def ref_drawdown_pct(close, windows):
    features = {}
    for w in windows:
        dd_pct = np.full(len(close), np.nan, dtype=np.float32)
        for i in range(w, len(close)):
            window = close[i-w:i+1]
            peak = window.max()
            if peak > 1e-10:
                dd_pct[i] = (close[i] - peak) / peak
        features[f"drawdown_pct_{w}"] = dd_pct
    return features


def ref_realized_vol(close, windows):
    features = {}
    log_ret = np.full(len(close), np.nan, dtype=np.float32)
    log_ret[1:] = np.log(close[1:] / close[:-1]).astype(np.float32)
    for w in windows:
        rvol = np.full(len(close), np.nan, dtype=np.float32)
        for i in range(w, len(close)):
            window = log_ret[i-w+1:i+1]
            rvol[i] = window.std() * np.sqrt(252)
        features[f"realized_vol_{w}"] = rvol
    return features


def ref_sharpe_rolling(close, windows):
    features = {}
    log_ret = np.full(len(close), np.nan, dtype=np.float32)
    log_ret[1:] = np.log(close[1:] / close[:-1]).astype(np.float32)
    for w in windows:
        sharpe = np.full(len(close), np.nan, dtype=np.float32)
        for i in range(w, len(close)):
            window = log_ret[i-w+1:i+1]
            mean_ret = window.mean()
            std_ret = window.std()
            if std_ret > 1e-10:
                s = (mean_ret / std_ret) * np.sqrt(252)
                sharpe[i] = np.clip(s, -10.0, 10.0)
        features[f"sharpe_rolling_{w}"] = sharpe
    return features


def ref_volume_ratio(volume, window):
    vol_ma = np.full(len(volume), np.nan, dtype=np.float32)
    for i in range(window, len(volume)):
        vol_ma[i] = volume[i-window:i].mean()
    ratio = np.where(vol_ma > 1e-10, volume / vol_ma, 1.0)
    return np.clip(ratio, 0.0, 10.0).astype(np.float32)


def ref_bb_position(close, window, num_std):
    import pandas as pd
    bb_mid = np.full(len(close), np.nan, dtype=np.float32)
    bb_std = np.full(len(close), np.nan, dtype=np.float32)
    for i in range(window, len(close)):
        window_data = close[i-window:i]
        bb_mid[i] = window_data.mean()
        bb_std[i] = window_data.std()
    bb_upper = bb_mid + num_std * bb_std
    bb_lower = bb_mid - num_std * bb_std
    bb_width = bb_upper - bb_lower
    return np.where(bb_width > 1e-10, (close - bb_mid) / bb_width, 0.0).astype(np.float32)


# --- Deterministic test data ---

@pytest.fixture
def price_data():
    np.random.seed(42)
    n = 200
    close = 2000 + np.cumsum(np.random.randn(n) * 2).astype(np.float64)
    close = np.maximum(close, 100)  # keep positive
    return close


@pytest.fixture
def volume_data():
    np.random.seed(42)
    return (100 + np.random.rand(200) * 50).astype(np.float64)


# --- Tests ---

def test_rolling_zscore_parity(price_data):
    from hydra.data.features_stationary import compute_rolling_zscore
    windows = [5, 10, 20]
    ref = ref_rolling_zscore(price_data, windows)
    new = compute_rolling_zscore(price_data, windows)

    for key in ref:
        r, n = ref[key], new[key]
        # Compare only where reference is not NaN
        mask = np.isfinite(r)
        assert mask.sum() > 0, f"No valid values for {key}"
        np.testing.assert_allclose(n[mask], r[mask], rtol=1e-4, atol=1e-6,
                                   err_msg=f"Mismatch in {key}")


def test_drawdown_pct_parity(price_data):
    from hydra.data.features_stationary import compute_drawdown_pct
    windows = [5, 10, 20]
    ref = ref_drawdown_pct(price_data, windows)
    new = compute_drawdown_pct(price_data, windows)

    for key in ref:
        r, n = ref[key], new[key]
        mask = np.isfinite(r)
        assert mask.sum() > 0, f"No valid values for {key}"
        np.testing.assert_allclose(n[mask], r[mask], rtol=1e-4, atol=1e-6,
                                   err_msg=f"Mismatch in {key}")


def test_realized_vol_parity(price_data):
    from hydra.data.features_stationary import compute_realized_vol
    windows = [5, 10, 20]
    ref = ref_realized_vol(price_data, windows)
    new = compute_realized_vol(price_data, windows)

    for key in ref:
        r, n = ref[key], new[key]
        mask = np.isfinite(r)
        assert mask.sum() > 0, f"No valid values for {key}"
        np.testing.assert_allclose(n[mask], r[mask], rtol=1e-4, atol=1e-6,
                                   err_msg=f"Mismatch in {key}")


def test_sharpe_rolling_parity(price_data):
    from hydra.data.features_stationary import compute_sharpe_rolling
    windows = [5, 10, 20]
    ref = ref_sharpe_rolling(price_data, windows)
    new = compute_sharpe_rolling(price_data, windows)

    for key in ref:
        r, n = ref[key], new[key]
        mask = np.isfinite(r)
        assert mask.sum() > 0, f"No valid values for {key}"
        np.testing.assert_allclose(n[mask], r[mask], rtol=1e-4, atol=1e-6,
                                   err_msg=f"Mismatch in {key}")


def test_volume_ratio_parity(volume_data):
    from hydra.data.features_stationary import compute_volume_ratio
    ref = ref_volume_ratio(volume_data, 10)
    new = compute_volume_ratio(volume_data, 10)

    mask = np.isfinite(ref)
    assert mask.sum() > 0
    np.testing.assert_allclose(new[mask], ref[mask], rtol=1e-4, atol=1e-6)


def test_bb_position_parity(price_data):
    from hydra.data.features_stationary import compute_bb_position
    ref = ref_bb_position(price_data, 10, 2.0)
    new = compute_bb_position(price_data, 10, 2.0)

    mask = np.isfinite(ref)
    assert mask.sum() > 0
    # Wider tolerance: float32 output from float64 intermediate vs pure float32 ref
    np.testing.assert_allclose(new[mask], ref[mask], rtol=2e-3, atol=1e-5)
