"""Microstructure features: spreads, illiquidity, VPIN."""
import numpy as np
import pandas as pd
from typing import List

from data_pipeline.config import FEATURE_WINDOWS


def compute_roll_spread(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute Roll implicit spread: 2 * sqrt(max(-cov(ΔP_t, ΔP_{t-1}), 0))."""
    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    # Rolling covariance of returns with lagged returns
    cov_values = []
    for i in range(len(returns)):
        if i < window + 1:
            cov_values.append(np.nan)
        else:
            window_returns = returns.iloc[i - window:i]
            lagged = window_returns.shift(1)
            cov = window_returns.cov(lagged)
            roll = 2 * np.sqrt(max(-cov, 0))
            cov_values.append(roll)

    features[f"roll_spread_{window}"] = cov_values
    return features


def compute_corwin_schultz(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """Compute Corwin-Schultz spread from high/low ratio."""
    features = pd.DataFrame(index=df.index)

    # Compute beta (high/low ratio)
    hl_ratio = np.log(df["high"] / df["low"]) ** 2

    # Rolling average
    beta = hl_ratio.rolling(window).mean()

    # Compute spread
    spread = 2 * (np.exp(0.5 * beta) - 1) / (1 + np.exp(0.5 * beta))

    features[f"corwin_schultz_{window}"] = spread
    return features


def compute_amihud(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute Amihud illiquidity: |return| / volume."""
    if windows is None:
        windows = [w for w in FEATURE_WINDOWS if w <= 50]

    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change().abs()
    volume = df["volume"]

    # Illiquidity = |return| / volume
    illiq = returns / (volume + 1e-10)  # avoid division by zero

    for w in windows:
        features[f"amihud_{w}"] = illiq.rolling(w).mean()

    return features


def compute_kyle_lambda(df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
    """Compute Kyle's lambda: price impact per unit order flow.

    Estimated as regression slope of |return| on volume.
    """
    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change().abs()
    volume = df["volume"]

    lambda_values = []
    for i in range(len(returns)):
        if i < window:
            lambda_values.append(np.nan)
        else:
            ret_window = returns.iloc[i - window:i].values
            vol_window = volume.iloc[i - window:i].values

            # Simple linear regression
            if np.std(vol_window) > 0:
                lambda_val = np.cov(ret_window, vol_window)[0, 1] / np.var(vol_window)
            else:
                lambda_val = np.nan

            lambda_values.append(lambda_val)

    features[f"kyle_lambda_{window}"] = lambda_values
    return features


def compute_vpin(df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
    """Compute VPIN: volume-synchronized probability of informed trading.

    Classify each bar as buy/sell volume using tick rule.
    """
    features = pd.DataFrame(index=df.index)

    # Tick rule: if close > open -> buy, else sell
    buy_volume = np.where(df["close"] > df["open"], df["volume"], 0)
    sell_volume = np.where(df["close"] <= df["open"], df["volume"], 0)

    # VPIN = |buy - sell| / total
    total_volume = df["volume"]
    vpin = np.abs(buy_volume - sell_volume) / (total_volume + 1e-10)

    # Rolling average
    features[f"vpin_{window}"] = pd.Series(vpin, index=df.index).rolling(window).mean()

    return features


def compute_realized_variance(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute realized variance at multiple timescales."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    for w in windows:
        features[f"realized_var_{w}"] = returns.rolling(w).apply(lambda x: (x ** 2).sum())

    return features


def compute_bipower_variation(df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
    """Compute bipower variation (jump-robust volatility measure)."""
    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    # Bipower variation = sum(|r_t| * |r_{t-1}|)
    abs_returns = returns.abs()
    lagged_abs = abs_returns.shift(1)
    bpv = (abs_returns * lagged_abs).rolling(window).sum() * (np.pi / 2)

    features[f"bipower_var_{window}"] = bpv
    return features


def compute_jump_component(df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
    """Compute jump component: realized variance - bipower variation."""
    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    rv = returns.rolling(window).apply(lambda x: (x ** 2).sum())

    abs_returns = returns.abs()
    lagged_abs = abs_returns.shift(1)
    bpv = (abs_returns * lagged_abs).rolling(window).sum() * (np.pi / 2)

    features[f"jump_{window}"] = rv - bpv
    return features


def compute_vol_of_vol(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute volatility of volatility."""
    if windows is None:
        windows = [w for w in FEATURE_WINDOWS if w >= 20]

    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    for w in windows:
        rolling_vol = returns.rolling(w // 2).std()
        features[f"vol_of_vol_{w}"] = rolling_vol.rolling(w // 2).std()

    return features


def compute_all_microstructure_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all microstructure features (~60 features)."""
    all_features = [
        compute_roll_spread(df),
        compute_corwin_schultz(df),
        compute_amihud(df),
        compute_kyle_lambda(df),
        compute_vpin(df),
        compute_realized_variance(df),
        compute_bipower_variation(df),
        compute_jump_component(df),
        compute_vol_of_vol(df),
    ]

    return pd.concat(all_features, axis=1)
