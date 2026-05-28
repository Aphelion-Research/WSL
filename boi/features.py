"""Multi-timeframe feature builder for BOI M15."""
import pandas as pd
import numpy as np
from typing import Dict, Optional


def build_m15_features(m15: pd.DataFrame) -> pd.DataFrame:
    """Build M15 bar features.

    Args:
        m15: M15 OHLCV DataFrame with DatetimeIndex

    Returns:
        DataFrame with M15 features (point-in-time safe)
    """
    close = m15['close']
    high = m15['high']
    low = m15['low']
    open_ = m15['open']
    volume = m15.get('tick_volume', m15.get('volume', pd.Series(1, index=m15.index)))

    f = pd.DataFrame(index=m15.index)

    # Returns over multiple horizons
    for bars in [1, 2, 4, 8, 16]:
        f[f'ret_{bars}b'] = close.pct_change(bars)

    # ATR
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    f['atr_14'] = tr.rolling(14).mean()
    f['atr_pct'] = f['atr_14'] / close

    # Range/body/wick ratios
    body = (close - open_).abs()
    range_ = high - low
    f['body_pct'] = body / range_.replace(0, np.nan)

    upper_wick = high - pd.concat([open_, close], axis=1).max(axis=1)
    lower_wick = pd.concat([open_, close], axis=1).min(axis=1) - low
    f['upper_wick_pct'] = upper_wick / range_.replace(0, np.nan)
    f['lower_wick_pct'] = lower_wick / range_.replace(0, np.nan)

    # Close position in range
    f['close_pos_range'] = (close - low) / range_.replace(0, np.nan)

    # Volatility percentile
    f['vol_pct_96b'] = close.rolling(96).std().rank(pct=True)

    # Rolling high/low distance
    for bars in [16, 48, 96]:
        rh = high.rolling(bars).max()
        rl = low.rolling(bars).min()
        f[f'dist_high_{bars}b'] = (rh - close) / close
        f[f'dist_low_{bars}b'] = (close - rl) / close

    # Compression/expansion
    for bars in [8, 16]:
        f[f'atr_ratio_{bars}b'] = f['atr_14'] / f['atr_14'].shift(bars).replace(0, np.nan)

    return f


