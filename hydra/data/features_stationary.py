"""Regime-invariant feature engineering — all features stationary, no absolute price levels.

PRINCIPLES:
1. Every feature is a ratio, percentage, or rolling statistic
2. No features anchored to training-period quantiles
3. ATR always normalized by close (ATR_pct)
4. All z-scores computed with rolling windows only
5. Drawdowns normalized by current price
6. Returns computed as log-returns or percentage changes

This module replaces regime-dependent features identified in the PhD diagnostic report.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm
from statsmodels.tsa.stattools import adfuller


def compute_log_returns(close: np.ndarray, periods: list[int]) -> dict[str, np.ndarray]:
    """Compute log returns over multiple periods."""
    features = {}
    for p in periods:
        ret = np.full(len(close), np.nan, dtype=np.float32)
        ret[p:] = np.log(close[p:] / close[:-p]).astype(np.float32)
        features[f"log_return_{p}"] = ret
    return features


def compute_rolling_zscore(close: np.ndarray, windows: list[int]) -> dict[str, np.ndarray]:
    """Rolling z-score using ONLY the last N bars (not training quantiles). Clipped to [-5, 5]."""
    features = {}
    s = pd.Series(close, dtype=np.float64)
    for w in windows:
        # Original: mean/std over close[i-w:i] (excludes current bar), applied at index i
        # pandas rolling(w) on shifted series gives same window
        rolled = s.shift(1).rolling(w, min_periods=w)
        mean = rolled.mean().values
        std = rolled.std(ddof=0).values
        z = np.where(std > 1e-10, (close - mean) / std, np.nan)
        features[f"rolling_zscore_{w}"] = np.clip(z, -5.0, 5.0).astype(np.float32)
    return features


def compute_atr_pct(high: np.ndarray, low: np.ndarray, close: np.ndarray, periods: list[int]) -> dict[str, np.ndarray]:
    """ATR normalized by close (percentage ATR)."""
    features = {}
    for period in periods:
        hl = high - low
        hc = np.abs(high - np.roll(close, 1))
        lc = np.abs(low - np.roll(close, 1))
        tr = np.maximum(np.maximum(hl, hc), lc)
        tr[0] = high[0] - low[0]

        atr = np.full(len(close), np.nan, dtype=np.float32)
        atr[period-1] = tr[:period].mean()
        for i in range(period, len(close)):
            atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period

        atr_pct = np.where(close > 1e-10, atr / close, 0.0).astype(np.float32)
        features[f"atr_pct_{period}"] = atr_pct
    return features


def compute_drawdown_pct(close: np.ndarray, windows: list[int]) -> dict[str, np.ndarray]:
    """Drawdown normalized by current price (NOT absolute drawdown)."""
    features = {}
    s = pd.Series(close, dtype=np.float64)
    for w in windows:
        # Original: peak over close[i-w:i+1] (w+1 bars including current)
        peak = s.rolling(w + 1, min_periods=w + 1).max().values
        dd_pct = np.where(peak > 1e-10, (close - peak) / peak, np.nan).astype(np.float32)
        features[f"drawdown_pct_{w}"] = dd_pct
    return features


def compute_realized_vol(close: np.ndarray, windows: list[int]) -> dict[str, np.ndarray]:
    """Rolling realized volatility (annualized)."""
    features = {}
    log_ret = np.full(len(close), np.nan, dtype=np.float64)
    log_ret[1:] = np.log(close[1:] / close[:-1])

    s = pd.Series(log_ret)
    for w in windows:
        # Original: std over log_ret[i-w+1:i+1] (w bars including current), ddof=0
        rvol = (s.rolling(w, min_periods=w).std(ddof=0) * np.sqrt(252)).values.astype(np.float32)
        features[f"realized_vol_{w}"] = rvol
    return features


def compute_rsi(close: np.ndarray, period: int = 14) -> np.ndarray:
    """RSI (already ratio-based, 0-100)."""
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)

    avg_gain = np.full(len(close), np.nan, dtype=np.float32)
    avg_loss = np.full(len(close), np.nan, dtype=np.float32)

    avg_gain[period] = gain[1:period+1].mean()
    avg_loss[period] = loss[1:period+1].mean()

    for i in range(period+1, len(close)):
        avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i]) / period
        avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i]) / period

    rs = np.where(avg_loss > 1e-10, avg_gain / avg_loss, 0.0)
    rsi = 100 - (100 / (1 + rs))
    return rsi.astype(np.float32)


def compute_volume_ratio(volume: np.ndarray, window: int = 20) -> np.ndarray:
    """Volume / rolling_mean_volume. Clipped to [0, 10]."""
    # Original: mean over volume[i-window:i] (excludes current), applied at index i
    s = pd.Series(volume, dtype=np.float64)
    vol_ma = s.shift(1).rolling(window, min_periods=window).mean().values

    ratio = np.where(vol_ma > 1e-10, volume / vol_ma, 1.0)
    ratio = np.clip(ratio, 0.0, 10.0).astype(np.float32)
    return ratio


def compute_macd_pct(close: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, np.ndarray]:
    """MACD normalized by close (percentage MACD)."""
    def ema(x, span):
        alpha = 2 / (span + 1)
        ema_vals = np.full(len(x), np.nan, dtype=np.float32)
        ema_vals[span-1] = x[:span].mean()
        for i in range(span, len(x)):
            ema_vals[i] = alpha * x[i] + (1 - alpha) * ema_vals[i-1]
        return ema_vals

    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd = ema_fast - ema_slow
    macd_pct = np.where(close > 1e-10, macd / close, 0.0).astype(np.float32)

    macd_signal = ema(macd, signal)
    macd_signal_pct = np.where(close > 1e-10, macd_signal / close, 0.0).astype(np.float32)

    macd_hist_pct = macd_pct - macd_signal_pct

    return {
        "macd_pct": macd_pct,
        "macd_signal_pct": macd_signal_pct,
        "macd_hist_pct": macd_hist_pct,
    }


def compute_bb_position(close: np.ndarray, window: int = 20, num_std: float = 2.0) -> np.ndarray:
    """Bollinger Band position: (close - bb_mid) / (bb_upper - bb_lower)."""
    # Original: mean/std over close[i-window:i] (excludes current), applied at index i
    s = pd.Series(close, dtype=np.float64)
    rolled = s.shift(1).rolling(window, min_periods=window)
    bb_mid = rolled.mean().values
    bb_std = rolled.std(ddof=0).values

    bb_upper = bb_mid + num_std * bb_std
    bb_lower = bb_mid - num_std * bb_std
    bb_width = bb_upper - bb_lower

    bb_position = np.where(bb_width > 1e-10, (close - bb_mid) / bb_width, 0.0).astype(np.float32)
    return bb_position


def compute_autocorr(close: np.ndarray, windows: list[int], lags: list[int]) -> dict[str, np.ndarray]:
    """Rolling autocorrelation of log returns."""
    features = {}
    log_ret = np.full(len(close), np.nan, dtype=np.float64)
    log_ret[1:] = np.log(close[1:] / close[:-1])

    s = pd.Series(log_ret)
    for w in windows:
        for lag in lags:
            # Original: corrcoef(log_ret[i-w:i], log_ret[i-w-lag:i-lag]) at index i
            # This is correlation between the window and its lagged copy
            s_lagged = s.shift(lag)
            corr = s.rolling(w, min_periods=w).corr(s_lagged).values.astype(np.float32)
            features[f"autocorr_{w}_lag{lag}"] = corr
    return features


def compute_hurst(close: np.ndarray, windows: list[int]) -> dict[str, np.ndarray]:
    """Rolling Hurst exponent (0.5=random walk, >0.5=trending, <0.5=mean-reverting)."""
    features = {}
    log_ret = np.log(close[1:] / close[:-1])

    for w in windows:
        hurst = np.full(len(close), np.nan, dtype=np.float32)
        # Original: window = log_ret[i-w:i-1] at index i (w-1 elements from offset i-w)
        # min length check: len(window) < 20 → skip
        if w - 1 < 20:
            features[f"hurst_{w}"] = hurst
            continue

        for i in range(w, len(close)):
            window = log_ret[i-w:i-1]

            mean_ret = window.mean()
            cumsum = (window - mean_ret).cumsum()
            R = cumsum.max() - cumsum.min()
            S = window.std()

            if S > 1e-10:
                rs = R / S
                if rs > 0:
                    h = np.log(rs) / np.log(len(window) / 2)
                    hurst[i] = np.clip(h, 0.0, 1.0)

        features[f"hurst_{w}"] = hurst
    return features


def compute_sharpe_rolling(close: np.ndarray, windows: list[int]) -> dict[str, np.ndarray]:
    """Rolling Sharpe ratio (annualized, clipped to [-10, 10])."""
    features = {}
    log_ret = np.full(len(close), np.nan, dtype=np.float64)
    log_ret[1:] = np.log(close[1:] / close[:-1])

    s = pd.Series(log_ret)
    for w in windows:
        # Original: mean/std over log_ret[i-w+1:i+1] (w bars including current), ddof=0
        rolled = s.rolling(w, min_periods=w)
        mean_ret = rolled.mean().values
        std_ret = rolled.std(ddof=0).values
        sharpe = np.where(std_ret > 1e-10, (mean_ret / std_ret) * np.sqrt(252), np.nan)
        features[f"sharpe_rolling_{w}"] = np.clip(sharpe, -10.0, 10.0).astype(np.float32)
    return features


def compute_regime_probs(close: np.ndarray, window: int = 50) -> dict[str, np.ndarray]:
    """Regime probabilities based on rolling volatility and trend."""
    log_ret = np.log(close[1:] / close[:-1])
    log_ret = np.concatenate([[0], log_ret])

    vol = np.full(len(close), np.nan, dtype=np.float32)
    trend = np.full(len(close), np.nan, dtype=np.float32)

    for i in range(window, len(close)):
        window_ret = log_ret[i-window+1:i+1]
        vol[i] = window_ret.std() * np.sqrt(252)
        trend[i] = (close[i] / close[i-window]) - 1.0

    # Normalize to [0,1] using ROLLING quantiles (point-in-time safe)
    # For vol: compute rolling 252-bar (1yr) quantiles
    vol_series = pd.Series(vol, dtype=np.float32)
    vol_q25 = vol_series.shift(1).rolling(252, min_periods=50).quantile(0.25).values
    vol_q75 = vol_series.shift(1).rolling(252, min_periods=50).quantile(0.75).values
    vol_range = vol_q75 - vol_q25
    vol_norm = np.where(vol_range > 1e-10, (vol - vol_q25) / (vol_range + 1e-10), 0.5).astype(np.float32)
    vol_norm = np.clip(vol_norm, 0.0, 1.0)  # clip to [0,1]

    # Trend already normalized correctly (no global stats)
    trend_norm = (trend + 1) / 2  # map [-1, 1] to [0, 1]

    # Regime heuristics
    crisis_prob = np.where(vol_norm > 0.75, vol_norm, 0.0).astype(np.float32)
    trend_up_prob = np.where((trend_norm > 0.6) & (vol_norm < 0.6), trend_norm, 0.0).astype(np.float32)
    trend_dn_prob = np.where((trend_norm < 0.4) & (vol_norm < 0.6), 1 - trend_norm, 0.0).astype(np.float32)
    ranging_prob = np.where((vol_norm < 0.4) & (np.abs(trend) < 0.1), 1 - vol_norm, 0.0).astype(np.float32)

    return {
        "regime_crisis_prob": crisis_prob,
        "regime_trend_up_prob": trend_up_prob,
        "regime_trend_dn_prob": trend_dn_prob,
        "regime_ranging_prob": ranging_prob,
    }


def build_stationary_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build regime-invariant feature matrix from OHLCV data.

    Args:
        df: DataFrame with columns [ts, open, high, low, close, volume]

    Returns:
        DataFrame with stationary features added
    """
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    volume = df["volume"].values if "volume" in df.columns else np.ones(len(close))

    features = {}

    # Log returns (5, 10, 20, 50, 100 periods)
    features.update(compute_log_returns(close, [1, 5, 10, 20, 50, 100]))

    # Rolling z-scores (10, 20, 50 periods)
    features.update(compute_rolling_zscore(close, [10, 20, 50]))

    # ATR percentage (14 only, others redundant per correlation audit)
    features.update(compute_atr_pct(high, low, close, [14]))

    # Drawdown percentage (20 only, reduce redundancy)
    features.update(compute_drawdown_pct(close, [20]))

    # Realized volatility (10, 20, 50 periods)
    features.update(compute_realized_vol(close, [10, 20, 50]))

    # RSI
    features["rsi_14"] = compute_rsi(close, 14)

    # Volume ratio
    features["volume_ratio_20"] = compute_volume_ratio(volume, 20)

    # MACD percentage
    features.update(compute_macd_pct(close, 12, 26, 9))

    # Bollinger Band position (skip, perfectly correlated with rolling_zscore_20)
    # features["bb_position_20"] = compute_bb_position(close, 20, 2.0)

    # Autocorrelation (10, 20, 50 periods; lags 1, 5, 10)
    features.update(compute_autocorr(close, [10, 20, 50], [1, 5, 10]))

    # Hurst exponent (50, 100 periods)
    features.update(compute_hurst(close, [50, 100]))

    # Rolling Sharpe (10, 20, 50 periods)
    features.update(compute_sharpe_rolling(close, [10, 20, 50]))

    # Regime probabilities
    features.update(compute_regime_probs(close, 50))

    # Add to dataframe
    for name, vals in features.items():
        df[name] = vals

    return df


