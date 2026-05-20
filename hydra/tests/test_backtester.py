"""Tests for Python reference backtester."""
import numpy as np
import pytest

from hydra.backtest.engine_py import run_backtest, kelly_size
from hydra.data.targets import wilder_atr


def _make_uptrend(n=100, start=1800.0, step=2.0):
    close = np.linspace(start, start + step * n, n)
    high = close + 1.0
    low = close - 1.0
    return close, high, low


def test_kelly_size_basic():
    size = kelly_size(confidence=0.70, capital=100_000.0)
    assert 0 < size <= 25_000.0


def test_kelly_size_low_confidence():
    size = kelly_size(confidence=0.30, capital=100_000.0)
    assert size == 0.0


def test_all_longs_profitable_in_uptrend():
    n = 200
    close, high, low = _make_uptrend(n, start=1800.0, step=5.0)
    atr = wilder_atr(high, low, close)
    signals = np.ones(n)
    signals[:20] = 0
    confidences = np.full(n, 0.70)

    trades, equity = run_backtest(close, high, low, atr, signals, confidences)
    assert len(trades) > 0
    profitable = sum(1 for t in trades if t.pnl > 0)
    assert profitable / len(trades) > 0.5


def test_no_signal_no_trades():
    n = 100
    close = np.full(n, 1800.0)
    high = close + 1.0
    low = close - 1.0
    atr = wilder_atr(high, low, close)
    signals = np.zeros(n)
    confidences = np.zeros(n)

    trades, equity = run_backtest(close, high, low, atr, signals, confidences)
    assert len(trades) == 0
    assert equity[-1] == 100_000.0


def test_stop_fill_at_stop_price():
    n = 50
    close = np.full(n, 1800.0)
    high = np.full(n, 1801.0)
    low = np.full(n, 1799.0)
    atr = np.full(n, 5.0)
    signals = np.zeros(n)
    confidences = np.full(n, 0.70)

    signals[5] = 1
    for i in range(6, 50):
        low[i] = 1780.0

    trades, equity = run_backtest(close, high, low, atr, signals, confidences)
    assert len(trades) >= 1
    t = trades[0]
    assert t.direction == 1
    expected_stop = t.entry_px - 1.0 * 5.0
    assert abs(t.exit_px - expected_stop) < 0.01


def test_look_ahead_shifted_signal():
    """Perfect-foresight signals should beat time-shifted signals."""
    n = 300
    rng = np.random.RandomState(42)
    steps = rng.choice([-3.0, 3.0], size=n)
    close = 1800.0 + np.cumsum(steps)
    high = close + 2.0
    low = close - 2.0
    atr = wilder_atr(high, low, close)

    oracle_signals = np.zeros(n)
    for i in range(n - 25):
        if np.isfinite(atr[i]) and atr[i] > 0:
            oracle_signals[i] = 1.0 if steps[i + 1] > 0 else -1.0
    confidences = np.full(n, 0.65)

    trades_correct, eq_correct = run_backtest(
        close, high, low, atr, oracle_signals, confidences)

    random_signals = rng.choice([-1.0, 0.0, 1.0], size=n)
    trades_random, eq_random = run_backtest(
        close, high, low, atr, random_signals, confidences)

    profit_correct = eq_correct[-1] - eq_correct[0]
    profit_random = eq_random[-1] - eq_random[0]
    assert profit_correct > profit_random