def aggregate_m5_to_m15(m5: pd.DataFrame, m15_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Aggregate M5 bars into M15 features (point-in-time safe).

    For each M15 bar, use the 3 preceding M5 bars (not the current M15 bar's M5s).

    Args:
        m5: M5 OHLCV DataFrame
        m15_index: M15 bar timestamps

    Returns:
        DataFrame with M5-derived features aligned to M15 index
    """
    m5 = m5.copy()
    m5['ret'] = m5['close'].pct_change()

    f = pd.DataFrame(index=m15_index)

    # For each M15 bar, get last 3 M5 returns BEFORE that M15 bar
    # Lag by 1 M5 bar to avoid lookahead
    m5_lagged = m5.shift(1)

    for i, ts in enumerate(m15_index):
        # Get 3 M5 bars before this M15 bar
        mask = (m5_lagged.index < ts) & (m5_lagged.index >= ts - pd.Timedelta(minutes=15))
        m5_window = m5_lagged[mask].tail(3)

        if len(m5_window) >= 2:
            # Last 3 M5 returns
            rets = m5_window['ret'].values
            if len(rets) >= 1:
                f.loc[ts, 'm5_ret_last'] = rets[-1]
            if len(rets) >= 2:
                f.loc[ts, 'm5_ret_2nd'] = rets[-2]
            if len(rets) >= 3:
                f.loc[ts, 'm5_ret_3rd'] = rets[-3]

            # M5 realized volatility
            f.loc[ts, 'm5_rvol'] = m5_window['ret'].std()

            # M5 range expansion
            ranges = m5_window['high'] - m5_window['low']
            f.loc[ts, 'm5_range_exp'] = ranges.iloc[-1] / ranges.mean() if ranges.mean() > 0 else 1.0

            # M5 directional consensus
            f.loc[ts, 'm5_consensus'] = (m5_window['ret'] > 0).sum() / len(m5_window)

            # M5 wick rejection proxy
            body = (m5_window['close'] - m5_window['open']).abs()
            range_ = m5_window['high'] - m5_window['low']
            f.loc[ts, 'm5_wick_ratio'] = (1 - body / range_.replace(0, np.nan)).mean()

    return f


def build_htf_features(
    m15: pd.DataFrame,
    h1: Optional[pd.DataFrame] = None,
    h4: Optional[pd.DataFrame] = None,
    d1: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build higher timeframe features (point-in-time safe).

    Uses backward fill (as-of join) to align HTF to M15.

    Args:
        m15: M15 bars (for index)
        h1: H1 bars (optional)
        h4: H4 bars (optional)
        d1: D1 bars (optional)

    Returns:
        DataFrame with HTF features aligned to M15 index
    """
    f = pd.DataFrame(index=m15.index)

    # H1 features
    if h1 is not None:
        h1 = h1.copy()
        h1['sma_20'] = h1['close'].rolling(20).mean()
        h1['sma_50'] = h1['close'].rolling(50).mean()
        h1['trend'] = (h1['sma_20'] > h1['sma_50']).astype(int)
        h1['sma_dist'] = (h1['close'] - h1['sma_20']) / h1['close']

        # Range position
        rh = h1['high'].rolling(24).max()
        rl = h1['low'].rolling(24).min()
        h1['range_pos'] = (h1['close'] - rl) / (rh - rl).replace(0, np.nan)

        # Volatility regime
        h1['vol'] = h1['close'].rolling(24).std()
        h1['vol_regime'] = (h1['vol'] > h1['vol'].rolling(100).quantile(0.7)).astype(int)

        # As-of join (backward fill)
        for col in ['trend', 'sma_dist', 'range_pos', 'vol_regime']:
            f[f'h1_{col}'] = h1[col].reindex(f.index, method='ffill')

    # H4 features
    if h4 is not None:
        h4 = h4.copy()
        h4['sma_20'] = h4['close'].rolling(20).mean()
        h4['trend'] = (h4['close'] > h4['sma_20']).astype(int)

        # Compression/expansion
        atr = (h4['high'] - h4['low']).rolling(14).mean()
        h4['compression'] = (atr < atr.rolling(50).quantile(0.3)).astype(int)

        for col in ['trend', 'compression']:
            f[f'h4_{col}'] = h4[col].reindex(f.index, method='ffill')

    # D1 features
    if d1 is not None:
        d1 = d1.copy()
        d1['sma_50'] = d1['close'].rolling(50).mean()
        d1['sma_100'] = d1['close'].rolling(100).mean()
        d1['trend'] = ((d1['close'] > d1['sma_50']) & (d1['sma_50'] > d1['sma_100'])).astype(int)

        for col in ['trend']:
            f[f'd1_{col}'] = d1[col].reindex(f.index, method='ffill')

    return f


def build_session_features(m15: pd.DataFrame) -> pd.DataFrame:
    """Build session/time features.

    Args:
        m15: M15 DataFrame with DatetimeIndex

    Returns:
        DataFrame with session features
    """
    f = pd.DataFrame(index=m15.index)

    hour = m15.index.hour

    # Session flags (UTC times, adjust if data is different timezone)
    f['asia'] = ((hour >= 0) & (hour < 8)).astype(int)
    f['london'] = ((hour >= 8) & (hour < 16)).astype(int)
    f['ny'] = ((hour >= 13) & (hour < 21)).astype(int)
    f['late'] = ((hour >= 21) | (hour < 0)).astype(int)

    # Overlap
    f['london_ny_overlap'] = ((hour >= 13) & (hour < 16)).astype(int)

    # Cyclical encoding
    f['hour_sin'] = np.sin(2 * np.pi * hour / 24)
    f['hour_cos'] = np.cos(2 * np.pi * hour / 24)
    f['dow_sin'] = np.sin(2 * np.pi * m15.index.dayofweek / 7)
    f['dow_cos'] = np.cos(2 * np.pi * m15.index.dayofweek / 7)

    return f


def build_all_features(
    m15: pd.DataFrame,
    m5: Optional[pd.DataFrame] = None,
    h1: Optional[pd.DataFrame] = None,
    h4: Optional[pd.DataFrame] = None,
    d1: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Build all BOI features (point-in-time safe).

    Args:
        m15: M15 OHLCV DataFrame
        m5: M5 OHLCV DataFrame (optional)
        h1: H1 OHLCV DataFrame (optional)
        h4: H4 OHLCV DataFrame (optional)
        d1: D1 OHLCV DataFrame (optional)

    Returns:
        Combined feature DataFrame
    """
    features = [
        build_m15_features(m15),
        build_session_features(m15),
    ]

    if m5 is not None:
        features.append(aggregate_m5_to_m15(m5, m15.index))

    if any(x is not None for x in [h1, h4, d1]):
        features.append(build_htf_features(m15, h1, h4, d1))

    # Combine
    result = pd.concat(features, axis=1)

    return result
