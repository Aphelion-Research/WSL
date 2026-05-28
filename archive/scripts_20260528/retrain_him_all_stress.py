"""
Him V2 Full Retrain + Stress Test
==================================
All 3 models: detrended labels, 10 EMA + VWAP universal features.
Two test periods:
  - Primary OOS: Train 2015-2024, Test 2025-2026
  - Stress test:  Train 2015-2019, Test 2020-2026 (survives crash?)
Backtest: propfirm rules, trend filter, timeframe-appropriate execution.
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
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

EMA_PERIODS = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]

XGB_PARAMS = {
    'max_depth': 4,
    'learning_rate': 0.05,
    'subsample': 0.7,
    'colsample_bytree': 0.5,
    'min_child_weight': 100,
    'reg_alpha': 3.0,
    'reg_lambda': 5.0,
    'objective': 'binary:logistic',
    'eval_metric': 'auc',
    'tree_method': 'hist',
    'seed': 42,
}


# ============================================================
# UNIVERSAL FEATURES
# ============================================================

def compute_10ema_ensemble(close):
    f = pd.DataFrame(index=close.index)
    emas = {}
    for p in EMA_PERIODS:
        emas[p] = close.ewm(span=p, adjust=False).mean()

    for p in [9, 21, 50, 200]:
        f[f'price_above_ema{p}'] = (close > emas[p]).astype(float)

    ordered = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]
    bullish_count = np.zeros(len(close))
    for i in range(len(ordered) - 1):
        bullish_count += (emas[ordered[i]].values > emas[ordered[i + 1]].values).astype(float)
    f['ema_bullish_count'] = bullish_count / (len(ordered) - 1)
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


# ============================================================
# TIMEFRAME FEATURE BUILDERS
# ============================================================

def build_m5_features_and_label(m5):
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
        rh = high.rolling(n).max()
        rl = low.rolling(n).min()
        f_spec[f'pullback_high_{n}'] = (rh - close) / close
        f_spec[f'pullback_low_{n}'] = (close - rl) / close

    rh_48 = close.rolling(48).max()
    rl_48 = close.rolling(48).min()
    rng_48 = (rh_48 - rl_48).replace(0, np.nan)
    f_spec['range_pos_4h'] = (close - rl_48) / rng_48

    f_spec['vol_ratio'] = volume / volume.rolling(48).mean().replace(0, np.nan)

    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_24 = tr.rolling(24).mean()
    f_spec['atr_2h_pct'] = atr_24 / close
    f_spec['vol_ratio_short_long'] = tr.rolling(12).mean() / atr_24.replace(0, np.nan)

    hour = m5.index.hour + m5.index.minute / 60
    f_spec['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)

    features = pd.concat([f_ema, f_vwap, f_spec], axis=1)

    # Detrended label: 12-bar forward excess return
    fwd_ret_12 = close.pct_change(12).shift(-12)
    trailing_avg = close.pct_change(12).rolling(48).mean()
    label = (fwd_ret_12 > trailing_avg).astype(float)

    return features, label


def build_m15_features_and_label(m15):
    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    f_spec = pd.DataFrame(index=m15.index)
    for bars in [16, 32, 64, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_96 = tr.rolling(96).mean().replace(0, np.nan)

    for period in [16, 32, 64]:
        rh = close.rolling(period).max()
        f_spec[f'pullback_high_{period}'] = (rh - close) / atr_96

    rh96 = close.rolling(96).max()
    rl96 = close.rolling(96).min()
    rng_96 = (rh96 - rl96).replace(0, np.nan)
    f_spec['range_pos_96bar'] = (close - rl96) / rng_96

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

    # Detrended label: 16-bar excess return
    fwd_ret_16 = close.pct_change(16).shift(-16)
    trailing_avg = close.pct_change(16).rolling(96).mean()
    label = (fwd_ret_16 > trailing_avg).astype(float)

    return features, label


def build_h1_features_and_label(h1):
    close = h1['close']
    high = h1['high']
    low = h1['low']
    volume = h1['tick_volume']

    f_ema = compute_10ema_ensemble(close)
    f_vwap = compute_vwap_bands(close, high, low, volume, period=72)

    f_spec = pd.DataFrame(index=h1.index)
    for bars in [1, 2, 4, 8, 12, 24, 48, 96]:
        f_spec[f'ret_{bars}bar'] = close.pct_change(bars)

    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
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

    # Detrended label: 4-bar excess return
    fwd_ret_4h = close.pct_change(4).shift(-4)
    trailing_avg = close.pct_change(4).rolling(24).mean()
    label = (fwd_ret_4h > trailing_avg).astype(float)

    return features, label


# ============================================================
# TRAIN + PREDICT
# ============================================================

def train_model(features, label, feature_cols, train_end, model_name):
    df = features[feature_cols].copy()
    df['label'] = label
    df = df.dropna()

    train = df[df.index <= train_end]
    test = df[df.index > train_end]

    if len(test) == 0:
        return None, None, None

    dtrain = xgb.DMatrix(train[feature_cols].values, label=train['label'].values, feature_names=feature_cols)
    dtest = xgb.DMatrix(test[feature_cols].values, label=test['label'].values, feature_names=feature_cols)

    model = xgb.train(
        XGB_PARAMS, dtrain,
        num_boost_round=300,
        evals=[(dtrain, 'train'), (dtest, 'test')],
        early_stopping_rounds=50,
        verbose_eval=0,
    )

    test_pred = model.predict(dtest)
    test_auc = roc_auc_score(test['label'].values, test_pred)

    print(f"    {model_name}: AUC={test_auc:.4f} | iter={model.best_iteration} | pred_std={test_pred.std():.4f} | n_test={len(test):,}")

    return model, test_auc, test_pred


# ============================================================
# BACKTEST ENGINE
# ============================================================

def compute_trend_filter(m5):
    """Daily SMA50/100 trend filter."""
    daily_close = m5['close'].resample('1D').last().dropna()
    d_sma50 = daily_close.rolling(50).mean()
    d_sma100 = daily_close.rolling(100).mean()
    daily_bull = ((daily_close > d_sma50) & (daily_close > d_sma100)).shift(2)
    daily_bear = ((daily_close < d_sma50) & (daily_close < d_sma100)).shift(2)
    return daily_bull, daily_bear


def run_backtest(m5_oos, proba, signal_times, holding_bars_m5, config, trend_bull=None, trend_bear=None):
    """
    Propfirm backtest on M5 bars.
    proba: array of probabilities aligned with signal_times
    signal_times: DatetimeIndex of signal bars
    """
    threshold = config['threshold']
    risk_pct = config['risk_per_trade']
    stop_mult = config['stop_atr_mult']
    tp_mult = config['tp_atr_mult']
    use_stops = config.get('use_stops', True)

    leverage = 50
    initial_capital = 10000.0
    daily_loss_limit = 0.02
    total_loss_breach = 9000.0

    equity = initial_capital
    peak_equity = initial_capital
    daily_start_equity = initial_capital
    current_date = None
    daily_pnl = 0.0

    close = m5_oos['close'].values
    high_arr = m5_oos['high'].values
    low_arr = m5_oos['low'].values
    dates = m5_oos.index

    # ATR on M5 (12-bar = 1h)
    tr = np.maximum(high_arr - low_arr, np.maximum(
        np.abs(high_arr - np.roll(close, 1)),
        np.abs(low_arr - np.roll(close, 1))))
    tr[0] = high_arr[0] - low_arr[0]
    atr = pd.Series(tr, index=dates).rolling(12).mean().values

    # Expand trend to M5 if provided
    if trend_bull is not None:
        bull_m5 = trend_bull.reindex(dates, method='ffill').fillna(False).values
        bear_m5 = trend_bear.reindex(dates, method='ffill').fillna(False).values
    else:
        bull_m5 = np.ones(len(dates), dtype=bool)
        bear_m5 = np.ones(len(dates), dtype=bool)

    trades = []
    breached = False
    blocked_until_idx = -1

    for sig_idx, (sig_time, p) in enumerate(zip(signal_times, proba)):
        if breached:
            break

        # Determine signal
        if p > threshold:
            signal = 1
        elif p < (1 - threshold):
            signal = -1
        else:
            continue

        # Find in M5 timeline
        m5_idx = dates.searchsorted(sig_time)
        if m5_idx >= len(close) - 1 or m5_idx <= blocked_until_idx:
            continue

        # Trend filter
        if signal == 1 and not bull_m5[m5_idx]:
            continue
        if signal == -1 and not bear_m5[m5_idx]:
            continue

        dt = dates[m5_idx]

        # Account checks
        if equity <= total_loss_breach:
            breached = True
            break

        if current_date is None or dt.date() != current_date:
            current_date = dt.date()
            daily_start_equity = equity
            daily_pnl = 0.0

        if daily_pnl <= -(daily_start_equity * daily_loss_limit):
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

        # Simulate
        exit_price = None
        exit_reason = None
        exit_bar = m5_idx

        end_bar = min(m5_idx + holding_bars_m5, len(close) - 1)
        for j in range(m5_idx + 1, end_bar + 1):
            if use_stops:
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
            exit_bar = end_bar
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
            'signal': 'LONG' if signal == 1 else 'SHORT',
            'pnl': float(trade_pnl),
            'exit_reason': exit_reason,
            'equity_after': float(equity),
        })

        blocked_until_idx = exit_bar

    if not trades:
        return {'total_trades': 0, 'return_pct': 0.0, 'breached': False, 'win_rate': 0, 'profit_factor': 0, 'max_drawdown_pct': 0}

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1

    eq_curve = np.array([initial_capital] + [t['equity_after'] for t in trades])
    peak_arr = np.maximum.accumulate(eq_curve)
    dd_arr = (eq_curve - peak_arr) / peak_arr * 100
    max_dd = float(dd_arr.min())

    # Monthly
    monthly = {}
    for t in trades:
        month = t['entry_time'][:7]
        if month not in monthly:
            monthly[month] = {'trades': 0, 'wins': 0, 'pnl': 0.0}
        monthly[month]['trades'] += 1
        if t['pnl'] > 0:
            monthly[month]['wins'] += 1
        monthly[month]['pnl'] += t['pnl']

    # Check 2020 crash survival
    crash_months = {k: v for k, v in monthly.items() if k.startswith('2020-03') or k.startswith('2020-04')}

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
        'monthly': monthly,
        'crash_2020': crash_months,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    start = datetime.now()
    print(f"HIM V2 FULL RETRAIN + STRESS TEST — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Load data
    print("\nLoading M5 data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']
    print(f"  M5: {len(m5):,} bars ({m5.index[0].date()} to {m5.index[-1].date()})")

    # Resample
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

    print(f"  M15: {len(m15):,} bars | H1: {len(h1):,} bars")

    # Build features + labels
    print("\nBuilding features...")
    m5_features, m5_label = build_m5_features_and_label(m5)
    m15_features, m15_label = build_m15_features_and_label(m15)
    h1_features, h1_label = build_h1_features_and_label(h1)

    m5_feat_cols = list(m5_features.columns)
    m15_feat_cols = list(m15_features.columns)
    h1_feat_cols = list(h1_features.columns)

    print(f"  M5: {len(m5_feat_cols)} features | M15: {len(m15_feat_cols)} | H1: {len(h1_feat_cols)}")

    # Trend filter
    trend_bull, trend_bear = compute_trend_filter(m5)

    # ============================================================
    # PHASE 1: PRIMARY OOS (Train 2015-2024, Test 2025-2026)
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 1: PRIMARY OOS (Train 2015-2024, Test 2025-2026)")
    print("=" * 80)

    train_end_primary = pd.Timestamp('2024-12-31 23:59:00')

    print("\n  Training...")
    m5_model_p, m5_auc_p, _ = train_model(m5_features, m5_label, m5_feat_cols, train_end_primary, "M5")
    m15_model_p, m15_auc_p, _ = train_model(m15_features, m15_label, m15_feat_cols, train_end_primary, "M15")
    h1_model_p, h1_auc_p, _ = train_model(h1_features, h1_label, h1_feat_cols, train_end_primary, "H1")

    # Save primary models
    if m5_model_p:
        m5_model_p.save_model(str(MODEL_DIR / "Him_M5.json"))
    if m15_model_p:
        m15_model_p.save_model(str(MODEL_DIR / "Him_M15.json"))
    if h1_model_p:
        h1_model_p.save_model(str(MODEL_DIR / "Him_H1.json"))

    # Backtest primary OOS
    print("\n  Backtesting OOS 2025-2026...")
    m5_oos = m5[m5.index >= '2025-01-01']

    # M5 predictions on OOS
    m5_oos_feat = m5_features[m5_features.index >= '2025-01-01'].dropna()
    m5_oos_dmat = xgb.DMatrix(m5_oos_feat[m5_feat_cols].values, feature_names=m5_feat_cols)
    m5_oos_proba = m5_model_p.predict(m5_oos_dmat)

    # M15 predictions on OOS
    m15_oos_feat = m15_features[m15_features.index >= '2025-01-01'].dropna()
    m15_oos_dmat = xgb.DMatrix(m15_oos_feat[m15_feat_cols].values, feature_names=m15_feat_cols)
    m15_oos_proba = m15_model_p.predict(m15_oos_dmat)

    # H1 predictions on OOS
    h1_oos_feat = h1_features[h1_features.index >= '2025-01-01'].dropna()
    h1_oos_dmat = xgb.DMatrix(h1_oos_feat[h1_feat_cols].values, feature_names=h1_feat_cols)
    h1_oos_proba = h1_model_p.predict(h1_oos_dmat)

    # Configs
    m5_bt_config = {'threshold': 0.65, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0, 'use_stops': True}
    m15_bt_config = {'threshold': 0.60, 'risk_per_trade': 0.01, 'stop_atr_mult': 2.0, 'tp_atr_mult': 3.5, 'use_stops': True}
    h1_bt_config = {'threshold': 0.60, 'risk_per_trade': 0.01, 'stop_atr_mult': 2.5, 'tp_atr_mult': 4.0, 'use_stops': True}
    # H1 also test without stops (hold-to-horizon)
    h1_bt_config_nonstop = {'threshold': 0.60, 'risk_per_trade': 0.01, 'stop_atr_mult': 2.5, 'tp_atr_mult': 4.0, 'use_stops': False}

    bt_m5_p = run_backtest(m5_oos, m5_oos_proba, m5_oos_feat.index, 12, m5_bt_config, trend_bull, trend_bear)
    bt_m15_p = run_backtest(m5_oos, m15_oos_proba, m15_oos_feat.index, 48, m15_bt_config, trend_bull, trend_bear)
    bt_h1_p = run_backtest(m5_oos, h1_oos_proba, h1_oos_feat.index, 48, h1_bt_config, trend_bull, trend_bear)
    bt_h1_p_ns = run_backtest(m5_oos, h1_oos_proba, h1_oos_feat.index, 48, h1_bt_config_nonstop, trend_bull, trend_bear)

    print(f"\n  {'Model':<20} {'Trades':<8} {'WR%':<7} {'PF':<6} {'Return%':<10} {'MaxDD%':<8} {'Breach'}")
    print(f"  {'-'*65}")
    for name, bt in [('M5 (stops)', bt_m5_p), ('M15 (stops)', bt_m15_p), ('H1 (stops)', bt_h1_p), ('H1 (hold-to-exit)', bt_h1_p_ns)]:
        if bt['total_trades'] > 0:
            print(f"  {name:<20} {bt['total_trades']:<8} {bt['win_rate']:<7.1f} {bt['profit_factor']:<6.2f} {bt['return_pct']:<+10.1f} {bt['max_drawdown_pct']:<8.1f} {'BREACH' if bt['breached'] else 'OK'}")
        else:
            print(f"  {name:<20} NO TRADES")

    # ============================================================
    # PHASE 2: STRESS TEST (Train 2015-2019, Test 2020-2026)
    # ============================================================
    print("\n" + "=" * 80)
    print("PHASE 2: STRESS TEST (Train 2015-2019, Test 2020-2026)")
    print("=" * 80)

    train_end_stress = pd.Timestamp('2019-12-31 23:59:00')

    print("\n  Training (smaller dataset — 2015-2019 only)...")
    m5_model_s, m5_auc_s, _ = train_model(m5_features, m5_label, m5_feat_cols, train_end_stress, "M5")
    m15_model_s, m15_auc_s, _ = train_model(m15_features, m15_label, m15_feat_cols, train_end_stress, "M15")
    h1_model_s, h1_auc_s, _ = train_model(h1_features, h1_label, h1_feat_cols, train_end_stress, "H1")

    # Backtest stress test on 2020-2026
    print("\n  Backtesting 2020-2026 (includes COVID crash)...")
    m5_stress = m5[m5.index >= '2020-01-01']

    m5_stress_feat = m5_features[m5_features.index >= '2020-01-01'].dropna()
    m5_stress_dmat = xgb.DMatrix(m5_stress_feat[m5_feat_cols].values, feature_names=m5_feat_cols)
    m5_stress_proba = m5_model_s.predict(m5_stress_dmat)

    m15_stress_feat = m15_features[m15_features.index >= '2020-01-01'].dropna()
    m15_stress_dmat = xgb.DMatrix(m15_stress_feat[m15_feat_cols].values, feature_names=m15_feat_cols)
    m15_stress_proba = m15_model_s.predict(m15_stress_dmat)

    h1_stress_feat = h1_features[h1_features.index >= '2020-01-01'].dropna()
    h1_stress_dmat = xgb.DMatrix(h1_stress_feat[h1_feat_cols].values, feature_names=h1_feat_cols)
    h1_stress_proba = h1_model_s.predict(h1_stress_dmat)

    bt_m5_s = run_backtest(m5_stress, m5_stress_proba, m5_stress_feat.index, 12, m5_bt_config, trend_bull, trend_bear)
    bt_m15_s = run_backtest(m5_stress, m15_stress_proba, m15_stress_feat.index, 48, m15_bt_config, trend_bull, trend_bear)
    bt_h1_s = run_backtest(m5_stress, h1_stress_proba, h1_stress_feat.index, 48, h1_bt_config, trend_bull, trend_bear)
    bt_h1_s_ns = run_backtest(m5_stress, h1_stress_proba, h1_stress_feat.index, 48, h1_bt_config_nonstop, trend_bull, trend_bear)

    print(f"\n  {'Model':<20} {'Trades':<8} {'WR%':<7} {'PF':<6} {'Return%':<10} {'MaxDD%':<8} {'Breach'}")
    print(f"  {'-'*65}")
    for name, bt in [('M5 (stops)', bt_m5_s), ('M15 (stops)', bt_m15_s), ('H1 (stops)', bt_h1_s), ('H1 (hold-to-exit)', bt_h1_s_ns)]:
        if bt['total_trades'] > 0:
            print(f"  {name:<20} {bt['total_trades']:<8} {bt['win_rate']:<7.1f} {bt['profit_factor']:<6.2f} {bt['return_pct']:<+10.1f} {bt['max_drawdown_pct']:<8.1f} {'BREACH' if bt['breached'] else 'OK'}")
        else:
            print(f"  {name:<20} NO TRADES")

    # 2020 crash detail
    print("\n  2020 CRASH SURVIVAL (Mar-Apr 2020):")
    for name, bt in [('M5', bt_m5_s), ('M15', bt_m15_s), ('H1 stops', bt_h1_s), ('H1 hold', bt_h1_s_ns)]:
        crash = bt.get('crash_2020', {})
        if crash:
            crash_pnl = sum(m['pnl'] for m in crash.values())
            crash_trades = sum(m['trades'] for m in crash.values())
            print(f"    {name:<15} Trades={crash_trades} | PnL=${crash_pnl:+,.0f}")
        else:
            print(f"    {name:<15} No trades during crash")

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    print(f"\n  {'Model':<12} {'OOS AUC':<10} {'OOS Ret%':<10} {'OOS DD%':<9} {'Stress Ret%':<12} {'Stress DD%':<11} {'Crash OK?'}")
    print(f"  {'-'*75}")

    for name, auc_p, bt_p, bt_s in [
        ('M5', m5_auc_p, bt_m5_p, bt_m5_s),
        ('M15', m15_auc_p, bt_m15_p, bt_m15_s),
        ('H1 stops', h1_auc_p, bt_h1_p, bt_h1_s),
        ('H1 hold', h1_auc_p, bt_h1_p_ns, bt_h1_s_ns),
    ]:
        crash = bt_s.get('crash_2020', {})
        crash_pnl = sum(m['pnl'] for m in crash.values()) if crash else 0
        crash_ok = "YES" if crash_pnl > 0 else ("SKIP" if not crash else "NO")
        print(f"  {name:<12} {auc_p:<10.4f} {bt_p['return_pct']:<+10.1f} {bt_p['max_drawdown_pct']:<9.1f} {bt_s['return_pct']:<+12.1f} {bt_s['max_drawdown_pct']:<11.1f} {crash_ok}")

    # Save results
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'primary_oos': {
            'train': '2015-2024', 'test': '2025-2026',
            'M5': {'auc': m5_auc_p, **{k: v for k, v in bt_m5_p.items() if k != 'monthly'}},
            'M15': {'auc': m15_auc_p, **{k: v for k, v in bt_m15_p.items() if k != 'monthly'}},
            'H1_stops': {'auc': h1_auc_p, **{k: v for k, v in bt_h1_p.items() if k != 'monthly'}},
            'H1_hold': {'auc': h1_auc_p, **{k: v for k, v in bt_h1_p_ns.items() if k != 'monthly'}},
        },
        'stress_test': {
            'train': '2015-2019', 'test': '2020-2026',
            'M5': {'auc': m5_auc_s, **{k: v for k, v in bt_m5_s.items() if k != 'monthly'}},
            'M15': {'auc': m15_auc_s, **{k: v for k, v in bt_m15_s.items() if k != 'monthly'}},
            'H1_stops': {'auc': h1_auc_s, **{k: v for k, v in bt_h1_s.items() if k != 'monthly'}},
            'H1_hold': {'auc': h1_auc_s, **{k: v for k, v in bt_h1_s_ns.items() if k != 'monthly'}},
        },
    }

    output_path = OUTPUT_DIR / "stress_test_results.json"
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  Results saved: {output_path}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"  Total time: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
