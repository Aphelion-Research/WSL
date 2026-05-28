"""
Him V2 Proper Risk Management Per Timeframe
=============================================
M5:  Directional stops (1.5/3.0 ATR) — proven
M15: Hold-to-horizon + catastrophic stop (5 ATR) — mean-reversion needs time
H1:  Hold-to-horizon + catastrophic stop (5 ATR) — same logic

Key insight: mean-reversion labels predict "excess return over N bars" not "price goes up now".
Tight stops trigger on noise BEFORE the mean-reversion completes.
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
# FEATURE BUILDERS (same as before)
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


def build_m5_features_and_label(m5):
    close, high, low, volume = m5['close'], m5['high'], m5['low'], m5['tick_volume']
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
    fwd_ret_12 = close.pct_change(12).shift(-12)
    trailing_avg = close.pct_change(12).rolling(48).mean()
    label = (fwd_ret_12 > trailing_avg).astype(float)
    return features, label


def build_m15_features_and_label(m15):
    close, high, low, volume = m15['close'], m15['high'], m15['low'], m15['tick_volume']
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
    fwd_ret_16 = close.pct_change(16).shift(-16)
    trailing_avg = close.pct_change(16).rolling(96).mean()
    label = (fwd_ret_16 > trailing_avg).astype(float)
    return features, label


def build_h1_features_and_label(h1):
    close, high, low, volume = h1['close'], h1['high'], h1['low'], h1['tick_volume']
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
    fwd_ret_4h = close.pct_change(4).shift(-4)
    trailing_avg = close.pct_change(4).rolling(24).mean()
    label = (fwd_ret_4h > trailing_avg).astype(float)
    return features, label


# ============================================================
# BACKTEST ENGINE — per-model risk profiles
# ============================================================

def run_backtest(m5_data, proba, signal_times, risk_profile, trend_bull=None, trend_bear=None):
    """
    Risk profiles:
      'momentum': tight stops, TP target (M5)
      'mean_reversion': hold-to-horizon, catastrophic stop only, smaller size
      'mean_reversion_wide': wide stops (3 ATR), no TP, hold to horizon
    """
    threshold = risk_profile['threshold']
    risk_pct = risk_profile['risk_per_trade']
    holding_bars = risk_profile['holding_bars_m5']
    mode = risk_profile['mode']  # 'momentum' or 'mean_reversion'
    stop_mult = risk_profile.get('stop_atr_mult', 1.5)
    tp_mult = risk_profile.get('tp_atr_mult', 3.0)
    catastrophic_mult = risk_profile.get('catastrophic_stop_mult', 5.0)

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

    tr = np.maximum(high_arr - low_arr, np.maximum(
        np.abs(high_arr - np.roll(close, 1)),
        np.abs(low_arr - np.roll(close, 1))))
    tr[0] = high_arr[0] - low_arr[0]
    atr = pd.Series(tr, index=dates).rolling(12).mean().values

    if trend_bull is not None:
        bull_m5 = trend_bull.reindex(dates, method='ffill').fillna(False).values
        bear_m5 = trend_bear.reindex(dates, method='ffill').fillna(False).values
    else:
        bull_m5 = np.ones(len(dates), dtype=bool)
        bear_m5 = np.ones(len(dates), dtype=bool)

    trades = []
    breached = False
    blocked_until_idx = -1

    for sig_time, p in zip(signal_times, proba):
        if breached:
            break

        if p > threshold:
            signal = 1
        elif p < (1 - threshold):
            signal = -1
        else:
            continue

        m5_idx = dates.searchsorted(sig_time)
        if m5_idx >= len(close) - 1 or m5_idx <= blocked_until_idx:
            continue

        if signal == 1 and not bull_m5[m5_idx]:
            continue
        if signal == -1 and not bear_m5[m5_idx]:
            continue

        dt = dates[m5_idx]

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
        oz_per_lot = 100

        if mode == 'momentum':
            # Standard directional: stop defines position size
            stop_distance = atr[m5_idx] * stop_mult
            tp_distance = atr[m5_idx] * tp_mult
            risk_amount = equity * risk_pct
            lots = risk_amount / (stop_distance * oz_per_lot)

        elif mode == 'mean_reversion':
            # Hold-to-horizon: size by max expected adverse excursion (2 ATR)
            # Catastrophic stop at 5 ATR only for black swans
            stop_distance = atr[m5_idx] * catastrophic_mult
            tp_distance = None  # no TP — hold to horizon
            expected_adverse = atr[m5_idx] * 2.0
            risk_amount = equity * risk_pct
            lots = risk_amount / (expected_adverse * oz_per_lot)

        elif mode == 'mean_reversion_wide':
            # Wide stops, no TP, hold to horizon
            stop_distance = atr[m5_idx] * stop_mult
            tp_distance = None
            risk_amount = equity * risk_pct
            lots = risk_amount / (stop_distance * oz_per_lot)

        max_lots = (equity * leverage) / (entry_price * oz_per_lot)
        lots = min(lots, max_lots)
        if lots <= 0:
            continue

        if signal == 1:
            stop_price = entry_price - stop_distance
            tp_price = entry_price + tp_distance if tp_distance else None
        else:
            stop_price = entry_price + stop_distance
            tp_price = entry_price - tp_distance if tp_distance else None

        # Simulate trade
        exit_price = None
        exit_reason = None
        exit_bar = m5_idx
        end_bar = min(m5_idx + holding_bars, len(close) - 1)

        for j in range(m5_idx + 1, end_bar + 1):
            # Catastrophic/regular stop always active
            if signal == 1:
                if low_arr[j] <= stop_price:
                    exit_price = stop_price
                    exit_reason = 'stop'
                    exit_bar = j
                    break
                if tp_price and high_arr[j] >= tp_price:
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
                if tp_price and low_arr[j] <= tp_price:
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
        return {'total_trades': 0, 'return_pct': 0.0, 'breached': False, 'win_rate': 0, 'profit_factor': 0, 'max_drawdown_pct': 0, 'monthly': {}}

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1

    eq_curve = np.array([initial_capital] + [t['equity_after'] for t in trades])
    peak_arr = np.maximum.accumulate(eq_curve)
    dd_arr = (eq_curve - peak_arr) / peak_arr * 100
    max_dd = float(dd_arr.min())

    monthly = {}
    for t in trades:
        month = t['entry_time'][:7]
        if month not in monthly:
            monthly[month] = {'trades': 0, 'wins': 0, 'pnl': 0.0}
        monthly[month]['trades'] += 1
        if t['pnl'] > 0:
            monthly[month]['wins'] += 1
        monthly[month]['pnl'] += t['pnl']

    exit_reasons = {}
    for t in trades:
        r = t['exit_reason']
        exit_reasons[r] = exit_reasons.get(r, 0) + 1

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
        'exit_reasons': exit_reasons,
        'avg_win': float(np.mean([t['pnl'] for t in wins])) if wins else 0,
        'avg_loss': float(np.mean([t['pnl'] for t in losses])) if losses else 0,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    start = datetime.now()
    print(f"HIM V2 PROPER RISK PER MODEL — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("M5:  Momentum execution (1.5/3.0 ATR stop/TP, 1% risk)")
    print("M15: Mean-reversion (hold-to-horizon, 5 ATR catastrophic, 0.75% risk)")
    print("H1:  Mean-reversion (hold-to-horizon, 5 ATR catastrophic, 0.75% risk)")
    print("     + Wide-stop variant (3 ATR stop, no TP)")
    print("=" * 80)

    # Load
    print("\nLoading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']

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

    # Features
    print("Building features...")
    m5_features, m5_label = build_m5_features_and_label(m5)
    m15_features, m15_label = build_m15_features_and_label(m15)
    h1_features, h1_label = build_h1_features_and_label(h1)

    m5_feat_cols = list(m5_features.columns)
    m15_feat_cols = list(m15_features.columns)
    h1_feat_cols = list(h1_features.columns)

    # Trend filter
    daily_close = m5['close'].resample('1D').last().dropna()
    d_sma50 = daily_close.rolling(50).mean()
    d_sma100 = daily_close.rolling(100).mean()
    trend_bull = ((daily_close > d_sma50) & (daily_close > d_sma100)).shift(2)
    trend_bear = ((daily_close < d_sma50) & (daily_close < d_sma100)).shift(2)

    # ============================================================
    # TRAIN (2015-2024)
    # ============================================================
    print("\nTraining (2015-2024)...")
    train_end = pd.Timestamp('2024-12-31 23:59:00')

    def train_xgb(features, label, feat_cols, train_end, name):
        df = features[feat_cols].copy()
        df['label'] = label
        df = df.dropna()
        train = df[df.index <= train_end]
        test = df[df.index > train_end]
        dtrain = xgb.DMatrix(train[feat_cols].values, label=train['label'].values, feature_names=feat_cols)
        dtest = xgb.DMatrix(test[feat_cols].values, label=test['label'].values, feature_names=feat_cols)
        model = xgb.train(XGB_PARAMS, dtrain, num_boost_round=300,
                          evals=[(dtrain, 'train'), (dtest, 'test')],
                          early_stopping_rounds=50, verbose_eval=0)
        test_pred = model.predict(dtest)
        test_auc = roc_auc_score(test['label'].values, test_pred)
        print(f"  {name}: AUC={test_auc:.4f} | iter={model.best_iteration} | std={test_pred.std():.4f}")
        return model, test_auc

    m5_model, m5_auc = train_xgb(m5_features, m5_label, m5_feat_cols, train_end, "M5")
    m15_model, m15_auc = train_xgb(m15_features, m15_label, m15_feat_cols, train_end, "M15")
    h1_model, h1_auc = train_xgb(h1_features, h1_label, h1_feat_cols, train_end, "H1")

    # Save models
    m5_model.save_model(str(MODEL_DIR / "Him_M5.json"))
    m15_model.save_model(str(MODEL_DIR / "Him_M15.json"))
    h1_model.save_model(str(MODEL_DIR / "Him_H1.json"))

    # ============================================================
    # BACKTEST OOS (2025-2026)
    # ============================================================
    print("\n" + "=" * 80)
    print("BACKTEST: OOS 2025-2026")
    print("=" * 80)

    m5_oos = m5[m5.index >= '2025-01-01']

    # Predictions
    m5_oos_feat = m5_features[m5_features.index >= '2025-01-01'].dropna()
    m5_proba = m5_model.predict(xgb.DMatrix(m5_oos_feat[m5_feat_cols].values, feature_names=m5_feat_cols))

    m15_oos_feat = m15_features[m15_features.index >= '2025-01-01'].dropna()
    m15_proba = m15_model.predict(xgb.DMatrix(m15_oos_feat[m15_feat_cols].values, feature_names=m15_feat_cols))

    h1_oos_feat = h1_features[h1_features.index >= '2025-01-01'].dropna()
    h1_proba = h1_model.predict(xgb.DMatrix(h1_oos_feat[h1_feat_cols].values, feature_names=h1_feat_cols))

    # Risk profiles
    m5_risk = {
        'mode': 'momentum',
        'threshold': 0.65,
        'risk_per_trade': 0.01,
        'stop_atr_mult': 1.5,
        'tp_atr_mult': 3.0,
        'holding_bars_m5': 12,
    }

    m15_risk_hold = {
        'mode': 'mean_reversion',
        'threshold': 0.60,
        'risk_per_trade': 0.0075,
        'catastrophic_stop_mult': 5.0,
        'holding_bars_m5': 48,  # 16 M15 bars = 4h
    }

    m15_risk_wide = {
        'mode': 'mean_reversion_wide',
        'threshold': 0.60,
        'risk_per_trade': 0.0075,
        'stop_atr_mult': 3.5,
        'holding_bars_m5': 48,
    }

    h1_risk_hold = {
        'mode': 'mean_reversion',
        'threshold': 0.60,
        'risk_per_trade': 0.0075,
        'catastrophic_stop_mult': 5.0,
        'holding_bars_m5': 48,  # 4 H1 bars = 4h
    }

    h1_risk_wide = {
        'mode': 'mean_reversion_wide',
        'threshold': 0.60,
        'risk_per_trade': 0.0075,
        'stop_atr_mult': 3.5,
        'holding_bars_m5': 48,
    }

    print("\n  Running backtests...")
    results_oos = {}
    results_oos['M5_momentum'] = run_backtest(m5_oos, m5_proba, m5_oos_feat.index, m5_risk, trend_bull, trend_bear)
    results_oos['M15_hold'] = run_backtest(m5_oos, m15_proba, m15_oos_feat.index, m15_risk_hold, trend_bull, trend_bear)
    results_oos['M15_wide'] = run_backtest(m5_oos, m15_proba, m15_oos_feat.index, m15_risk_wide, trend_bull, trend_bear)
    results_oos['H1_hold'] = run_backtest(m5_oos, h1_proba, h1_oos_feat.index, h1_risk_hold, trend_bull, trend_bear)
    results_oos['H1_wide'] = run_backtest(m5_oos, h1_proba, h1_oos_feat.index, h1_risk_wide, trend_bull, trend_bear)

    print(f"\n  {'Strategy':<18} {'Trades':<8} {'WR%':<7} {'PF':<6} {'Return%':<10} {'MaxDD%':<8} {'Exits':<25} {'Status'}")
    print(f"  {'-'*90}")
    for name, r in results_oos.items():
        if r['total_trades'] > 0:
            exits = r.get('exit_reasons', {})
            exit_str = f"s:{exits.get('stop',0)} tp:{exits.get('tp',0)} t:{exits.get('timeout',0)}"
            status = "BREACH" if r['breached'] else "OK"
            print(f"  {name:<18} {r['total_trades']:<8} {r['win_rate']:<7.1f} {r['profit_factor']:<6.2f} {r['return_pct']:<+10.1f} {r['max_drawdown_pct']:<8.1f} {exit_str:<25} {status}")

    # ============================================================
    # STRESS TEST (Train 2015-2019, Test 2020-2026)
    # ============================================================
    print("\n" + "=" * 80)
    print("STRESS TEST: Train 2015-2019, Test 2020-2026")
    print("=" * 80)

    train_end_s = pd.Timestamp('2019-12-31 23:59:00')
    print("\n  Training on 2015-2019...")
    m5_model_s, m5_auc_s = train_xgb(m5_features, m5_label, m5_feat_cols, train_end_s, "M5")
    m15_model_s, m15_auc_s = train_xgb(m15_features, m15_label, m15_feat_cols, train_end_s, "M15")
    h1_model_s, h1_auc_s = train_xgb(h1_features, h1_label, h1_feat_cols, train_end_s, "H1")

    m5_stress = m5[m5.index >= '2020-01-01']

    m5_s_feat = m5_features[m5_features.index >= '2020-01-01'].dropna()
    m5_s_proba = m5_model_s.predict(xgb.DMatrix(m5_s_feat[m5_feat_cols].values, feature_names=m5_feat_cols))

    m15_s_feat = m15_features[m15_features.index >= '2020-01-01'].dropna()
    m15_s_proba = m15_model_s.predict(xgb.DMatrix(m15_s_feat[m15_feat_cols].values, feature_names=m15_feat_cols))

    h1_s_feat = h1_features[h1_features.index >= '2020-01-01'].dropna()
    h1_s_proba = h1_model_s.predict(xgb.DMatrix(h1_s_feat[h1_feat_cols].values, feature_names=h1_feat_cols))

    print("\n  Running stress backtests (2020-2026)...")
    results_stress = {}
    results_stress['M5_momentum'] = run_backtest(m5_stress, m5_s_proba, m5_s_feat.index, m5_risk, trend_bull, trend_bear)
    results_stress['M15_hold'] = run_backtest(m5_stress, m15_s_proba, m15_s_feat.index, m15_risk_hold, trend_bull, trend_bear)
    results_stress['M15_wide'] = run_backtest(m5_stress, m15_s_proba, m15_s_feat.index, m15_risk_wide, trend_bull, trend_bear)
    results_stress['H1_hold'] = run_backtest(m5_stress, h1_s_proba, h1_s_feat.index, h1_risk_hold, trend_bull, trend_bear)
    results_stress['H1_wide'] = run_backtest(m5_stress, h1_s_proba, h1_s_feat.index, h1_risk_wide, trend_bull, trend_bear)

    print(f"\n  {'Strategy':<18} {'Trades':<8} {'WR%':<7} {'PF':<6} {'Return%':<10} {'MaxDD%':<8} {'Exits':<25} {'Status'}")
    print(f"  {'-'*90}")
    for name, r in results_stress.items():
        if r['total_trades'] > 0:
            exits = r.get('exit_reasons', {})
            exit_str = f"s:{exits.get('stop',0)} tp:{exits.get('tp',0)} t:{exits.get('timeout',0)}"
            status = "BREACH" if r['breached'] else "OK"
            print(f"  {name:<18} {r['total_trades']:<8} {r['win_rate']:<7.1f} {r['profit_factor']:<6.2f} {r['return_pct']:<+10.1f} {r['max_drawdown_pct']:<8.1f} {exit_str:<25} {status}")

    # 2020 crash months
    print("\n  2020 CRASH (Mar-Apr):")
    for name, r in results_stress.items():
        crash_pnl = 0
        crash_trades = 0
        for month in ['2020-03', '2020-04']:
            if month in r['monthly']:
                crash_pnl += r['monthly'][month]['pnl']
                crash_trades += r['monthly'][month]['trades']
        if crash_trades > 0:
            print(f"    {name:<18} Trades={crash_trades:<5} PnL=${crash_pnl:+,.0f}")

    # ============================================================
    # FINAL SUMMARY
    # ============================================================
    print("\n" + "=" * 80)
    print("FINAL SUMMARY — PROPER RISK PER MODEL")
    print("=" * 80)

    print(f"\n  {'Model':<18} {'AUC':<7} {'OOS Ret%':<10} {'OOS DD%':<9} {'Stress Ret%':<12} {'Stress DD%':<11} {'Deploy?'}")
    print(f"  {'-'*78}")
    for name in ['M5_momentum', 'M15_hold', 'M15_wide', 'H1_hold', 'H1_wide']:
        auc = {'M5_momentum': m5_auc, 'M15_hold': m15_auc, 'M15_wide': m15_auc, 'H1_hold': h1_auc, 'H1_wide': h1_auc}[name]
        oos = results_oos[name]
        stress = results_stress[name]
        deploy = "YES" if (oos['return_pct'] > 0 and not oos['breached'] and stress['return_pct'] > 0) else "NO"
        print(f"  {name:<18} {auc:<7.4f} {oos['return_pct']:<+10.1f} {oos['max_drawdown_pct']:<9.1f} {stress['return_pct']:<+12.1f} {stress['max_drawdown_pct']:<11.1f} {deploy}")

    # Save
    save_data = {
        'timestamp': datetime.now().isoformat(),
        'aucs': {'M5': m5_auc, 'M15': m15_auc, 'H1': h1_auc},
        'risk_profiles': {
            'M5': m5_risk, 'M15_hold': m15_risk_hold, 'M15_wide': m15_risk_wide,
            'H1_hold': h1_risk_hold, 'H1_wide': h1_risk_wide,
        },
        'oos_results': {k: {kk: vv for kk, vv in v.items() if kk != 'monthly'} for k, v in results_oos.items()},
        'stress_results': {k: {kk: vv for kk, vv in v.items() if kk != 'monthly'} for k, v in results_stress.items()},
    }
    output_path = OUTPUT_DIR / "proper_risk_results.json"
    with open(output_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Saved: {output_path}")
    print(f"  Time: {(datetime.now() - start).total_seconds():.0f}s")


if __name__ == "__main__":
    main()
