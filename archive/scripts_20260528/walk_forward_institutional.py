"""
Walk-Forward Validation — Institutional Grid
=============================================
Tests selection bias by optimizing on 2025, validating on 2026.
Uses same grid as institutional optimization (1,680 configs).
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from pathlib import Path
from datetime import datetime
from itertools import product

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_M5.json")
OUTPUT_DIR = Path("output_him_v2/walk_forward_institutional")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

EMA_PERIODS = [9, 21, 50, 100, 150, 200, 300, 500, 800, 1000]


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


def build_m5_features(m5):
    close, high, low, volume = m5['close'], m5['high'], m5['low'], m5['tick_volume']
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
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_24 = tr.rolling(24).mean()
    f_spec['atr_2h_pct'] = atr_24 / close
    f_spec['vol_ratio_short_long'] = tr.rolling(12).mean() / atr_24.replace(0, np.nan)
    hour = m5.index.hour + m5.index.minute / 60
    f_spec['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f_spec['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f_spec['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)
    return pd.concat([f_ema, f_vwap, f_spec], axis=1)


def fast_backtest(m5_data, proba, signal_times, config, trend_bull, trend_bear):
    threshold = config['threshold']
    risk_pct = config['risk_pct']
    stop_mult = config['stop_mult']
    tp_mult = config['tp_mult']
    holding_bars = config['holding_bars']
    leverage = 50
    initial_capital = 10000.0
    breach_threshold = 9000.0
    equity = initial_capital
    close = m5_data['close'].values
    high_arr = m5_data['high'].values
    low_arr = m5_data['low'].values
    dates = m5_data.index
    tr = np.maximum(high_arr - low_arr, np.maximum(np.abs(high_arr - np.roll(close, 1)), np.abs(low_arr - np.roll(close, 1))))
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
        stop_distance = atr[m5_idx] * stop_mult
        risk_amount = equity * risk_pct
        lots = risk_amount / (stop_distance * oz_per_lot)
        max_lots = (equity * leverage) / (entry_price * oz_per_lot)
        lots = min(lots, max_lots)
        if lots <= 0:
            continue
        if signal == 1:
            stop_price = entry_price - stop_distance
            tp_price = entry_price + atr[m5_idx] * tp_mult
        else:
            stop_price = entry_price + stop_distance
            tp_price = entry_price - atr[m5_idx] * tp_mult
        exit_price = None
        exit_bar = m5_idx
        end_bar = min(m5_idx + holding_bars, len(close) - 1)
        for j in range(m5_idx + 1, end_bar + 1):
            if signal == 1:
                if low_arr[j] <= stop_price:
                    exit_price = stop_price
                    exit_bar = j
                    break
                if high_arr[j] >= tp_price:
                    exit_price = tp_price
                    exit_bar = j
                    break
            else:
                if high_arr[j] >= stop_price:
                    exit_price = stop_price
                    exit_bar = j
                    break
                if low_arr[j] <= tp_price:
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
    return {'return_pct': return_pct, 'trades': trades, 'win_rate': win_rate, 'profit_factor': pf, 'max_dd': max_dd, 'final_equity': equity}


def main():
    start = datetime.now()
    print(f"WALK-FORWARD VALIDATION (INSTITUTIONAL GRID) — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("Period 1 (Train): 2015-2024")
    print("Period 2 (Optimize): 2025")
    print("Period 3 (Validate): 2026")
    print("=" * 80)

    print("\n[1/7] Loading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']

    period1_end = '2024-12-31'
    period2_start = '2025-01-01'
    period2_end = '2025-12-31'
    period3_start = '2026-01-01'

    m5_period1 = m5[m5.index <= period1_end]
    m5_period2 = m5[(m5.index >= period2_start) & (m5.index <= period2_end)]
    m5_period3 = m5[m5.index >= period3_start]

    print(f"  Period 1 (Train): 2015-01-01 to 2024-12-31 → {len(m5_period1):,} bars")
    print(f"  Period 2 (Optimize): 2025-01-01 to 2025-12-31 → {len(m5_period2):,} bars")
    print(f"  Period 3 (Validate): 2026-01-01 to 2026-05-27 → {len(m5_period3):,} bars")

    print("\n[2/7] Verifying model...")
    m5_model = xgb.Booster()
    m5_model.load_model(str(MODEL_PATH))
    print(f"  Model: {MODEL_PATH.name}")
    print(f"  Training: 2015-2024 (assumed)")

    print("\n[3/7] Building features...")
    m5_features = build_m5_features(m5)
    feat_cols = list(m5_features.columns)
    print(f"  Features: {len(feat_cols)}")

    print("\n[4/7] Trend filter...")
    daily_close = m5['close'].resample('1D').last().dropna()
    d_sma50 = daily_close.rolling(50).mean()
    d_sma100 = daily_close.rolling(100).mean()
    trend_bull = ((daily_close > d_sma50) & (daily_close > d_sma100)).shift(2)
    trend_bear = ((daily_close < d_sma50) & (daily_close < d_sma100)).shift(2)

    print("\n[5/7] PERIOD 2 OPTIMIZATION (2025)...")
    m5_p2_feat = m5_features[(m5_features.index >= period2_start) & (m5_features.index <= period2_end)].dropna()
    m5_p2_proba = m5_model.predict(xgb.DMatrix(m5_p2_feat[feat_cols].values, feature_names=feat_cols))
    print(f"  Signals: {len(m5_p2_proba):,}")
    print(f"  Proba: mean={m5_p2_proba.mean():.3f}, std={m5_p2_proba.std():.3f}")

    # Institutional grid (1,680 configs)
    thresholds = [0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.70]
    risk_pcts = [0.01]
    stop_mults = [1.0, 1.2, 1.5, 1.8, 2.0, 2.5]
    tp_mults = [2.0, 2.5, 3.0, 3.5, 4.0]
    holding_bars = [8, 10, 12, 14, 16, 20, 24, 30]

    configs = []
    for thresh, risk, stop, tp, hold in product(thresholds, risk_pcts, stop_mults, tp_mults, holding_bars):
        configs.append({'threshold': thresh, 'risk_pct': risk, 'stop_mult': stop, 'tp_mult': tp, 'holding_bars': hold})

    print(f"  Configs: {len(configs):,}")

    results_p2 = []
    for i, cfg in enumerate(configs):
        if i % 200 == 0 and i > 0:
            print(f"    {i}/{len(configs)} ({i/len(configs)*100:.0f}%)")
        r = fast_backtest(m5_period2, m5_p2_proba, m5_p2_feat.index, cfg, trend_bull, trend_bear)
        if r:
            results_p2.append({**cfg, **r})

    print(f"  Valid: {len(results_p2):,} / {len(configs):,}")

    if not results_p2:
        print("\n  NO PROFITABLE CONFIGS")
        return

    results_p2.sort(key=lambda x: -x['return_pct'])

    print("\n" + "=" * 80)
    print("PERIOD 2 (2025) — TOP 10")
    print("=" * 80)
    print(f"  {'Rank':<5} {'Ret%':<8} {'Trades':<7} {'WR%':<6} {'PF':<6} {'DD%':<7} {'Thresh':<7} {'Hold':<6} {'Stop':<6} {'TP':<6}")
    print(f"  {'-'*80}")
    for i, r in enumerate(results_p2[:10], 1):
        print(f"  {i:<5} {r['return_pct']:<+8.1f} {r['trades']:<7} {r['win_rate']:<6.1f} {r['profit_factor']:<6.2f} {r['max_dd']:<7.1f} {r['threshold']:<7.2f} {r['holding_bars']:<6} {r['stop_mult']:<6.1f} {r['tp_mult']:<6.1f}")

    best_p2 = results_p2[0]
    locked_config = {k: best_p2[k] for k in ['threshold', 'risk_pct', 'stop_mult', 'tp_mult', 'holding_bars']}

    print("\n" + "=" * 80)
    print("LOCKED CONFIG")
    print("=" * 80)
    print(f"  Threshold: {locked_config['threshold']}")
    print(f"  Holding: {locked_config['holding_bars']} bars")
    print(f"  Stop: {locked_config['stop_mult']:.1f} ATR")
    print(f"  TP: {locked_config['tp_mult']:.1f} ATR")
    print(f"\n  Period 2: {best_p2['return_pct']:+.1f}%, WR {best_p2['win_rate']:.1f}%, PF {best_p2['profit_factor']:.2f}")

    print("\n[6/7] PERIOD 3 VALIDATION (2026)...")
    m5_p3_feat = m5_features[m5_features.index >= period3_start].dropna()
    m5_p3_proba = m5_model.predict(xgb.DMatrix(m5_p3_feat[feat_cols].values, feature_names=feat_cols))
    print(f"  Signals: {len(m5_p3_proba):,}")

    r_p3 = fast_backtest(m5_period3, m5_p3_proba, m5_p3_feat.index, locked_config, trend_bull, trend_bear)

    if not r_p3:
        print("\n  VALIDATION FAILED: breach or no trades")
        print("\n" + "=" * 80)
        print("VERDICT: ✗ REJECT — Config failed on 2026 (breached or no edge)")
        print("=" * 80)
        return

    p3_annual = r_p3['return_pct'] * (12 / 5)
    p2_annual = best_p2['return_pct']

    print("\n" + "=" * 80)
    print("PERIOD 3 (2026) VALIDATION")
    print("=" * 80)
    print(f"  Return: {r_p3['return_pct']:+.1f}% (5mo) → {p3_annual:+.1f}% annualized")
    print(f"  Trades: {r_p3['trades']}")
    print(f"  Win Rate: {r_p3['win_rate']:.1f}%")
    print(f"  PF: {r_p3['profit_factor']:.2f}")
    print(f"  Max DD: {r_p3['max_dd']:.1f}%")

    print("\n[7/7] OVERFITTING ANALYSIS...")
    return_ratio = p3_annual / p2_annual if p2_annual > 0 else 0
    degradation = p2_annual - p3_annual
    wr_change = r_p3['win_rate'] - best_p2['win_rate']

    print("\n" + "=" * 80)
    print("WALK-FORWARD ANALYSIS")
    print("=" * 80)
    print(f"  {'Metric':<20} │ {'Period 2':<15} │ {'Period 3':<15} │ {'Change':<10}")
    print(f"  {'-'*65}")
    print(f"  {'Return % (ann.)':<20} │ {p2_annual:<+15.1f} │ {p3_annual:<+15.1f} │ {degradation:<+10.1f}")
    print(f"  {'Max DD %':<20} │ {best_p2['max_dd']:<15.1f} │ {r_p3['max_dd']:<15.1f} │ {r_p3['max_dd']-best_p2['max_dd']:<+10.1f}")
    print(f"  {'Win Rate %':<20} │ {best_p2['win_rate']:<15.1f} │ {r_p3['win_rate']:<15.1f} │ {wr_change:<+10.1f}")
    print(f"  {'Profit Factor':<20} │ {best_p2['profit_factor']:<15.2f} │ {r_p3['profit_factor']:<15.2f} │ {r_p3['profit_factor']-best_p2['profit_factor']:<+10.2f}")

    print(f"\n  Return Ratio: {return_ratio:.3f}")
    if return_ratio > 0.95:
        print(f"    → Minimal overfitting")
    elif return_ratio > 0.85:
        print(f"    → Moderate overfitting (acceptable)")
    else:
        print(f"    → Significant overfitting")

    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    if p3_annual > 200 and return_ratio > 0.85:
        verdict = "✓ DEPLOY"
        print(f"\n  {verdict}: Period 3 {p3_annual:+.1f}% annualized, minimal overfitting")
    elif p3_annual > 100 and return_ratio > 0.70:
        verdict = "⚠ CAUTION"
        print(f"\n  {verdict}: Period 3 {p3_annual:+.1f}% annualized, moderate degradation")
    else:
        verdict = "✗ REJECT"
        print(f"\n  {verdict}: Period 3 {p3_annual:+.1f}% annualized, significant overfitting")

    print(f"\n  Conservative: {p3_annual:+.1f}% annual")
    print(f"  Expected: {(p2_annual + p3_annual)/2:+.1f}% annual")
    print(f"  Monthly: {p3_annual/12:+.1f}%")

    # Save outputs
    df_p2 = pd.DataFrame(results_p2)
    df_p2.to_csv(OUTPUT_DIR / "period2_optimization_results.csv", index=False)

    df_p3 = pd.DataFrame([{**locked_config, **r_p3, 'annualized_return': p3_annual}])
    df_p3.to_csv(OUTPUT_DIR / "period3_validation_results.csv", index=False)

    analysis = {
        'timestamp': datetime.now().isoformat(),
        'locked_config': locked_config,
        'period2': {'return_pct': best_p2['return_pct'], 'annualized': p2_annual, 'trades': best_p2['trades'], 'win_rate': best_p2['win_rate'], 'pf': best_p2['profit_factor'], 'max_dd': best_p2['max_dd']},
        'period3': {'return_pct': r_p3['return_pct'], 'annualized': p3_annual, 'trades': r_p3['trades'], 'win_rate': r_p3['win_rate'], 'pf': r_p3['profit_factor'], 'max_dd': r_p3['max_dd']},
        'overfitting': {'return_ratio': return_ratio, 'degradation': degradation, 'wr_change': wr_change},
        'verdict': verdict
    }
    with open(OUTPUT_DIR / "walk_forward_analysis.json", 'w') as f:
        json.dump(analysis, f, indent=2)

    with open(OUTPUT_DIR / "final_verdict.txt", 'w') as f:
        f.write(f"WALK-FORWARD VALIDATION\n{'='*80}\n\n")
        f.write(f"LOCKED CONFIG:\n")
        f.write(f"  Threshold: {locked_config['threshold']}\n")
        f.write(f"  Holding: {locked_config['holding_bars']} bars\n")
        f.write(f"  Stop: {locked_config['stop_mult']} ATR\n")
        f.write(f"  TP: {locked_config['tp_mult']} ATR\n\n")
        f.write(f"PERFORMANCE:\n")
        f.write(f"  Period 2 (2025): {p2_annual:+.1f}% annual\n")
        f.write(f"  Period 3 (2026): {p3_annual:+.1f}% annual\n")
        f.write(f"  Degradation: {degradation:+.1f}%\n\n")
        f.write(f"VERDICT: {verdict}\n")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n  Time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"  Files: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
