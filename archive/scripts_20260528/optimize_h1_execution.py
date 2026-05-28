"""
H1 Execution Optimization — Brute Force Search
===============================================
Test 1000+ execution configs to find ANY profitable setup for H1 model.
WARNING: This is optimization on OOS — results will be overfit.
But we need to know if H1 CAN be profitable with the right execution.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
import warnings
from pathlib import Path
from datetime import datetime
from itertools import product

warnings.filterwarnings('ignore')

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_H1.json")
OUTPUT_DIR = Path("output_him_v2")
OUTPUT_DIR.mkdir(exist_ok=True)

EMA_PERIODS = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]


# ============================================================
# FEATURE BUILDER (same as training)
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


def build_h1_features(h1):
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
    return pd.concat([f_ema, f_vwap, f_spec], axis=1)


# ============================================================
# FAST BACKTEST ENGINE
# ============================================================

def fast_backtest(m5_data, proba, signal_times, config, trend_bull, trend_bear):
    """Stripped-down backtest for speed."""
    threshold = config['threshold']
    risk_pct = config['risk_pct']
    stop_mult = config['stop_mult']
    tp_mult = config['tp_mult']
    holding_bars = config['holding_bars']
    use_stop = config['use_stop']
    use_tp = config['use_tp']

    leverage = 50
    initial_capital = 10000.0
    breach_threshold = 9000.0

    equity = initial_capital
    close = m5_data['close'].values
    high_arr = m5_data['high'].values
    low_arr = m5_data['low'].values
    dates = m5_data.index

    tr = np.maximum(high_arr - low_arr, np.maximum(
        np.abs(high_arr - np.roll(close, 1)),
        np.abs(low_arr - np.roll(close, 1))))
    tr[0] = high_arr[0] - low_arr[0]
    atr = pd.Series(tr, index=dates).rolling(12).mean().values

    bull_m5 = trend_bull.reindex(dates, method='ffill').fillna(False).values
    bear_m5 = trend_bear.reindex(dates, method='ffill').fillna(False).values

    trades = 0
    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0
    max_dd = 0.0
    peak = initial_capital
    blocked_until_idx = -1

    for sig_time, p in zip(signal_times, proba):
        if equity <= breach_threshold:
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

        if np.isnan(atr[m5_idx]) or atr[m5_idx] <= 0:
            continue

        entry_price = close[m5_idx]
        oz_per_lot = 100

        if use_stop:
            stop_distance = atr[m5_idx] * stop_mult
        else:
            stop_distance = atr[m5_idx] * 10.0  # catastrophic only

        risk_amount = equity * risk_pct
        lots = risk_amount / (stop_distance * oz_per_lot)
        max_lots = (equity * leverage) / (entry_price * oz_per_lot)
        lots = min(lots, max_lots)
        if lots <= 0:
            continue

        if signal == 1:
            stop_price = entry_price - stop_distance
            tp_price = entry_price + atr[m5_idx] * tp_mult if use_tp else None
        else:
            stop_price = entry_price + stop_distance
            tp_price = entry_price - atr[m5_idx] * tp_mult if use_tp else None

        exit_price = None
        exit_bar = m5_idx
        end_bar = min(m5_idx + holding_bars, len(close) - 1)

        for j in range(m5_idx + 1, end_bar + 1):
            if signal == 1:
                if low_arr[j] <= stop_price:
                    exit_price = stop_price
                    exit_bar = j
                    break
                if tp_price and high_arr[j] >= tp_price:
                    exit_price = tp_price
                    exit_bar = j
                    break
            else:
                if high_arr[j] >= stop_price:
                    exit_price = stop_price
                    exit_bar = j
                    break
                if tp_price and low_arr[j] <= tp_price:
                    exit_price = tp_price
                    exit_bar = j
                    break

        if exit_price is None:
            exit_bar = end_bar
            exit_price = close[exit_bar]

        if signal == 1:
            pnl = (exit_price - entry_price) * lots * oz_per_lot
        else:
            pnl = (entry_price - exit_price) * lots * oz_per_lot

        equity += pnl
        peak = max(peak, equity)
        dd = (equity - peak) / peak * 100
        max_dd = min(max_dd, dd)

        trades += 1
        if pnl > 0:
            wins += 1
            gross_profit += pnl
        else:
            gross_loss += abs(pnl)

        blocked_until_idx = exit_bar

    if trades == 0:
        return None

    if equity <= breach_threshold:
        return None

    return_pct = (equity - initial_capital) / initial_capital * 100
    win_rate = wins / trades * 100
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    return {
        'return_pct': return_pct,
        'trades': trades,
        'win_rate': win_rate,
        'profit_factor': pf,
        'max_dd': max_dd,
        'final_equity': equity,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    start = datetime.now()
    print(f"H1 EXECUTION OPTIMIZATION — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("Brute-force search: 1000+ configs")
    print("WARNING: Optimizing on OOS = overfitting. For research only.")
    print("=" * 80)

    # Load
    print("\nLoading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']

    h1 = m5.resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'tick_volume': 'sum', 'spread': 'mean',
    }).dropna(subset=['close'])
    h1 = h1[h1['tick_volume'] > 0]

    # Features
    print("Building H1 features...")
    h1_features = build_h1_features(h1)
    h1_feat_cols = list(h1_features.columns)

    # Trend filter
    daily_close = m5['close'].resample('1D').last().dropna()
    d_sma50 = daily_close.rolling(50).mean()
    d_sma100 = daily_close.rolling(100).mean()
    trend_bull = ((daily_close > d_sma50) & (daily_close > d_sma100)).shift(2)
    trend_bear = ((daily_close < d_sma50) & (daily_close < d_sma100)).shift(2)

    # Load model + predict OOS
    print("Loading H1 model + generating predictions...")
    h1_model = xgb.Booster()
    h1_model.load_model(str(MODEL_PATH))

    h1_oos = h1[h1.index >= '2025-01-01']
    h1_oos_feat = h1_features[h1_features.index >= '2025-01-01'].dropna()
    h1_proba = h1_model.predict(xgb.DMatrix(h1_oos_feat[h1_feat_cols].values, feature_names=h1_feat_cols))

    m5_oos = m5[m5.index >= '2025-01-01']

    print(f"  H1 OOS signals: {len(h1_proba):,} bars")
    print(f"  Proba dist: mean={h1_proba.mean():.3f}, std={h1_proba.std():.3f}")
    print(f"    >0.60: {(h1_proba>0.60).sum()} | >0.65: {(h1_proba>0.65).sum()} | >0.70: {(h1_proba>0.70).sum()}")

    # ============================================================
    # GRID SEARCH
    # ============================================================
    print("\n" + "=" * 80)
    print("GRID SEARCH (1000+ configs)")
    print("=" * 80)

    thresholds = [0.50, 0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.70]
    risk_pcts = [0.005, 0.0075, 0.01, 0.0125, 0.015]
    stop_mults = [0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 7.0]  # 0 = no stop (catastrophic only)
    tp_mults = [0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]  # 0 = no TP
    holding_bars = [24, 36, 48, 60, 72, 96]  # M5 bars = 2-8 hours

    configs = []
    for thresh, risk, stop, tp, hold in product(thresholds, risk_pcts, stop_mults, tp_mults, holding_bars):
        configs.append({
            'threshold': thresh,
            'risk_pct': risk,
            'stop_mult': stop,
            'tp_mult': tp,
            'holding_bars': hold,
            'use_stop': stop > 0,
            'use_tp': tp > 0,
        })

    print(f"\n  Total configs: {len(configs):,}")
    print(f"  Running backtests...")

    results = []
    for i, cfg in enumerate(configs):
        if i % 500 == 0 and i > 0:
            print(f"    Progress: {i}/{len(configs)} ({i/len(configs)*100:.0f}%)")

        r = fast_backtest(m5_oos, h1_proba, h1_oos_feat.index, cfg, trend_bull, trend_bear)
        if r:
            results.append({**cfg, **r})

    print(f"\n  Valid results: {len(results):,} / {len(configs):,}")

    if not results:
        print("\n  NO PROFITABLE CONFIGS FOUND")
        return

    # Sort by return
    results.sort(key=lambda x: -x['return_pct'])

    print("\n" + "=" * 80)
    print("TOP 20 CONFIGS (by return %)")
    print("=" * 80)

    print(f"\n  {'Rank':<5} {'Ret%':<8} {'Trades':<7} {'WR%':<6} {'PF':<6} {'DD%':<7} {'Thresh':<7} {'Risk%':<7} {'Stop':<6} {'TP':<6} {'Hold':<5}")
    print(f"  {'-'*85}")

    for i, r in enumerate(results[:20], 1):
        stop_str = f"{r['stop_mult']:.1f}" if r['use_stop'] else "none"
        tp_str = f"{r['tp_mult']:.1f}" if r['use_tp'] else "none"
        print(f"  {i:<5} {r['return_pct']:<+8.1f} {r['trades']:<7} {r['win_rate']:<6.1f} {r['profit_factor']:<6.2f} {r['max_dd']:<7.1f} {r['threshold']:<7.2f} {r['risk_pct']*100:<7.2f} {stop_str:<6} {tp_str:<6} {r['holding_bars']:<5}")

    # Best config
    best = results[0]
    print("\n" + "=" * 80)
    print("BEST CONFIG DETAIL")
    print("=" * 80)
    print(f"\n  Threshold:    {best['threshold']}")
    print(f"  Risk/trade:   {best['risk_pct']*100:.2f}%")
    print(f"  Stop:         {best['stop_mult']:.1f} ATR" if best['use_stop'] else "  Stop:         catastrophic only")
    print(f"  TP:           {best['tp_mult']:.1f} ATR" if best['use_tp'] else "  TP:           hold to horizon")
    print(f"  Hold bars:    {best['holding_bars']} M5 = {best['holding_bars']/12:.1f} hours")
    print(f"\n  Return:       {best['return_pct']:+.1f}%")
    print(f"  Trades:       {best['trades']}")
    print(f"  Win rate:     {best['win_rate']:.1f}%")
    print(f"  Profit factor: {best['profit_factor']:.2f}")
    print(f"  Max DD:       {best['max_dd']:.1f}%")
    print(f"  Final equity: ${best['final_equity']:,.0f}")

    # Save top 100
    save_data = {
        'timestamp': datetime.now().isoformat(),
        'oos_period': '2025-01-01 to 2026-05-20',
        'total_configs': len(configs),
        'valid_results': len(results),
        'top_100': results[:100],
        'best': best,
    }

    output_path = OUTPUT_DIR / "h1_optimization_results.json"
    with open(output_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Saved top 100: {output_path}")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"  Time: {elapsed:.0f}s")

    # Pattern analysis
    print("\n" + "=" * 80)
    print("PATTERN ANALYSIS (Top 100)")
    print("=" * 80)

    top100 = results[:100]
    avg_thresh = np.mean([r['threshold'] for r in top100])
    avg_risk = np.mean([r['risk_pct'] for r in top100])
    avg_stop = np.mean([r['stop_mult'] for r in top100 if r['use_stop']])
    avg_tp = np.mean([r['tp_mult'] for r in top100 if r['use_tp']])
    avg_hold = np.mean([r['holding_bars'] for r in top100])
    pct_no_stop = sum(1 for r in top100 if not r['use_stop']) / 100 * 100
    pct_no_tp = sum(1 for r in top100 if not r['use_tp']) / 100 * 100

    print(f"\n  Avg threshold:   {avg_thresh:.3f}")
    print(f"  Avg risk/trade:  {avg_risk*100:.2f}%")
    print(f"  Avg stop:        {avg_stop:.2f} ATR ({pct_no_stop:.0f}% use catastrophic only)")
    print(f"  Avg TP:          {avg_tp:.2f} ATR ({pct_no_tp:.0f}% hold to horizon)")
    print(f"  Avg hold:        {avg_hold:.0f} M5 bars = {avg_hold/12:.1f}h")


if __name__ == "__main__":
    main()