def audit_stationarity(df: pd.DataFrame, feature_cols: list[str], max_p_value: float = 0.05) -> dict:
    """Run ADF test on all features, flag non-stationary ones.

    Args:
        df: DataFrame with features
        feature_cols: List of feature column names to test
        max_p_value: Maximum p-value to consider stationary

    Returns:
        dict with keys:
            - stationary: list of stationary feature names
            - non_stationary: list of (name, p_value) tuples
            - failed: list of feature names where ADF test failed
    """
    stationary = []
    non_stationary = []
    failed = []

    for col in feature_cols:
        vals = df[col].values
        valid = vals[np.isfinite(vals)]

        if len(valid) < 50:
            failed.append(col)
            continue

        try:
            result = adfuller(valid, maxlag=10, regression='c', autolag='AIC')
            p_value = result[1]

            if p_value <= max_p_value:
                stationary.append(col)
            else:
                non_stationary.append((col, p_value))
        except Exception:
            failed.append(col)

    return {
        "stationary": stationary,
        "non_stationary": non_stationary,
        "failed": failed,
    }


def compute_feature_correlations(df: pd.DataFrame, feature_cols: list[str], threshold: float = 0.95) -> list[tuple]:
    """Find highly correlated feature pairs.

    Args:
        df: DataFrame with features
        feature_cols: List of feature column names
        threshold: Correlation threshold to flag

    Returns:
        List of (feat1, feat2, correlation) tuples where |corr| > threshold
    """
    X = df[feature_cols].values

    # Replace NaN/Inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

    # Compute correlation matrix
    corr_matrix = np.corrcoef(X.T)

    high_corr = []
    n = len(feature_cols)
    for i in range(n):
        for j in range(i+1, n):
            corr = corr_matrix[i, j]
            if np.abs(corr) > threshold:
                high_corr.append((feature_cols[i], feature_cols[j], corr))

    return high_corr


