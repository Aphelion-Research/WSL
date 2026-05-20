"""Triple-barrier target labelling with Wilder ATR."""
from __future__ import annotations

import numpy as np

from hydra.config import TARGET


def wilder_atr(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    n: int = TARGET.atr_window,
) -> np.ndarray:
    pc = np.roll(close, 1)
    pc[0] = close[0]
    tr = np.maximum.reduce([high - low, np.abs(high - pc), np.abs(low - pc)])
    atr = np.full_like(tr, np.nan, dtype=np.float64)
    if len(tr) < n:
        return atr
    atr[n - 1] = tr[:n].mean()
    for i in range(n, len(tr)):
        atr[i] = (atr[i - 1] * (n - 1) + tr[i]) / n
    return atr


def triple_barrier_long(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    horizon: int = TARGET.horizon_bars,
    sl_mult: float = TARGET.stop_mult,
    tp_mult: float = TARGET.target_mult,
    min_atr_pct: float = TARGET.min_atr_pct,
) -> np.ndarray:
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    for t in range(n - horizon):
        if not np.isfinite(atr[t]):
            continue
        if close[t] == 0 or atr[t] / close[t] < min_atr_pct:
            continue
        sl = close[t] - sl_mult * atr[t]
        tp = close[t] + tp_mult * atr[t]
        for k in range(1, horizon + 1):
            if low[t + k] <= sl:
                y[t] = 0.0
                break
            if high[t + k] >= tp:
                y[t] = 1.0
                break
    return y


def triple_barrier_short(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    atr: np.ndarray,
    horizon: int = TARGET.horizon_bars,
    sl_mult: float = TARGET.stop_mult,
    tp_mult: float = TARGET.target_mult,
    min_atr_pct: float = TARGET.min_atr_pct,
) -> np.ndarray:
    n = len(close)
    y = np.full(n, np.nan, dtype=np.float32)
    for t in range(n - horizon):
        if not np.isfinite(atr[t]):
            continue
        if close[t] == 0 or atr[t] / close[t] < min_atr_pct:
            continue
        sl = close[t] + sl_mult * atr[t]
        tp = close[t] - tp_mult * atr[t]
        for k in range(1, horizon + 1):
            if high[t + k] >= sl:
                y[t] = 0.0
                break
            if low[t + k] <= tp:
                y[t] = 1.0
                break
    return y


def make_targets(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> np.ndarray:
    """Unified binary target: 1=long wins, 0=short wins, NaN=neither."""
    atr = wilder_atr(high, low, close)
    y_long = triple_barrier_long(high, low, close, atr)
    y_short = triple_barrier_short(high, low, close, atr)
    y = np.full(len(close), np.nan, dtype=np.float32)
    long_win = y_long == 1.0
    short_win = y_short == 1.0
    y[long_win & ~short_win] = 1.0
    y[short_win & ~long_win] = 0.0
    both = long_win & short_win
    y[both] = 1.0
    return y
