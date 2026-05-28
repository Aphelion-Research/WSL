"""
Walk-Forward Validation — Hold-to-Horizon Execution
====================================================
Fixes execution mismatch. Model predicts mean reversion, execution holds to horizon.
No directional stops/TPs - just hold 12 bars (1 hour) and exit.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from pathlib import Path
from datetime import datetime

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_M5.json")
OUTPUT_DIR = Path("output_him_v2/walk_forward_hold_horizon")
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


def hold_horizon_backtest(m5_data, proba, signal_times, config, trend_bull, trend_bear):
    """Hold-to-horizon execution matching detrended labels.

    Model predicts: will next 12 bars beat trailing average?
    Execution: hold exactly 12 bars, catastrophic stop only (10 ATR).
    """
    threshold = config['threshold']
    hold_bars = 12  # match label horizon
    leverage = 50
    initial_capital = 10000.0
    breach_threshold = 9000.0

    equity = initial_capital
    close = m5_data['close'].values
    high_arr = m5_data['high'].values
    low_arr = m5_data['low'].values
    dates = m5_data.index

    # ATR for catastrophic stop only
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

        # Signal direction from model
        if p > threshold:
            signal = 1
        elif p < (1 - threshold):
            signal = -1
        else:
            continue

        m5_idx = dates.searchsorted(sig_time)
        if m5_idx >= len(close) - hold_bars or m5_idx <= blocked_until_idx:
            continue

        # Trend filter
        if signal == 1 and not bull_m5[m5_idx]:
            continue
        if signal == -1 and not bear_m5[m5_idx]:
            continue

        if np.isnan(atr[m5_idx]) or atr[m5_idx] <= 0:
            continue

        entry_price = close[m5_idx]
        oz_per_lot = 100

        # Fixed position size (1% risk on catastrophic 10 ATR move)
        catastrophic_stop = atr[m5_idx] * 10.0
        risk_amount = equity * 0.01
        lots = risk_amount / (catastrophic_stop * oz_per_lot)
        max_lots = (equity * leverage) / (entry_price * oz_per_lot)
        lots = min(lots, max_lots)
        if lots <= 0:
            continue

        # Catastrophic stop only (10 ATR)
        if signal == 1:
            cata_stop = entry_price - catastrophic_stop
        else:
            cata_stop = entry_price + catastrophic_stop

        # Hold to horizon (12 bars) or hit catastrophic stop
        exit_price = None
        exit_bar = m5_idx + hold_bars

        for j in range(m5_idx + 1, exit_bar + 1):
            # Check catastrophic stop
            if signal == 1 and low_arr[j] <= cata_stop:
                exit_price = cata_stop
                exit_bar = j
                break
            elif signal == -1 and high_arr[j] >= cata_stop:
                exit_price = cata_stop
                exit_bar = j
                break

        # If no catastrophic stop hit, exit at horizon
        if exit_price is None:
            exit_price = close[exit_bar]

        # Calculate PnL
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
        'final_equity': equity
    }


def main():
    start = datetime.now()
    print(f"WALK-FORWARD — HOLD-TO-HORIZON EXECUTION — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print("FIX: Model predicts mean reversion → execution holds to horizon")
    print("     No directional stops/TPs, just hold 12 bars + catastrophic stop")
    print("=" * 80)

    print("\n[1/5] Loading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']

    period2_start = '2025-01-01'
    period2_end = '2025-12-31'
    period3_start = '2026-01-01'

    m5_period2 = m5[(m5.index >= period2_start) & (m5.index <= period2_end)]
    m5_period3 = m5[m5.index >= period3_start]

    print(f"  Period 2 (Optimize): {len(m5_period2):,} bars")
    print(f"  Period 3 (Validate): {len(m5_period3):,} bars")

    print("\n[2/5] Loading model + features...")
    m5_model = xgb.Booster()
    m5_model.load_model(str(MODEL_PATH))
    m5_features = build_m5_features(m5)
    feat_cols = list(m5_features.columns)
    print(f"  Features: {len(feat_cols)}")

    print("\n[3/5] Trend filter...")
    daily_close = m5['close'].resample('1D').last().dropna()
    d_sma50 = daily_close.rolling(50).mean()
    d_sma100 = daily_close.rolling(100).mean()
    trend_bull = ((daily_close > d_sma50) & (daily_close > d_sma100)).shift(2)
    trend_bear = ((daily_close < d_sma50) & (daily_close < d_sma100)).shift(2)

    print("\n[4/5] PERIOD 2 OPTIMIZATION (2025)...")
    m5_p2_feat = m5_features[(m5_features.index >= period2_start) & (m5_features.index <= period2_end)].dropna()
    m5_p2_proba = m5_model.predict(xgb.DMatrix(m5_p2_feat[feat_cols].values, feature_names=feat_cols))

    # Test only thresholds (hold_bars fixed at 12 to match label)
    thresholds = [0.50, 0.52, 0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.70, 0.72, 0.75]

    results_p2 = []
    for thresh in thresholds:
        cfg = {'threshold': thresh}
        r = hold_horizon_backtest(m5_period2, m5_p2_proba, m5_p2_feat.index, cfg, trend_bull, trend_bear)
        if r:
            results_p2.append({**cfg, **r})

    if not results_p2:
        print("\n  NO PROFITABLE CONFIGS")
        return

    results_p2.sort(key=lambda x: -x['return_pct'])

    print("\n" + "=" * 80)
    print("PERIOD 2 (2025) — ALL CONFIGS")
    print("=" * 80)
    print(f"  {'Rank':<5} {'Thresh':<8} {'Ret%':<10} {'Trades':<7} {'WR%':<6} {'PF':<6} {'DD%':<7}")
    print(f"  {'-'*60}")
    for i, r in enumerate(results_p2, 1):
        print(f"  {i:<5} {r['threshold']:<8.2f} {r['return_pct']:<+10.1f} {r['trades']:<7} {r['win_rate']:<6.1f} {r['profit_factor']:<6.2f} {r['max_dd']:<7.1f}")

    best_p2 = results_p2[0]
    locked_config = {'threshold': best_p2['threshold']}

    print("\n" + "=" * 80)
    print("LOCKED CONFIG")
    print("=" * 80)
    print(f"  Threshold: {locked_config['threshold']}")
    print(f"  Hold: 12 bars (60 min, matches label horizon)")
    print(f"  Stop: 10 ATR catastrophic only")
    print(f"  TP: none (hold to horizon)")
    print(f"\n  Period 2: {best_p2['return_pct']:+.1f}%, WR {best_p2['win_rate']:.1f}%, PF {best_p2['profit_factor']:.2f}")

    print("\n[5/5] PERIOD 3 VALIDATION (2026)...")
    m5_p3_feat = m5_features[m5_features.index >= period3_start].dropna()
    m5_p3_proba = m5_model.predict(xgb.DMatrix(m5_p3_feat[feat_cols].values, feature_names=feat_cols))

    r_p3 = hold_horizon_backtest(m5_period3, m5_p3_proba, m5_p3_feat.index, locked_config, trend_bull, trend_bear)

    if not r_p3:
        print("\n  VALIDATION FAILED")
        print("\n" + "=" * 80)
        print("VERDICT: ✗ REJECT — Still breached on 2026")
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

    return_ratio = p3_annual / p2_annual if p2_annual > 0 else 0
    degradation = p2_annual - p3_annual

    print("\n" + "=" * 80)
    print("WALK-FORWARD ANALYSIS")
    print("=" * 80)
    print(f"  Period 2 (2025): {p2_annual:+.1f}% annual")
    print(f"  Period 3 (2026): {p3_annual:+.1f}% annual")
    print(f"  Degradation: {degradation:+.1f}%")
    print(f"  Return Ratio: {return_ratio:.3f}")

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
        print(f"\n  {verdict}: {p3_annual:+.1f}% annualized, minimal overfitting")
    elif p3_annual > 100 and return_ratio > 0.70:
        verdict = "⚠ CAUTION"
        print(f"\n  {verdict}: {p3_annual:+.1f}% annualized, moderate degradation")
    else:
        verdict = "✗ REJECT"
        print(f"\n  {verdict}: {p3_annual:+.1f}% annualized, insufficient edge")

    print(f"\n  Expected monthly: {p3_annual/12:+.1f}%")
    print(f"  Conservative estimate: {p3_annual:+.1f}% annual")

    # Save
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'execution': 'hold_to_horizon',
        'hold_bars': 12,
        'locked_config': locked_config,
        'period2': {'return_pct': best_p2['return_pct'], 'annualized': p2_annual, 'trades': best_p2['trades'], 'win_rate': best_p2['win_rate'], 'pf': best_p2['profit_factor']},
        'period3': {'return_pct': r_p3['return_pct'], 'annualized': p3_annual, 'trades': r_p3['trades'], 'win_rate': r_p3['win_rate'], 'pf': r_p3['profit_factor']},
        'overfitting': {'return_ratio': return_ratio, 'degradation': degradation},
        'verdict': verdict
    }
    with open(OUTPUT_DIR / "walk_forward_analysis.json", 'w') as f:
        json.dump(analysis, f, indent=2)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n  Time: {elapsed:.0f}s")
    print(f"  Files: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
