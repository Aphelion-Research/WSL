"""Parity tests for vectorized triple_barrier label_directional.

Tests fast chunked vectorized path against a reference scalar implementation.
"""
import numpy as np
import pytest


def ref_label_directional(high, low, close, atr, spread, direction,
                          horizon, stop_mult, target_mult, min_atr_pct,
                          min_hold_bars, spread_to_atr_min):
    """Reference scalar implementation (original algorithm)."""
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    mfe = np.full(n, np.nan, dtype=np.float32)
    mae = np.full(n, np.nan, dtype=np.float32)

    for t in range(n - horizon):
        if not np.isfinite(atr[t]) or atr[t] <= 0:
            continue
        if close[t] == 0 or atr[t] / close[t] < min_atr_pct:
            continue
        if atr[t] < spread[t] / spread_to_atr_min:
            continue

        entry = close[t]
        if direction == 1:
            stop_px = entry - stop_mult * atr[t]
            target_px = entry + target_mult * atr[t]
        else:
            stop_px = entry + stop_mult * atr[t]
            target_px = entry - target_mult * atr[t]

        max_fav = 0.0
        max_adv = 0.0
        hit_bar = -1

        for k in range(1, horizon + 1):
            if direction == 1:
                fav = (high[t + k] - entry) / atr[t]
                adv = (low[t + k] - entry) / atr[t]
                max_fav = max(max_fav, fav)
                max_adv = min(max_adv, adv)
                if low[t + k] <= stop_px and k >= min_hold_bars:
                    y[t] = 0.0
                    hit_bar = k
                    break
                if high[t + k] >= target_px and k >= min_hold_bars:
                    y[t] = 1.0
                    hit_bar = k
                    break
            else:
                fav = (entry - low[t + k]) / atr[t]
                adv = (entry - high[t + k]) / atr[t]
                max_fav = max(max_fav, fav)
                max_adv = min(max_adv, adv)
                if high[t + k] >= stop_px and k >= min_hold_bars:
                    y[t] = 0.0
                    hit_bar = k
                    break
                if low[t + k] <= target_px and k >= min_hold_bars:
                    y[t] = 1.0
                    hit_bar = k
                    break

        if hit_bar > 0:
            mfe[t] = max_fav
            mae[t] = max_adv

    return y, mfe, mae


@pytest.fixture
def synth_ohlc():
    """Deterministic synthetic OHLC with trends and reversals."""
    np.random.seed(123)
    n = 300
    # Random walk with drift
    returns = np.random.randn(n) * 0.005
    close = 2000 * np.exp(np.cumsum(returns))
    noise = np.abs(np.random.randn(n)) * 2
    high = close + noise
    low = close - noise
    # Ensure OHLC consistency
    high = np.maximum(high, close)
    low = np.minimum(low, close)
    return high, low, close


@pytest.fixture
def synth_atr_spread(synth_ohlc):
    """Compute ATR and spread for test data."""
    high, low, close = synth_ohlc
    n = len(close)
    # Simple ATR approximation
    tr = high - low
    atr = np.full(n, np.nan, dtype=np.float64)
    period = 14
    atr[period - 1] = tr[:period].mean()
    for i in range(period, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    spread = np.full(n, 0.3, dtype=np.float32)
    return atr, spread


class TestLabelDirectionalParity:
    """Compare vectorized vs reference for multiple configurations."""

    def _run_parity(self, synth_ohlc, synth_atr_spread, direction, horizon,
                    stop_mult, target_mult, min_hold_bars):
        from hydra.labels.triple_barrier import TripleBarrierLabeler

        high, low, close = synth_ohlc
        atr, spread = synth_atr_spread

        labeler = TripleBarrierLabeler(
            atr_window=14,
            horizon_bars=horizon,
            stop_mult=stop_mult,
            target_mult=target_mult,
            min_atr_pct=0.0001,
            min_hold_bars=min_hold_bars,
            spread_to_atr_min=0.33,
        )

        # Fast (vectorized)
        y_fast, mfe_fast, mae_fast = labeler.label_directional(
            high, low, close, atr, spread, direction)

        # Reference (scalar)
        y_ref, mfe_ref, mae_ref = ref_label_directional(
            high, low, close, atr, spread, direction,
            horizon=horizon, stop_mult=stop_mult, target_mult=target_mult,
            min_atr_pct=0.0001, min_hold_bars=min_hold_bars,
            spread_to_atr_min=0.33)

        # Compare labels
        both_nan = np.isnan(y_ref) & np.isnan(y_fast)
        both_valid = np.isfinite(y_ref) & np.isfinite(y_fast)
        assert (both_nan | both_valid).all(), \
            f"NaN pattern mismatch: ref has {np.isfinite(y_ref).sum()} valid, " \
            f"fast has {np.isfinite(y_fast).sum()} valid"

        if both_valid.any():
            np.testing.assert_array_equal(y_fast[both_valid], y_ref[both_valid],
                                          err_msg="Label values differ")

        # Compare MFE/MAE where both have values
        mfe_valid = np.isfinite(mfe_ref) & np.isfinite(mfe_fast)
        if mfe_valid.any():
            np.testing.assert_allclose(mfe_fast[mfe_valid], mfe_ref[mfe_valid],
                                       rtol=1e-5, atol=1e-7)

        mae_valid = np.isfinite(mae_ref) & np.isfinite(mae_fast)
        if mae_valid.any():
            np.testing.assert_allclose(mae_fast[mae_valid], mae_ref[mae_valid],
                                       rtol=1e-5, atol=1e-7)

    def test_long_default(self, synth_ohlc, synth_atr_spread):
        self._run_parity(synth_ohlc, synth_atr_spread,
                         direction=1, horizon=20, stop_mult=1.5,
                         target_mult=2.0, min_hold_bars=3)

    def test_short_default(self, synth_ohlc, synth_atr_spread):
        self._run_parity(synth_ohlc, synth_atr_spread,
                         direction=-1, horizon=20, stop_mult=1.5,
                         target_mult=2.0, min_hold_bars=3)

    def test_long_tight_stops(self, synth_ohlc, synth_atr_spread):
        self._run_parity(synth_ohlc, synth_atr_spread,
                         direction=1, horizon=10, stop_mult=0.5,
                         target_mult=1.0, min_hold_bars=1)

    def test_short_wide_horizon(self, synth_ohlc, synth_atr_spread):
        self._run_parity(synth_ohlc, synth_atr_spread,
                         direction=-1, horizon=50, stop_mult=2.0,
                         target_mult=3.0, min_hold_bars=5)

    def test_min_hold_bars_boundary(self, synth_ohlc, synth_atr_spread):
        """Verify min_hold_bars correctly prevents early labels."""
        self._run_parity(synth_ohlc, synth_atr_spread,
                         direction=1, horizon=30, stop_mult=1.0,
                         target_mult=2.0, min_hold_bars=10)
