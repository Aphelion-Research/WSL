"""
Walk-Forward Validation — Him V2 MultiScale — REAL RESULTS
===========================================================
No bullshit. Proper split, hold-to-horizon, minimal grid.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from pathlib import Path
from datetime import datetime

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_V2_MultiScale.json")
OUTPUT_DIR = Path("output_him_v2/walk_forward_multiscale")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)


def build_multiscale_features(m5):
    """Build multi-timeframe features for Him V2 MultiScale."""
    close = m5['close']
    high = m5['high']
    low = m5['low']
    volume = m5['tick_volume']
    spread = m5['spread']

    f = pd.DataFrame(index=m5.index)

    # Multi-scale returns
    for bars in [1, 4, 8, 16, 32, 64, 96]:
        f[f'ret_{bars}bar'] = close.pct_change(bars)

    # Range position (multiple horizons)
    for bars, suffix in [(72, '6h'), (144, '12h'), (288, '24h')]:
        rh = close.rolling(bars).max()
        rl = close.rolling(bars).min()
        rng = (rh - rl).replace(0, np.nan)
        f[f'range_pos_{suffix}'] = (close - rl) / rng

    # VWAP deviation (multiple horizons)
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        tp = (high + low + close) / 3
        vol = volume.replace(0, 1)
        vwap = (tp * vol).rolling(bars).sum() / vol.rolling(bars).sum()
        f[f'vwap_dev_{suffix}'] = close - vwap

    # ATR (multiple horizons)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    for bars, suffix in [(36, '3h'), (144, '12h'), (288, '24h')]:
        atr = tr.rolling(bars).mean()
        f[f'atr_{suffix}_pct'] = atr / close

    # Volume ratios
    f['vol_ratio_short'] = volume / volume.rolling(48).mean().replace(0, np.nan)
    f['vol_ratio_long'] = volume / volume.rolling(288).mean().replace(0, np.nan)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f['rsi_14'] = 100 - 100 / (1 + gain / loss)

    # Bollinger position
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Volume z-score
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Time features
    hour = m5.index.hour + m5.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * m5.index.dayofweek / 5)

    # Pullbacks
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        rh = high.rolling(bars).max()
        rl = low.rolling(bars).min()
        f[f'pullback_high_{suffix}'] = (rh - close) / close
        f[f'pullback_low_{suffix}'] = (close - rl) / close

    # Spread z-score
    f['spread_zscore'] = (spread - spread.rolling(288).mean()) / spread.rolling(288).std().replace(0, np.nan)

    # Consecutive bars
    f['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f['consec_down'] = close.diff().lt(0).rolling(8).sum()

    # Multi-scale consensus (EMAs at different timeframes)
    ema_12 = close.ewm(span=12).mean()
    ema_48 = close.ewm(span=48).mean()
    ema_144 = close.ewm(span=144).mean()
    f['multi_scale_consensus'] = ((close > ema_12).astype(float) + (close > ema_48).astype(float) + (close > ema_144).astype(float)) / 3

    # Daily trend
    daily_close = close.resample('1D').last()
    daily_sma50 = daily_close.rolling(50).mean()
    daily_sma100 = daily_close.rolling(100).mean()
    f['daily_sma50'] = (daily_close > daily_sma50).astype(float).reindex(m5.index, method='ffill')
    f['daily_sma100'] = (daily_close > daily_sma100).astype(float).reindex(m5.index, method='ffill')
    f['daily_ret_5d'] = daily_close.pct_change(5).reindex(m5.index, method='ffill')

    return f


def backtest_hold_horizon(m5_data, proba, signal_times, threshold, hold_bars=16):
    """Hold-to-horizon backtest. Catastrophic stop only."""
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
    atr = pd.Series(tr, index=dates).rolling(24).mean().values

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
        if m5_idx >= len(close) - hold_bars or m5_idx <= blocked_until_idx:
            continue

        if np.isnan(atr[m5_idx]) or atr[m5_idx] <= 0:
            continue

        entry_price = close[m5_idx]
        oz_per_lot = 100

        # 1% risk on 10 ATR catastrophic
        catastrophic_stop = atr[m5_idx] * 10.0
        risk_amount = equity * 0.01
        lots = risk_amount / (catastrophic_stop * oz_per_lot)
        max_lots = (equity * leverage) / (entry_price * oz_per_lot)
        lots = min(lots, max_lots)
        if lots <= 0:
            continue

        if signal == 1:
            cata_stop = entry_price - catastrophic_stop
        else:
            cata_stop = entry_price + catastrophic_stop

        exit_price = None
        exit_bar = m5_idx + hold_bars

        for j in range(m5_idx + 1, exit_bar + 1):
            if signal == 1 and low_arr[j] <= cata_stop:
                exit_price = cata_stop
                exit_bar = j
                break
            elif signal == -1 and high_arr[j] >= cata_stop:
                exit_price = cata_stop
                exit_bar = j
                break

        if exit_price is None:
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

    if trades == 0 or equity <= breach_threshold:
        return None

    return_pct = (equity - initial_capital) / initial_capital * 100
    win_rate = wins / trades * 100
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    return {'return_pct': return_pct, 'trades': trades, 'win_rate': win_rate, 'profit_factor': pf, 'max_dd': max_dd, 'final_equity': equity}


def main():
    start = datetime.now()
    print(f"WALK-FORWARD — Him V2 MultiScale — REAL RESULTS")
    print("=" * 80)
    print("Period 1 (Train): 2015-2023 (model already trained)")
    print("Period 2 (Optimize): 2024")
    print("Period 3 (Validate): 2025-2026")
    print("Execution: Hold 16 bars (80min), catastrophic stop only")
    print("=" * 80)

    print("\n[1/5] Loading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5 = m5[m5.index >= '2015-01-01']

    period2_start = '2024-01-01'
    period2_end = '2024-12-31'
    period3_start = '2025-01-01'

    m5_period2 = m5[(m5.index >= period2_start) & (m5.index <= period2_end)]
    m5_period3 = m5[m5.index >= period3_start]

    print(f"  Period 2 (2024): {len(m5_period2):,} bars")
    print(f"  Period 3 (2025-2026): {len(m5_period3):,} bars")

    print("\n[2/5] Loading model...")
    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))
    print(f"  Model: {MODEL_PATH.name}")

    print("\n[3/5] Building features...")
    m5_features = build_multiscale_features(m5)

    # Load expected feature list from model
    feat_cols = ['ret_1bar', 'ret_4bar', 'ret_16bar', 'ret_96bar', 'ret_8bar', 'ret_32bar', 'ret_64bar',
                 'range_pos_6h', 'range_pos_12h', 'range_pos_24h', 'vwap_dev_4h', 'vwap_dev_12h', 'vwap_dev_24h',
                 'atr_3h_pct', 'atr_12h_pct', 'atr_24h_pct', 'vol_ratio_short', 'vol_ratio_long',
                 'rsi_14', 'bb_pos', 'vol_zscore', 'cos_hour', 'sin_hour', 'cos_dow',
                 'pullback_high_4h', 'pullback_low_4h', 'pullback_high_12h', 'pullback_low_12h',
                 'pullback_high_24h', 'pullback_low_24h', 'spread_zscore', 'consec_up', 'consec_down',
                 'multi_scale_consensus', 'daily_sma50', 'daily_sma100', 'daily_ret_5d']

    print(f"  Features: {len(feat_cols)}")

    print("\n[4/5] PERIOD 2 OPTIMIZATION (2024)...")
    m5_p2_feat = m5_features[(m5_features.index >= period2_start) & (m5_features.index <= period2_end)][feat_cols].dropna()
    m5_p2_proba = model.predict(xgb.DMatrix(m5_p2_feat.values, feature_names=feat_cols))

    print(f"  Signals: {len(m5_p2_proba):,}")
    print(f"  Proba: mean={m5_p2_proba.mean():.3f}, std={m5_p2_proba.std():.3f}")

    thresholds = [0.50, 0.52, 0.55, 0.58, 0.60, 0.62, 0.65, 0.68, 0.70]

    results_p2 = []
    for thresh in thresholds:
        r = backtest_hold_horizon(m5_period2, m5_p2_proba, m5_p2_feat.index, thresh, hold_bars=16)
        if r:
            results_p2.append({'threshold': thresh, **r})

    if not results_p2:
        print("\n  NO PROFITABLE CONFIGS ON PERIOD 2")
        return

    results_p2.sort(key=lambda x: -x['return_pct'])

    print("\n" + "=" * 80)
    print("PERIOD 2 (2024) RESULTS")
    print("=" * 80)
    for i, r in enumerate(results_p2, 1):
        print(f"  {i}. Thresh {r['threshold']:.2f}: {r['return_pct']:+6.1f}%, {r['trades']:4} trades, WR {r['win_rate']:.1f}%, PF {r['profit_factor']:.2f}, DD {r['max_dd']:.1f}%")

    best = results_p2[0]
    locked_thresh = best['threshold']

    print("\n" + "=" * 80)
    print("LOCKED CONFIG")
    print("=" * 80)
    print(f"  Threshold: {locked_thresh}")
    print(f"  Hold: 16 bars (80 min)")
    print(f"  Period 2: {best['return_pct']:+.1f}%, WR {best['win_rate']:.1f}%, PF {best['profit_factor']:.2f}")

    print("\n[5/5] PERIOD 3 VALIDATION (2025-2026)...")
    m5_p3_feat = m5_features[m5_features.index >= period3_start][feat_cols].dropna()
    m5_p3_proba = model.predict(xgb.DMatrix(m5_p3_feat.values, feature_names=feat_cols))

    r_p3 = backtest_hold_horizon(m5_period3, m5_p3_proba, m5_p3_feat.index, locked_thresh, hold_bars=16)

    if not r_p3:
        print("\n" + "=" * 80)
        print("VERDICT: ✗ REJECT — Breached on 2025-2026")
        print("=" * 80)
        return

    # 2024 = 12 months, 2025-2026 = 17 months
    p2_annual = best['return_pct']
    p3_annual = r_p3['return_pct'] * (12 / 17)

    print("\n" + "=" * 80)
    print("PERIOD 3 (2025-2026) VALIDATION")
    print("=" * 80)
    print(f"  Return: {r_p3['return_pct']:+.1f}% (17mo) → {p3_annual:+.1f}% annualized")
    print(f"  Trades: {r_p3['trades']}")
    print(f"  Win Rate: {r_p3['win_rate']:.1f}%")
    print(f"  PF: {r_p3['profit_factor']:.2f}")
    print(f"  Max DD: {r_p3['max_dd']:.1f}%")

    return_ratio = p3_annual / p2_annual if p2_annual > 0 else 0
    degradation = p2_annual - p3_annual

    print("\n" + "=" * 80)
    print("OVERFITTING ANALYSIS")
    print("=" * 80)
    print(f"  Period 2 (2024): {p2_annual:+.1f}% annual")
    print(f"  Period 3 (2025-2026): {p3_annual:+.1f}% annual")
    print(f"  Degradation: {degradation:+.1f}%")
    print(f"  Return Ratio: {return_ratio:.3f}")

    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    if p3_annual > 50 and return_ratio > 0.70:
        verdict = "✓ DEPLOY"
        status = f"Edge exists: {p3_annual:+.1f}% annual on unseen data"
    elif p3_annual > 20 and return_ratio > 0.50:
        verdict = "⚠ MARGINAL"
        status = f"Weak edge: {p3_annual:+.1f}% annual, high degradation"
    else:
        verdict = "✗ REJECT"
        status = f"No edge: {p3_annual:+.1f}% annual insufficient"

    print(f"\n  {verdict}: {status}")
    print(f"  Expected monthly: {p3_annual/12:+.1f}%")

    # Save
    analysis = {
        'timestamp': datetime.now().isoformat(),
        'model': 'Him_V2_MultiScale',
        'locked_config': {'threshold': locked_thresh, 'hold_bars': 16},
        'period2': {'year': 2024, 'return_pct': best['return_pct'], 'trades': best['trades'], 'win_rate': best['win_rate'], 'pf': best['profit_factor']},
        'period3': {'period': '2025-2026', 'return_pct': r_p3['return_pct'], 'annualized': p3_annual, 'trades': r_p3['trades'], 'win_rate': r_p3['win_rate'], 'pf': r_p3['profit_factor']},
        'overfitting': {'return_ratio': return_ratio, 'degradation': degradation},
        'verdict': verdict
    }
    with open(OUTPUT_DIR / "walk_forward_analysis.json", 'w') as f:
        json.dump(analysis, f, indent=2)

    with open(OUTPUT_DIR / "RESULTS.txt", 'w') as f:
        f.write(f"Him V2 MultiScale — Walk-Forward Validation\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"LOCKED CONFIG:\n")
        f.write(f"  Threshold: {locked_thresh}\n")
        f.write(f"  Hold: 16 bars (80 min)\n\n")
        f.write(f"PERIOD 2 (2024):\n")
        f.write(f"  Return: {p2_annual:+.1f}% annual\n")
        f.write(f"  Trades: {best['trades']}\n")
        f.write(f"  Win Rate: {best['win_rate']:.1f}%\n")
        f.write(f"  PF: {best['profit_factor']:.2f}\n\n")
        f.write(f"PERIOD 3 (2025-2026):\n")
        f.write(f"  Return: {p3_annual:+.1f}% annual\n")
        f.write(f"  Trades: {r_p3['trades']}\n")
        f.write(f"  Win Rate: {r_p3['win_rate']:.1f}%\n")
        f.write(f"  PF: {r_p3['profit_factor']:.2f}\n\n")
        f.write(f"VERDICT: {verdict}\n")
        f.write(f"{status}\n")

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n  Time: {elapsed:.0f}s")
    print(f"  Files: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