def print_feature_summary(df: pd.DataFrame, feature_cols: list[str], split_idx: dict):
    """Print summary statistics for features across train/val/test splits.

    Args:
        df: DataFrame with features
        feature_cols: List of feature column names
        split_idx: dict with keys 'train', 'val', 'test' containing boolean masks
    """
    print("\n" + "=" * 80)
    print("FEATURE SUMMARY STATISTICS")
    print("=" * 80)

    for split_name in ["train", "val", "test"]:
        if split_name not in split_idx:
            continue

        mask = split_idx[split_name]
        X = df.loc[mask, feature_cols].values
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        print(f"\n{split_name.upper()} SPLIT:")
        print(f"  Shape: {X.shape}")
        print(f"  Mean (all features): {X.mean():.6f}")
        print(f"  Std (all features): {X.std():.6f}")
        print(f"  Min: {X.min():.6f}")
        print(f"  Max: {X.max():.6f}")
        print(f"  NaN count: {np.isnan(df.loc[mask, feature_cols].values).sum()}")
        print(f"  Inf count: {np.isinf(df.loc[mask, feature_cols].values).sum()}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Demo usage
    import duckdb
    from pathlib import Path

    db_path = Path.home() / "Dominion" / "data" / "dominion.duckdb"
    con = duckdb.connect(str(db_path), read_only=True)

    # Load OHLCV data
    df = con.execute(
        "SELECT timestamp as ts, open, high, low, close, volume FROM gold_master ORDER BY timestamp"
    ).df()
    con.close()

    print(f"Loaded {len(df)} bars from gold_master")

    # Build stationary features
    print("\nBuilding stationary features...")
    df = build_stationary_features(df)

    # Get feature columns (exclude OHLCV and timestamp)
    exclude = {"ts", "open", "high", "low", "close", "volume"}
    feature_cols = [c for c in df.columns if c not in exclude]

    print(f"\nGenerated {len(feature_cols)} stationary features")

    # Audit stationarity
    print("\nRunning ADF stationarity tests...")
    audit_results = audit_stationarity(df, feature_cols)

    print(f"\nStationary: {len(audit_results['stationary'])}")
    print(f"Non-stationary: {len(audit_results['non_stationary'])}")
    print(f"Failed: {len(audit_results['failed'])}")

    if audit_results['non_stationary']:
        print("\nNon-stationary features (p > 0.05):")
        for name, p_val in audit_results['non_stationary'][:10]:
            print(f"  {name}: p={p_val:.4f}")

    # Check correlations
    print("\nChecking feature correlations...")
    high_corr = compute_feature_correlations(df, feature_cols, threshold=0.95)

    print(f"\nHighly correlated pairs (|r| > 0.95): {len(high_corr)}")
    for feat1, feat2, corr in high_corr[:10]:
        print(f"  {feat1} <-> {feat2}: r={corr:.3f}")

    # Split and print summary
    n = len(df)
    train_end = n // 3
    val_end = (2 * n) // 3

    split_idx = {
        "train": np.arange(n) < train_end,
        "val": (np.arange(n) >= train_end) & (np.arange(n) < val_end),
        "test": np.arange(n) >= val_end,
    }

    print_feature_summary(df, feature_cols, split_idx)

    print("\n✓ Stationary feature engineering complete.")
