"""
Build institutional-grade XAU/USD dataset.
Inspired by hedge fund indicators: VWAP, volatility regime, order imbalance,
cross-asset leads, yield curves, positioning, and ATR-based risk.

Multi-timeframe: M5 base resampled to H1/H4/D1 with cross-asset daily merge.
~25-35 clean features, no redundant TA noise.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
OUTPUT = DATA_DIR / "institutional_xauusd.parquet"


def load_xau_m5():
    """Load XAU M5 base data."""
    df = pd.read_parquet(DATA_DIR / "mt5_history/XAUUSD_M5_dukascopy.parquet")
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time').sort_index()
    df = df[['open', 'high', 'low', 'close', 'tick_volume', 'spread']].copy()
    df = df[df['close'] > 0].dropna(subset=['close'])
    return df


def load_cross_asset():
    """Load cross-asset daily closes."""
    df = pd.read_parquet(DATA_DIR / "cross_asset/cross_asset_daily.parquet")
    df.index = pd.to_datetime(df.index)
    return df


def load_macro():
    """Load FRED macro data (yields, breakevens)."""
    macro_dir = DATA_DIR / "macro"
    series = {}
    for name in ['DGS2', 'DGS10', 'DGS5', 'DFII10', 'DFII5', 'T5YIE', 'T10YIE', 'DFF']:
        f = macro_dir / f"{name}.parquet"
        if f.exists():
            s = pd.read_parquet(f)
            if 'value' in s.columns:
                s = s.set_index('date')['value'] if 'date' in s.columns else s['value']
            elif len(s.columns) == 1:
                s = s.iloc[:, 0]
            else:
                s = s.iloc[:, -1]
            s.index = pd.to_datetime(s.index)
            series[name] = s
    combined = pd.DataFrame(series)
    combined = combined.ffill()
    return combined


def load_cot():
    """Load COT positioning data."""
    df = pd.read_parquet(DATA_DIR / "cot/cot_gold_weekly.parquet")
    df.index = pd.to_datetime(df.index)
    return df


def compute_vwap(df, window=48):
    """VWAP over N bars (typical price * volume cumsum / volume cumsum)."""
    tp = (df['high'] + df['low'] + df['close']) / 3
    vol = df['tick_volume'].replace(0, 1)
    cum_tp_vol = (tp * vol).rolling(window).sum()
    cum_vol = vol.rolling(window).sum()
    vwap = cum_tp_vol / cum_vol
    return (df['close'] - vwap) / vwap


def compute_atr(df, period=14):
    """Average True Range."""
    h = df['high']
    l = df['low']
    c = df['close'].shift(1)
    tr = pd.concat([h - l, (h - c).abs(), (l - c).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def compute_order_book_imbalance(df, window=12):
    """
    Proxy OBI from tick volume + price action.
    Up bars (close > open) = buy pressure, down bars = sell pressure.
    """
    buy_vol = df['tick_volume'].where(df['close'] > df['open'], 0)
    sell_vol = df['tick_volume'].where(df['close'] <= df['open'], 0)
    buy_sum = buy_vol.rolling(window).sum()
    sell_sum = sell_vol.rolling(window).sum()
    total = buy_sum + sell_sum
    obi = (buy_sum - sell_sum) / total.replace(0, np.nan)
    return obi


def compute_volatility_regime(df, short=12, long=288):
    """Vol regime: ratio of short-term to long-term ATR."""
    atr_short = compute_atr(df, short)
    atr_long = compute_atr(df, long)
    return atr_short / atr_long.replace(0, np.nan)


def compute_var_proxy(returns, window=252, confidence=0.05):
    """Historical VaR at 5% level over rolling window."""
    return returns.rolling(window).quantile(confidence)


def compute_session_vwap_deviation(df):
    """
    Intraday VWAP deviation — resets each London session.
    Approximation: rolling 288 bars (1 day) VWAP distance.
    """
    return compute_vwap(df, window=288)


def build_multi_timeframe_features(m5):
    """Build features at multiple timeframes from M5 base."""
    features = pd.DataFrame(index=m5.index)

    # === 1. VWAP FEATURES ===
    # Short VWAP (4hr = 48 bars)
    features['vwap_dev_4h'] = compute_vwap(m5, window=48)
    # Session VWAP (24hr = 288 bars)
    features['vwap_dev_session'] = compute_vwap(m5, window=288)

    # === 2. ORDER BOOK IMBALANCE PROXY ===
    features['obi_1h'] = compute_order_book_imbalance(m5, window=12)
    features['obi_4h'] = compute_order_book_imbalance(m5, window=48)
    features['obi_day'] = compute_order_book_imbalance(m5, window=288)

    # === 3. ATR AT MULTIPLE SCALES ===
    atr_1h = compute_atr(m5, 12)
    atr_4h = compute_atr(m5, 48)
    atr_day = compute_atr(m5, 288)
    # Normalize ATR to % of price
    features['atr_1h_pct'] = atr_1h / m5['close']
    features['atr_day_pct'] = atr_day / m5['close']

    # === 4. VOLATILITY REGIME ===
    features['vol_regime'] = compute_volatility_regime(m5, short=12, long=288)
    features['vol_regime_weekly'] = compute_volatility_regime(m5, short=48, long=288*5)

    # === 5. VaR PROXY ===
    returns = m5['close'].pct_change()
    features['var_5pct_daily'] = compute_var_proxy(returns, window=288, confidence=0.05)

    # === 6. 200-BAR SMA POSITION (multi-TF analog of 200-day SMA) ===
    sma_200_h1 = m5['close'].rolling(200 * 12).mean()  # 200 H1 bars in M5
    features['sma200_h1_pos'] = (m5['close'] - sma_200_h1) / sma_200_h1
    sma_50_d = m5['close'].rolling(50 * 288).mean()  # 50-day in M5
    features['sma50_day_pos'] = (m5['close'] - sma_50_d) / sma_50_d

    # === 7. SPREAD AS LIQUIDITY PROXY ===
    features['spread_zscore'] = (
        (m5['spread'] - m5['spread'].rolling(288).mean()) /
        m5['spread'].rolling(288).std().replace(0, np.nan)
    )

    # === 8. VOLUME PROFILE / DARK POOL PROXY ===
    # Unusual volume = potential block trades
    vol_ma = m5['tick_volume'].rolling(288).mean()
    vol_std = m5['tick_volume'].rolling(288).std()
    features['volume_zscore'] = (m5['tick_volume'] - vol_ma) / vol_std.replace(0, np.nan)

    # Large volume bars (>2 std) = institutional activity proxy
    features['big_volume_ratio'] = (
        m5['tick_volume'].where(m5['tick_volume'] > vol_ma + 2*vol_std, 0)
        .rolling(48).sum() / m5['tick_volume'].rolling(48).sum().replace(0, np.nan)
    )

    # === 9. TIME FEATURES (session effects) ===
    hour = m5.index.hour + m5.index.minute / 60
    features['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    features['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    features['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)

    # === 10. MOMENTUM (clean, not redundant) ===
    features['ret_1h'] = m5['close'].pct_change(12)
    features['ret_4h'] = m5['close'].pct_change(48)
    features['ret_1d'] = m5['close'].pct_change(288)
    features['ret_1w'] = m5['close'].pct_change(288 * 5)

    return features


def add_cross_asset_features(features, cross):
    """Add daily cross-asset signals merged onto M5 index."""
    # Create date column for merging
    feat_dates = features.index.normalize()

    # Key cross-asset relationships for gold
    gold_drivers = {}

    # DXY inverse relationship
    if 'dxy' in cross.columns:
        dxy = cross['dxy'].copy()
        gold_drivers['dxy_ret_1d'] = dxy.pct_change(1)
        gold_drivers['dxy_ret_5d'] = dxy.pct_change(5)
        gold_drivers['dxy_sma50_pos'] = (dxy - dxy.rolling(50).mean()) / dxy.rolling(50).mean()

    # Silver (gold/silver ratio)
    if 'silver' in cross.columns and 'gld' in cross.columns:
        gold_drivers['gold_silver_ratio'] = cross['gld'] / cross['silver'].replace(0, np.nan)
        gs = gold_drivers['gold_silver_ratio']
        gold_drivers['gold_silver_zscore'] = (gs - gs.rolling(60).mean()) / gs.rolling(60).std()

    # VIX (risk sentiment)
    if 'vix' in cross.columns:
        gold_drivers['vix_level'] = cross['vix']
        gold_drivers['vix_change_5d'] = cross['vix'].pct_change(5)

    # GVZ (gold-specific volatility)
    if 'gvz' in cross.columns:
        gold_drivers['gvz_level'] = cross['gvz']

    # SPX (risk-on/off)
    if 'spx' in cross.columns:
        gold_drivers['spx_ret_5d'] = cross['spx'].pct_change(5)

    # TLT (bonds — gold correlation)
    if 'tlt' in cross.columns:
        gold_drivers['tlt_ret_5d'] = cross['tlt'].pct_change(5)

    # Copper/Gold ratio (economic health proxy)
    if 'copper' in cross.columns and 'gld' in cross.columns:
        gold_drivers['copper_gold_ratio'] = cross['copper'] / cross['gld'].replace(0, np.nan)
        cg = gold_drivers['copper_gold_ratio']
        gold_drivers['copper_gold_zscore'] = (cg - cg.rolling(60).mean()) / cg.rolling(60).std()

    # WTI (inflation proxy)
    if 'wti' in cross.columns:
        gold_drivers['wti_ret_5d'] = cross['wti'].pct_change(5)

    # BTC (digital gold competitor)
    if 'btc' in cross.columns:
        gold_drivers['btc_ret_5d'] = cross['btc'].pct_change(5)

    # Build daily df and merge to M5
    daily_features = pd.DataFrame(gold_drivers, index=cross.index)
    daily_features.index = pd.to_datetime(daily_features.index)

    # Forward-fill to M5 (point-in-time safe: use yesterday's close)
    daily_features = daily_features.shift(1)  # lag 1 day for safety
    daily_features = daily_features.reindex(features.index, method='ffill')

    for col in daily_features.columns:
        features[col] = daily_features[col]

    return features


def add_yield_curve_features(features, macro):
    """Treasury yield spread features."""
    yield_features = {}

    if 'DGS10' in macro.columns and 'DGS2' in macro.columns:
        spread_10y2y = macro['DGS10'] - macro['DGS2']
        yield_features['yield_spread_10y2y'] = spread_10y2y
        yield_features['yield_spread_10y2y_change_5d'] = spread_10y2y.diff(5)

    if 'DFII10' in macro.columns:
        yield_features['real_yield_10y'] = macro['DFII10']
        yield_features['real_yield_10y_change_5d'] = macro['DFII10'].diff(5)

    if 'T10YIE' in macro.columns:
        yield_features['breakeven_10y'] = macro['T10YIE']
        yield_features['breakeven_10y_change_5d'] = macro['T10YIE'].diff(5)

    if 'DFF' in macro.columns:
        yield_features['fed_funds_rate'] = macro['DFF']

    daily_yields = pd.DataFrame(yield_features, index=macro.index)
    daily_yields = daily_yields.shift(1)  # point-in-time safe
    daily_yields = daily_yields.reindex(features.index, method='ffill')

    for col in daily_yields.columns:
        features[col] = daily_yields[col]

    return features


def add_cot_features(features, cot):
    """COT positioning features (weekly, lagged for point-in-time)."""
    cot_features = {}

    cot_features['cot_mm_net'] = cot['mm_long'] - cot['mm_short']
    net = cot_features['cot_mm_net']
    cot_features['cot_mm_net_percentile'] = net.rolling(52).rank(pct=True)
    cot_features['cot_mm_net_change'] = net.diff(1)
    cot_features['cot_oi'] = cot['open_interest']
    cot_features['cot_oi_change'] = cot['open_interest'].pct_change(1)

    weekly_cot = pd.DataFrame(cot_features, index=cot.index)
    # COT released Friday, available Monday — shift by 2 days extra for safety
    weekly_cot.index = weekly_cot.index + pd.Timedelta(days=3)
    weekly_cot = weekly_cot.reindex(features.index, method='ffill')

    for col in weekly_cot.columns:
        features[col] = weekly_cot[col]

    return features


def add_multi_symbol_mt5(features, m5):
    """
    Fetch correlated symbols from MT5 at H1 and compute lead/lag.
    Uses DXY proxy (EURUSD inverted), Silver, USDJPY.
    """
    # We'll compute correlations from M5 data if available
    # For now, use cross-asset daily which already covers these
    # This function is a placeholder for when we add H1 multi-symbol from MT5
    pass


def make_labels(m5, horizons={'4h': 48, '1d': 288, '3d': 288*3}):
    """Multi-horizon labels: direction after N bars."""
    labels = pd.DataFrame(index=m5.index)
    for name, bars in horizons.items():
        future_ret = m5['close'].shift(-bars) / m5['close'] - 1
        labels[f'label_{name}'] = (future_ret > 0).astype(int)
        labels[f'ret_{name}_fwd'] = future_ret
    return labels


def main():
    print("Loading data sources...")
    m5 = load_xau_m5()
    print(f"  XAU M5: {len(m5)} bars ({m5.index.min()} to {m5.index.max()})")

    cross = load_cross_asset()
    print(f"  Cross-asset: {len(cross)} days, {len(cross.columns)} symbols")

    macro = load_macro()
    print(f"  Macro: {len(macro)} days, {len(macro.columns)} series")

    cot = load_cot()
    print(f"  COT: {len(cot)} weeks")

    print("\nBuilding multi-timeframe features...")
    features = build_multi_timeframe_features(m5)
    print(f"  Base features: {len(features.columns)} columns")

    print("Adding cross-asset features...")
    features = add_cross_asset_features(features, cross)
    print(f"  After cross-asset: {len(features.columns)} columns")

    print("Adding yield curve features...")
    features = add_yield_curve_features(features, macro)
    print(f"  After yields: {len(features.columns)} columns")

    print("Adding COT positioning...")
    features = add_cot_features(features, cot)
    print(f"  After COT: {len(features.columns)} columns")

    print("\nMaking labels...")
    labels = make_labels(m5)

    # Combine
    dataset = pd.concat([features, labels], axis=1)

    # Drop warmup period (need 288*5 = 1440 bars for longest rolling)
    dataset = dataset.iloc[1440*2:]

    # Drop rows with NaN in features (but allow NaN in forward labels at end)
    feat_cols = [c for c in dataset.columns if not c.startswith('label_') and not c.startswith('ret_') or not c.endswith('_fwd')]
    feat_cols = [c for c in features.columns]
    dataset = dataset.dropna(subset=feat_cols)

    print(f"\n{'='*60}")
    print(f"FINAL DATASET: {len(dataset)} rows × {len(dataset.columns)} columns")
    print(f"Features: {len(feat_cols)}")
    print(f"Date range: {dataset.index.min()} to {dataset.index.max()}")
    print(f"\nFeature list:")
    for i, col in enumerate(feat_cols):
        print(f"  {i+1:2d}. {col}")
    print(f"\nLabels: {[c for c in dataset.columns if c.startswith('label_')]}")
    print(f"{'='*60}")

    dataset.to_parquet(OUTPUT)
    print(f"\nSaved to {OUTPUT}")

    # Quick sanity check
    print("\n--- Sanity Check ---")
    for label in [c for c in dataset.columns if c.startswith('label_')]:
        valid = dataset[label].dropna()
        print(f"  {label}: {len(valid)} samples, {valid.mean():.3f} positive rate")


if __name__ == "__main__":
    main()
