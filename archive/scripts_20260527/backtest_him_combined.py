"""
Him V2 Combined Multi-Timeframe Backtest
=========================================
Deploy M5 + M15 + H1 models on SINGLE account.
OOS: 2025-01-01 to 2026-05-20 (pure out-of-sample)
Output: 4 results (M5 solo, M15 solo, H1 solo, COMBINED)
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
import warnings
from pathlib import Path
from datetime import datetime
from sklearn.metrics import roc_auc_score

warnings.filterwarnings('ignore')

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_DIR = Path("models/Him")
OUTPUT_DIR = Path("output_him_v2")
OUTPUT_DIR.mkdir(exist_ok=True)

EMA_PERIODS = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]


# ============================================================
# FEATURE FUNCTIONS (same as training)
# ============================================================

def compute_10ema_ensemble(close):
    f = pd.DataFrame(index=close.index)
    emas = {}
    for p in EMA_PERIODS:
        ema = close.ewm(span=p, adjust=False).mean()
        emas[p] = ema

    for p in [9, 21, 50, 200]:
        f[f'price_above_ema{p}'] = (close > emas[p]).astype(float)

    ordered_periods = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]
    bullish_count = np.zeros(len(close))
    for i in range(len(ordered_periods) - 1):
        bullish_count += (emas[ordered_periods[i]].values > emas[ordered_periods[i + 1]].values).astype(float)
    f['ema_bullish_count'] = bullish_count / (len(ordered_periods) - 1)

    f['ema_spread'] = (emas[9] - emas[1000]) / close

    ema_arr = np.column_stack([emas[p].values for p in EMA_PERIODS])
    close_arr = close.values.reshape(-1, 1)
    distances = np.abs(ema_arr - close_arr) / close_arr
    f['dist_to_nearest_ema'] = np.nanmin(distances, axis=1)

    for p in EMA_PERIODS:
        f[f'ema_{p}_pos'] = (close - emas[p]) / close

    return f


def compute_vwap_bands(close, high, low, volume, period=72):
    f = pd.DataFrame(index=close.index)
    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)
    vwap = (tp * vol).rolling(period).sum() / vol.rolling(period).sum()
    f['vwap_dev'] = close - vwap
    f['vwap_dev_pct'] = f['vwap_dev'] / vwap
    dev_std = f['vwap_dev'].rolling(period).std()
    upper = vwap + dev_std
    lower = vwap - dev_std
    band_width = (upper - lower).replace(0, np.nan)
    f['price_vs_vwap_band'] = ((close - lower) / band_width).clip(0, 1)
    f['vwap_slope'] = vwap.diff(5) / vwap
    return f


def build_m5_features(m5):
    close = m5['close']
    high = m5['high']
    low = m5['low']
    volume = m5['tick_volume']

    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    f_spec = pd.DataFrame(index=m5.index)
    for bars in [4, 12, 24, 48, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    for n in [12, 24, 48]:
        rolling_high = high.rolling(n).max()
        rolling_low = low.rolling(n).min()
        f_spec[f'pullback_high_{n}'] = (rolling_high - close) / close
        f_spec[f'pullback_low_{n}'] = (close - rolling_low) / close

    rh_48 = close.rolling(48).max()
    rl_48 = close.rolling(48).min()
    rng_48 = (rh_48 - rl_48).replace(0, np.nan)
    f_spec['range_pos_4h'] = (close - rl_48) / rng_48

    f_spec['vol_ratio'] = volume / volume.rolling(48).mean().replace(0, np.nan)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_24 = tr.rolling(24).mean()
    f_spec['atr_2h_pct'] = atr_24 / close
    f_spec['vol_ratio_short_long'] = tr.rolling(12).mean() / atr_24.replace(0, np.nan)

    hour = m5.index.hour + m5.index.minute / 60
    f_spec['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)

    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)
    return features


def build_m15_features(m15):
    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    f_spec = pd.DataFrame(index=m15.index)
    for bars in [16, 32, 64, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_96 = tr.rolling(96).mean().replace(0, np.nan)

    for period in [16, 32, 64]:
        rh = close.rolling(period).max()
        f_spec[f'pullback_high_{period}'] = (rh - close) / atr_96

    rolling_high_96 = close.rolling(96).max()
    rolling_low_96 = close.rolling(96).min()
    rng_96 = (rolling_high_96 - rolling_low_96).replace(0, np.nan)
    f_spec['range_pos_96bar'] = (close - rolling_low_96) / rng_96

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f_spec['rsi_14'] = 100 - 100 / (1 + gain / loss_val)

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f_spec['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    hour = m15.index.hour + m15.index.minute / 60
    f_spec['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * m15.index.dayofweek / 5)

    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)
    return features


def build_h1_features(h1):
    close = h1['close']
    high = h1['high']
    low = h1['low']
    volume = h1['tick_volume']

    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    f_spec = pd.DataFrame(index=h1.index)
    for bars in [1, 2, 4, 8, 12, 24, 48, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr_6 = tr.rolling(6).mean().replace(0, np.nan)
    atr_24 = tr.rolling(24).mean().replace(0, np.nan)
    atr_96 = tr.rolling(96).mean().replace(0, np.nan)
    f_spec['atr_6h_pct'] = atr_6 / close
    f_spec['atr_24h_pct'] = atr_24 / close
    f_spec['atr_96h_pct'] = atr_96 / close
    f_spec['vol_ratio_short_long'] = atr_6 / atr_24

    for period, suffix in [(12, '12h'), (24, '24h'), (48, '48h'), (96, '96h')]:
        rh = close.rolling(period).max()
        rl = close.rolling(period).min()
        rng = (rh - rl).replace(0, np.nan)
        f_spec[f'range_pos_{suffix}'] = (close - rl) / rng

    for period, suffix in [(12, '12h'), (24, '24h'), (48, '48h')]:
        rh = close.rolling(period).max()
        rl = close.rolling(period).min()
        f_spec[f'pullback_high_{suffix}'] = (rh - close) / atr_24
        f_spec[f'pullback_low_{suffix}'] = (close - rl) / atr_24

    f_spec['vol_ratio'] = volume / volume.rolling(24).mean().replace(0, np.nan)
    f_spec['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    f_spec['cos_hour'] = np.cos(2 * np.pi * h1.index.hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * h1.index.hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * h1.index.dayofweek / 5)

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f_spec['rsi_14'] = 100 - 100 / (1 + gain / loss_val)

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f_spec['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    f_spec['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f_spec['consec_down'] = close.diff().lt(0).rolling(8).sum()

    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)
    return features


# ============================================================
# SIGNAL GENERATION
# ============================================================

def generate_signals(model_path, features_df, feature_cols, threshold=0.60):
    """Load model, predict, generate long/short signals."""
    model = xgb.Booster()
    model.load_model(str(model_path))

    valid = features_df[feature_cols].dropna()
    dmat = xgb.DMatrix(valid.values, feature_names=feature_cols)
    proba = model.predict(dmat)

    signals = pd.Series(0, index=valid.index)
    signals[proba > threshold] = 1       # LONG
    signals[proba < (1 - threshold)] = -1  # SHORT

    proba_series = pd.Series(proba, index=valid.index)
    return signals, proba_series


# ============================================================
# BACKTEST ENGINE (unified for all timeframes)
# ============================================================

def run_backtest(signals_df, m5_data, config):
    """
    Run propfirm backtest on M5 bars using signals from any timeframe.
    signals_df: DataFrame with columns ['signal', 'proba', 'timeframe', 'holding_bars_m5']
    Each row is a potential entry point (on M5 timeline).
    """
    risk_pct = config.get('risk_per_trade', 0.01)
    stop_mult = config.get('stop_atr_mult', 1.5)
    tp_mult = config.get('tp_atr_mult', 3.0)
    leverage = 50
    initial_capital = 10000.0
    daily_loss_limit = 0.02
    total_loss_breach = 9000.0

    equity = initial_capital
    peak_equity = initial_capital
    daily_start_equity = initial_capital
    current_date = None
    daily_pnl = 0.0

    close = m5_data['close'].values
    high_arr = m5_data['high'].values
    low_arr = m5_data['low'].values
    dates = m5_data.index

    # ATR on M5 (12-bar = 1h)
    tr = np.maximum(high_arr - low_arr, np.maximum(
        np.abs(high_arr - np.roll(close, 1)),
        np.abs(low_arr - np.roll(close, 1))
    ))
    tr[0] = high_arr[0] - low_arr[0]
    atr = pd.Series(tr, index=dates).rolling(12).mean().values

    trades = []
    breached = False
    breach_reason = None

    # Build position-blocked periods (no overlapping trades)
    blocked_until = pd.Timestamp.min

    for idx, row in signals_df.iterrows():
        if breached:
            break

        # Skip if still in a trade
        if idx <= blocked_until:
            continue

        signal = int(row['signal'])
        if signal == 0:
            continue

        # Find this timestamp in M5 index
        m5_idx = dates.searchsorted(idx)
        if m5_idx >= len(close) - 1:
            continue

        dt = dates[m5_idx]
        holding_bars = int(row['holding_bars_m5'])

        # Equity checks
        if equity <= total_loss_breach:
            breached = True
            breach_reason = f"Total loss: ${equity:.0f}"
            break

        if current_date is None or dt.date() != current_date:
            current_date = dt.date()
            daily_start_equity = equity
            daily_pnl = 0.0

        daily_limit = daily_start_equity * daily_loss_limit
        if daily_pnl <= -daily_limit:
            continue

        if np.isnan(atr[m5_idx]) or atr[m5_idx] <= 0:
            continue

        entry_price = close[m5_idx]
        stop_distance = atr[m5_idx] * stop_mult
        tp_distance = atr[m5_idx] * tp_mult

        risk_amount = equity * risk_pct
        oz_per_lot = 100
        lots = risk_amount / (stop_distance * oz_per_lot)
        max_lots = (equity * leverage) / (entry_price * oz_per_lot)
        lots = min(lots, max_lots)

        if lots <= 0:
            continue

        if signal == 1:
            stop_price = entry_price - stop_distance
            tp_price = entry_price + tp_distance
        else:
            stop_price = entry_price + stop_distance
            tp_price = entry_price - tp_distance

        # Simulate trade on M5 bars
        exit_price = None
        exit_reason = None
        exit_bar = m5_idx

        for j in range(m5_idx + 1, min(m5_idx + holding_bars + 1, len(close))):
            if signal == 1:
                if low_arr[j] <= stop_price:
                    exit_price = stop_price
                    exit_reason = 'stop'
                    exit_bar = j
                    break
                if high_arr[j] >= tp_price:
                    exit_price = tp_price
                    exit_reason = 'tp'
                    exit_bar = j
                    break
            else:
                if high_arr[j] >= stop_price:
                    exit_price = stop_price
                    exit_reason = 'stop'
                    exit_bar = j
                    break
                if low_arr[j] <= tp_price:
                    exit_price = tp_price
                    exit_reason = 'tp'
                    exit_bar = j
                    break

        if exit_price is None:
            exit_bar = min(m5_idx + holding_bars, len(close) - 1)
            exit_price = close[exit_bar]
            exit_reason = 'timeout'

        if signal == 1:
            trade_pnl = (exit_price - entry_price) * lots * oz_per_lot
        else:
            trade_pnl = (entry_price - exit_price) * lots * oz_per_lot

        equity += trade_pnl
        daily_pnl += trade_pnl
        peak_equity = max(peak_equity, equity)

        trades.append({
            'entry_time': str(dt),
            'exit_time': str(dates[exit_bar]),
            'signal': 'LONG' if signal == 1 else 'SHORT',
            'pnl': float(trade_pnl),
            'exit_reason': exit_reason,
            'proba': float(row['proba']),
            'equity_after': float(equity),
            'timeframe': row['timeframe'],
        })

        blocked_until = dates[exit_bar]

    # Stats
    if not trades:
        return {'total_trades': 0, 'return_pct': 0, 'breached': breached}

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1

    # Drawdown from equity curve
    eq_curve = [initial_capital] + [t['equity_after'] for t in trades]
    eq_arr = np.array(eq_curve)
    peak_arr = np.maximum.accumulate(eq_arr)
    dd_arr = (eq_arr - peak_arr) / peak_arr * 100
    max_dd = float(dd_arr.min())

    # Monthly breakdown
    monthly = {}
    for t in trades:
        month = t['entry_time'][:7]
        if month not in monthly:
            monthly[month] = {'trades': 0, 'wins': 0, 'pnl': 0.0, 'longs': 0, 'shorts': 0}
        monthly[month]['trades'] += 1
        if t['pnl'] > 0:
            monthly[month]['wins'] += 1
        monthly[month]['pnl'] += t['pnl']
        if t['signal'] == 'LONG':
            monthly[month]['longs'] += 1
        else:
            monthly[month]['shorts'] += 1

    # Per-timeframe breakdown
    tf_breakdown = {}
    for tf in ['M5', 'M15', 'H1']:
        tf_trades = [t for t in trades if t['timeframe'] == tf]
        if tf_trades:
            tf_wins = [t for t in tf_trades if t['pnl'] > 0]
            tf_losses = [t for t in tf_trades if t['pnl'] <= 0]
            tf_gross_profit = sum(t['pnl'] for t in tf_wins) if tf_wins else 0
            tf_gross_loss = abs(sum(t['pnl'] for t in tf_losses)) if tf_losses else 1
            tf_breakdown[tf] = {
                'trades': len(tf_trades),
                'wins': len(tf_wins),
                'win_rate': len(tf_wins) / len(tf_trades) * 100,
                'pnl': sum(t['pnl'] for t in tf_trades),
                'profit_factor': tf_gross_profit / tf_gross_loss if tf_gross_loss > 0 else 0,
            }

    return {
        'initial_capital': initial_capital,
        'final_equity': float(equity),
        'total_pnl': float(equity - initial_capital),
        'return_pct': float((equity - initial_capital) / initial_capital * 100),
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': float(len(wins) / len(trades) * 100),
        'profit_factor': float(gross_profit / gross_loss),
        'max_drawdown_pct': max_dd,
        'peak_equity': float(peak_equity),
        'breached': breached,
        'breach_reason': breach_reason,
        'monthly': monthly,
        'exit_reasons': {
            'stop': len([t for t in trades if t['exit_reason'] == 'stop']),
            'tp': len([t for t in trades if t['exit_reason'] == 'tp']),
            'timeout': len([t for t in trades if t['exit_reason'] == 'timeout']),
        },
        'avg_win': float(np.mean([t['pnl'] for t in wins])) if wins else 0,
        'avg_loss': float(np.mean([t['pnl'] for t in losses])) if losses else 0,
        'tf_breakdown': tf_breakdown,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    start = datetime.now()
    print(f"HIM V2 COMBINED BACKTEST — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("OOS Period: 2025-01-01 to 2026-05-20")
    print("Models: M5 (12-bar hold) + M15 (16-bar hold) + H1 (4-bar hold)")
    print("Account: $10K, 50x leverage, 2% daily / 10% total loss limits")
    print("=" * 80)

    # Load M5 data
    print("\nLoading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']

    # OOS period
    oos_start = '2025-01-01'
    m5_oos = m5[m5.index >= oos_start]
    print(f"  M5 OOS bars: {len(m5_oos):,} ({m5_oos.index[0].date()} to {m5_oos.index[-1].date()})")

    # Resample for M15 and H1
    m15 = m5.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'tick_volume': 'sum', 'spread': 'mean',
    }).dropna(subset=['close'])
    m15 = m15[m15['tick_volume'] > 0]

    h1 = m5.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'tick_volume': 'sum', 'spread': 'mean',
    }).dropna(subset=['close'])
    h1 = h1[h1['tick_volume'] > 0]

    # Build features (need full history for EMAs, then filter to OOS)
    print("\nBuilding features...")
    m5_features = build_m5_features(m5)
    m15_features = build_m15_features(m15)
    h1_features = build_h1_features(h1)

    # Load model configs to get feature columns
    config_path = OUTPUT_DIR / "him_timeframe_configs.json"
    with open(config_path) as f:
        configs = json.load(f)

    m5_feat_cols = configs['M5']['features']
    m15_feat_cols = configs['M15']['features']
    h1_feat_cols = configs['H1']['features']

    # --- Trend filter: daily SMA50/100 from M5 close ---
    daily_close = m5['close'].resample('1D').last().dropna()
    d_sma50 = daily_close.rolling(50).mean()
    d_sma100 = daily_close.rolling(100).mean()
    daily_bull = ((daily_close > d_sma50) & (daily_close > d_sma100)).shift(2)  # 2-day lag for safety
    daily_bear = ((daily_close < d_sma50) & (daily_close < d_sma100)).shift(2)
    # Expand to M5 timeline
    daily_bull_m5 = daily_bull.reindex(m5.index, method='ffill').fillna(False)
    daily_bear_m5 = daily_bear.reindex(m5.index, method='ffill').fillna(False)
    # For M15/H1
    daily_bull_m15 = daily_bull.reindex(m15.index, method='ffill').fillna(False)
    daily_bear_m15 = daily_bear.reindex(m15.index, method='ffill').fillna(False)
    daily_bull_h1 = daily_bull.reindex(h1.index, method='ffill').fillna(False)
    daily_bear_h1 = daily_bear.reindex(h1.index, method='ffill').fillna(False)

    # Generate signals (OOS only) — different thresholds per timeframe
    print("\nGenerating signals...")
    m5_threshold = 0.65   # M5 needs higher confidence (noisy)
    m15_threshold = 0.65  # M15 higher gate — only best signals
    h1_threshold = 0.65   # H1 higher gate — only best signals

    m5_signals, m5_proba = generate_signals(
        MODEL_DIR / "Him_M5.json", m5_features[m5_features.index >= oos_start], m5_feat_cols, m5_threshold)
    m15_signals, m15_proba = generate_signals(
        MODEL_DIR / "Him_M15.json", m15_features[m15_features.index >= oos_start], m15_feat_cols, m15_threshold)
    h1_signals, h1_proba = generate_signals(
        MODEL_DIR / "Him_H1.json", h1_features[h1_features.index >= oos_start], h1_feat_cols, h1_threshold)

    # Apply trend filter
    m5_oos_bull = daily_bull_m5[m5_features.index >= oos_start].reindex(m5_signals.index).fillna(False)
    m5_oos_bear = daily_bear_m5[m5_features.index >= oos_start].reindex(m5_signals.index).fillna(False)
    m5_signals[(m5_signals == 1) & ~m5_oos_bull] = 0
    m5_signals[(m5_signals == -1) & ~m5_oos_bear] = 0

    m15_oos_bull = daily_bull_m15[m15_features.index >= oos_start].reindex(m15_signals.index).fillna(False)
    m15_oos_bear = daily_bear_m15[m15_features.index >= oos_start].reindex(m15_signals.index).fillna(False)
    m15_signals[(m15_signals == 1) & ~m15_oos_bull] = 0
    m15_signals[(m15_signals == -1) & ~m15_oos_bear] = 0

    h1_oos_bull = daily_bull_h1[h1_features.index >= oos_start].reindex(h1_signals.index).fillna(False)
    h1_oos_bear = daily_bear_h1[h1_features.index >= oos_start].reindex(h1_signals.index).fillna(False)
    h1_signals[(h1_signals == 1) & ~h1_oos_bull] = 0
    h1_signals[(h1_signals == -1) & ~h1_oos_bear] = 0

    print(f"  M5  signals: {(m5_signals != 0).sum()} entries (long={(m5_signals==1).sum()}, short={(m5_signals==-1).sum()})")
    print(f"  M15 signals: {(m15_signals != 0).sum()} entries (long={(m15_signals==1).sum()}, short={(m15_signals==-1).sum()})")
    print(f"  H1  signals: {(h1_signals != 0).sum()} entries (long={(h1_signals==1).sum()}, short={(h1_signals==-1).sum()})")

    # Build signal DataFrames with metadata
    # M5: 12 bars hold = 12 M5 bars
    m5_sigs = pd.DataFrame({
        'signal': m5_signals[m5_signals != 0],
        'proba': m5_proba[m5_signals != 0],
        'timeframe': 'M5',
        'holding_bars_m5': 12,
    })

    # M15: 16 bars hold = 16*3 = 48 M5 bars
    m15_sigs = pd.DataFrame({
        'signal': m15_signals[m15_signals != 0],
        'proba': m15_proba[m15_signals != 0],
        'timeframe': 'M15',
        'holding_bars_m5': 48,
    })

    # H1: 4 bars hold = 4*12 = 48 M5 bars
    h1_sigs = pd.DataFrame({
        'signal': h1_signals[h1_signals != 0],
        'proba': h1_proba[h1_signals != 0],
        'timeframe': 'H1',
        'holding_bars_m5': 48,
    })

    # Backtest configs per timeframe
    bt_config_m5 = {
        'risk_per_trade': 0.01,
        'stop_atr_mult': 1.5,
        'tp_atr_mult': 3.0,
    }
    bt_config_m15 = {
        'risk_per_trade': 0.01,
        'stop_atr_mult': 2.5,   # wider stop for mean-reversion
        'tp_atr_mult': 4.0,
    }
    bt_config_h1 = {
        'risk_per_trade': 0.01,
        'stop_atr_mult': 2.5,   # wider stop for swing
        'tp_atr_mult': 4.0,
    }
    bt_config_combined = {
        'risk_per_trade': 0.0075,  # reduced per-trade risk for multi-model
        'stop_atr_mult': 2.0,
        'tp_atr_mult': 3.5,
    }

    # === RUN 5 BACKTESTS ===
    print("\n" + "=" * 80)
    print("RUNNING BACKTESTS")
    print("=" * 80)

    results = {}

    # 1. M5 Solo
    print("\n  [1/5] M5 Solo...")
    results['M5_solo'] = run_backtest(m5_sigs, m5_oos, bt_config_m5)

    # 2. M15 Solo
    print("  [2/5] M15 Solo...")
    results['M15_solo'] = run_backtest(m15_sigs, m5_oos, bt_config_m15)

    # 3. H1 Solo
    print("  [3/5] H1 Solo...")
    results['H1_solo'] = run_backtest(h1_sigs, m5_oos, bt_config_h1)

    # 4. COMBINED ALL (all 3 on same account, sorted by time)
    print("  [4/5] COMBINED ALL (M5 + M15 + H1)...")
    combined_sigs = pd.concat([m5_sigs, m15_sigs, h1_sigs]).sort_index()
    results['COMBINED_ALL'] = run_backtest(combined_sigs, m5_oos, bt_config_combined)

    # 5. COMBINED M5+M15 only (drop weak H1)
    print("  [5/5] COMBINED M5+M15 (best pair)...")
    combined_m5m15 = pd.concat([m5_sigs, m15_sigs]).sort_index()
    results['COMBINED_M5_M15'] = run_backtest(combined_m5m15, m5_oos, bt_config_combined)

    # === RESULTS ===
    print("\n" + "=" * 80)
    print("RESULTS (OOS: 2025-01-01 to 2026-05-20)")
    print("=" * 80)

    print(f"\n  {'Strategy':<15} {'Trades':<8} {'WR%':<7} {'PF':<6} {'Return%':<10} {'MaxDD%':<8} {'Final$':<10} {'Breach'}")
    print(f"  {'-'*72}")

    for name, r in results.items():
        if r['total_trades'] == 0:
            print(f"  {name:<15} {'NO TRADES'}")
            continue
        breach_str = "BREACH" if r.get('breached') else "OK"
        print(f"  {name:<15} {r['total_trades']:<8} {r['win_rate']:<7.1f} {r['profit_factor']:<6.2f} {r['return_pct']:<+10.1f} {r['max_drawdown_pct']:<8.1f} ${r['final_equity']:<9,.0f} {breach_str}")

    # Combined detail — use best combined
    comb = results.get('COMBINED_M5_M15', results.get('COMBINED_ALL', results.get('COMBINED')))
    if comb['total_trades'] > 0 and 'tf_breakdown' in comb:
        print(f"\n  COMBINED BREAKDOWN BY TIMEFRAME:")
        print(f"  {'TF':<6} {'Trades':<8} {'WR%':<7} {'PF':<6} {'PnL':<12}")
        print(f"  {'-'*40}")
        for tf, stats in comb['tf_breakdown'].items():
            print(f"  {tf:<6} {stats['trades']:<8} {stats['win_rate']:<7.1f} {stats['profit_factor']:<6.2f} ${stats['pnl']:<+11,.0f}")

    # Monthly for combined
    if comb['total_trades'] > 0:
        print(f"\n  COMBINED MONTHLY:")
        print(f"  {'Month':<8} {'Trades':<7} {'Wins':<6} {'WR%':<7} {'PnL':<12}")
        print(f"  {'-'*44}")
        for month in sorted(comb['monthly'].keys()):
            m = comb['monthly'][month]
            wr = m['wins'] / m['trades'] * 100 if m['trades'] > 0 else 0
            print(f"  {month:<8} {m['trades']:<7} {m['wins']:<6} {wr:<7.1f} ${m['pnl']:<+11,.0f}")

    # Diversification benefit
    if all(results[k]['total_trades'] > 0 for k in ['M5_solo', 'M15_solo', 'H1_solo'] if k in results):
        solo_best = max(results[k]['return_pct'] for k in ['M5_solo', 'M15_solo', 'H1_solo'] if k in results and results[k]['total_trades'] > 0)
        best_combined_key = 'COMBINED_M5_M15' if 'COMBINED_M5_M15' in results else 'COMBINED_ALL'
        combined_ret = results[best_combined_key]['return_pct']
        solo_worst_dd = min(results[k]['max_drawdown_pct'] for k in ['M5_solo', 'M15_solo', 'H1_solo'] if k in results and results[k]['total_trades'] > 0)
        combined_dd = results[best_combined_key]['max_drawdown_pct']

        print(f"\n  DIVERSIFICATION ANALYSIS:")
        print(f"    Best solo return: +{solo_best:.1f}% | Combined: +{combined_ret:.1f}%")
        print(f"    Worst solo DD: {solo_worst_dd:.1f}% | Combined DD: {combined_dd:.1f}%")
        if combined_dd > solo_worst_dd:
            print(f"    ✓ Combined has BETTER drawdown than worst solo")

    # Save all results
    save_data = {
        'timestamp': datetime.now().isoformat(),
        'oos_period': f"{oos_start} to 2026-05-20",
        'thresholds': {'M5': m5_threshold, 'M15': m15_threshold, 'H1': h1_threshold},
        'trend_filter': True,
        'configs': {'M5': bt_config_m5, 'M15': bt_config_m15, 'H1': bt_config_h1, 'combined': bt_config_combined},
        'results': results,
    }

    output_path = OUTPUT_DIR / "combined_backtest_results.json"
    with open(output_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Results saved: {output_path}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"  Total time: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
