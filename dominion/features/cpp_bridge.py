"""
Python bridge to C++ feature kernels.
Converts polars DataFrames to numpy arrays, calls C++, returns polars.
"""
from __future__ import annotations

import polars as pl
import numpy as np

from dominion.features import CPP_AVAILABLE

if CPP_AVAILABLE:
    import dominion.features.hydra_kernels as kernels


def ensure_cpp_available():
    """Raise error if C++ kernels not available."""
    if not CPP_AVAILABLE:
        raise RuntimeError(
            "C++ kernels not available. Build with: cd cpp && mkdir build && "
            "cd build && cmake .. && make && make install"
        )


def rolling_mean(df: pl.DataFrame, col: str, window: int, name: str | None = None) -> pl.Series:
    """Compute rolling mean using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.rolling_mean(data.tolist(), window)
    series_name = name if name else f"{col}_roll_mean_{window}"
    return pl.Series(series_name, result, dtype=pl.Float32)


def rolling_std(df: pl.DataFrame, col: str, window: int, name: str | None = None) -> pl.Series:
    """Compute rolling std using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.rolling_std(data.tolist(), window)
    series_name = name if name else f"{col}_roll_std_{window}"
    return pl.Series(series_name, result, dtype=pl.Float32)


def rolling_zscore(df: pl.DataFrame, col: str, window: int, name: str | None = None) -> pl.Series:
    """Compute rolling z-score using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.rolling_zscore(data.tolist(), window)
    series_name = name if name else f"{col}_roll_zscore_{window}"
    return pl.Series(series_name, result, dtype=pl.Float32)


def ema(df: pl.DataFrame, col: str, period: int, name: str | None = None) -> pl.Series:
    """Compute EMA using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.ema(data.tolist(), period)
    series_name = name if name else f"{col}_ema_{period}"
    return pl.Series(series_name, result, dtype=pl.Float32)


def rsi(df: pl.DataFrame, col: str, period: int, name: str | None = None) -> pl.Series:
    """Compute RSI using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.rsi(data.tolist(), period)
    series_name = name if name else f"{col}_rsi_{period}"
    return pl.Series(series_name, result, dtype=pl.Float32)


def atr(df: pl.DataFrame, period: int, name: str | None = None) -> pl.Series:
    """Compute ATR using C++ kernel."""
    ensure_cpp_available()
    high = df["high"].to_numpy().astype(np.float32)
    low = df["low"].to_numpy().astype(np.float32)
    close = df["close"].to_numpy().astype(np.float32)
    result = kernels.atr(high.tolist(), low.tolist(), close.tolist(), period)
    series_name = name if name else f"atr_{period}"
    return pl.Series(series_name, result, dtype=pl.Float32)


def bollinger_bands(df: pl.DataFrame, col: str, period: int,
                    num_std: float = 2.0) -> dict[str, pl.Series]:
    """Compute Bollinger Bands using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    bb = kernels.bollinger_bands(data.tolist(), period, num_std)
    return {
        f"{col}_bb_upper_{period}": pl.Series(bb.upper, dtype=pl.Float32),
        f"{col}_bb_middle_{period}": pl.Series(bb.middle, dtype=pl.Float32),
        f"{col}_bb_lower_{period}": pl.Series(bb.lower, dtype=pl.Float32),
        f"{col}_bb_width_{period}": pl.Series(bb.width, dtype=pl.Float32),
    }


def candle_features(df: pl.DataFrame) -> dict[str, pl.Series]:
    """Compute candle morphology features using C++ kernel."""
    ensure_cpp_available()
    open_ = df["open"].to_numpy().astype(np.float32)
    high = df["high"].to_numpy().astype(np.float32)
    low = df["low"].to_numpy().astype(np.float32)
    close = df["close"].to_numpy().astype(np.float32)

    return {
        "candle_body": pl.Series(kernels.candle_body(open_.tolist(), close.tolist()),
                                dtype=pl.Float32),
        "candle_upper_wick": pl.Series(
            kernels.candle_upper_wick(open_.tolist(), high.tolist(), close.tolist()),
            dtype=pl.Float32),
        "candle_lower_wick": pl.Series(
            kernels.candle_lower_wick(open_.tolist(), low.tolist(), close.tolist()),
            dtype=pl.Float32),
        "candle_range": pl.Series(kernels.candle_range(high.tolist(), low.tolist()),
                                 dtype=pl.Float32),
        "candle_body_ratio": pl.Series(
            kernels.candle_body_ratio(open_.tolist(), high.tolist(),
                                     low.tolist(), close.tolist()),
            dtype=pl.Float32),
        "candle_close_loc": pl.Series(
            kernels.candle_close_loc(high.tolist(), low.tolist(), close.tolist()),
            dtype=pl.Float32),
    }


def rolling_autocorr(df: pl.DataFrame, col: str, window: int, lag: int) -> pl.Series:
    """Compute rolling autocorrelation using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.rolling_autocorr(data.tolist(), window, lag)
    return pl.Series(f"{col}_acf_{window}_{lag}", result, dtype=pl.Float32)


def rolling_quantile(df: pl.DataFrame, col: str, window: int, q: float) -> pl.Series:
    """Compute rolling quantile using C++ kernel."""
    ensure_cpp_available()
    data = df[col].to_numpy().astype(np.float32)
    result = kernels.rolling_quantile(data.tolist(), window, q)
    return pl.Series(f"{col}_q{int(q*100)}_{window}", result, dtype=pl.Float32)
