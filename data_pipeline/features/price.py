"""Price-derived features."""
import numpy as np
import pandas as pd
from typing import List
from statsmodels.tsa.stattools import adfuller

from data_pipeline.config import FEATURE_WINDOWS


def compute_returns(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute simple and log returns at multiple windows."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    price = df["close"]

    for w in windows:
        features[f"return_{w}"] = price.pct_change(w)
        features[f"log_return_{w}"] = np.log(price / price.shift(w))

    return features


def compute_rolling_stats(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute rolling mean, std, skew, kurtosis."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    price = df["close"]
    returns = price.pct_change()

    for w in windows:
        features[f"rolling_mean_{w}"] = price.rolling(w).mean()
        features[f"rolling_std_{w}"] = returns.rolling(w).std()
        features[f"rolling_skew_{w}"] = returns.rolling(w).skew()
        features[f"rolling_kurt_{w}"] = returns.rolling(w).kurt()

    return features


def compute_sharpe(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute rolling Sharpe ratio (annualized)."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    for w in windows:
        rolling_mean = returns.rolling(w).mean()
        rolling_std = returns.rolling(w).std()
        features[f"sharpe_{w}"] = (rolling_mean / rolling_std) * np.sqrt(252)

    return features


def compute_drawdown(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute rolling maximum drawdown."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    price = df["close"]

    for w in windows:
        rolling_max = price.rolling(w).max()
        features[f"drawdown_{w}"] = (price - rolling_max) / rolling_max

    return features


def compute_hurst(series: pd.Series, window: int = 100) -> float:
    """Compute Hurst exponent via R/S analysis."""
    if len(series) < window:
        return np.nan

    lags = range(2, min(20, len(series) // 2))
    rs_values = []

    for lag in lags:
        chunks = [series[i:i + lag] for i in range(0, len(series), lag) if len(series[i:i + lag]) == lag]
        if not chunks:
            continue

        rs_list = []
        for chunk in chunks:
            if len(chunk) < 2:
                continue
            mean = chunk.mean()
            y = (chunk - mean).cumsum()
            r = y.max() - y.min()
            s = chunk.std()
            if s > 0:
                rs_list.append(r / s)

        if rs_list:
            rs_values.append((lag, np.mean(rs_list)))

    if len(rs_values) < 2:
        return np.nan

    log_lags = np.log([x[0] for x in rs_values])
    log_rs = np.log([x[1] for x in rs_values])

    hurst = np.polyfit(log_lags, log_rs, 1)[0]
    return hurst


def compute_hurst_rolling(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute rolling Hurst exponent."""
    if windows is None:
        windows = [w for w in FEATURE_WINDOWS if w >= 50]  # Hurst needs longer windows

    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    for w in windows:
        hurst_values = []
        for i in range(len(returns)):
            if i < w:
                hurst_values.append(np.nan)
            else:
                window_data = returns.iloc[i - w:i]
                hurst_values.append(compute_hurst(window_data, w))
        features[f"hurst_{w}"] = hurst_values

    return features


def compute_autocorr(df: pd.DataFrame, lags: List[int] = [1, 5, 10], windows: List[int] = None) -> pd.DataFrame:
    """Compute rolling autocorrelation."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    for w in windows:
        for lag in lags:
            features[f"autocorr_{w}_lag{lag}"] = returns.rolling(w).apply(
                lambda x: x.autocorr(lag=lag) if len(x) > lag else np.nan
            )

    return features


def compute_zscore(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute z-score of price vs rolling mean."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=df.index)
    price = df["close"]

    for w in windows:
        rolling_mean = price.rolling(w).mean()
        rolling_std = price.rolling(w).std()
        features[f"zscore_{w}"] = (price - rolling_mean) / rolling_std

    return features


def compute_frac_diff(df: pd.DataFrame, d: float = 0.4) -> pd.DataFrame:
    """Compute fractionally differentiated price (FFD method)."""
    features = pd.DataFrame(index=df.index)
    price = df["close"].values

    # FFD weights
    n = len(price)
    weights = [1.0]
    for k in range(1, n):
        weights.append(-weights[-1] * (d - k + 1) / k)
        if abs(weights[-1]) < 1e-5:
            break

    weights = np.array(weights[::-1])

    # Apply FFD
    frac_diff = np.convolve(price, weights, mode='same')
    features["frac_diff_0.4"] = frac_diff

    return features


def compute_adf(df: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """Compute rolling ADF test statistic."""
    features = pd.DataFrame(index=df.index)
    price = df["close"]

    adf_stats = []
    for i in range(len(price)):
        if i < window:
            adf_stats.append(np.nan)
        else:
            window_data = price.iloc[i - window:i]
            try:
                result = adfuller(window_data, maxlag=1, regression='c', autolag=None)
                adf_stats.append(result[0])  # ADF statistic
            except:
                adf_stats.append(np.nan)

    features[f"adf_{window}"] = adf_stats
    return features


def compute_all_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all price-derived features (~80 features)."""
    all_features = [
        compute_returns(df),
        compute_rolling_stats(df),
        compute_sharpe(df),
        compute_drawdown(df),
        compute_hurst_rolling(df),
        compute_autocorr(df),
        compute_zscore(df),
        compute_frac_diff(df),
        compute_adf(df),
    ]

    return pd.concat(all_features, axis=1)
