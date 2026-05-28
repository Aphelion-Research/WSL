"""
Diagnostic Analysis — Him V2 MultiScale — Locked Config
========================================================
No optimization. Forensic analysis of locked strategy.

Tests:
1. Cost sensitivity: 0x, 0.5x, 1x, 2x, 3x costs
2. Null tests: random, shuffled, shifted, reversed
3. Trade distribution: win/loss, concentration
4. Regime breakdown: year, month, session, volatility, trend
5. Stability: monthly PF, quarterly Sharpe, top trade concentration

Locked config from walk_forward_multiscale_real.py:
- Threshold: 0.55
- Hold: 16 bars (80 min)
- Stop: 10 ATR catastrophic only
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_V2_MultiScale.json")
OUTPUT_DIR = Path("output_him_v2/diagnostic_multiscale")
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

LOCKED_CONFIG = {'threshold': 0.55, 'hold_bars': 16}


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

    # Multi-scale consensus
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


def backtest_with_cost(m5_data, proba, signal_times, threshold, hold_bars, cost_multiplier=1.0):
    """Hold-to-horizon backtest with configurable transaction costs."""
    leverage = 50
    initial_capital = 10000.0
    breach_threshold = 9000.0

    # Base cost: implicit spread already in M5 bar prices
    # Additional cost: slippage + commission
    base_cost_pct = 0.0002  # 2 bps per round trip
    cost_pct = base_cost_pct * cost_multiplier

    equity = initial_capital
    close = m5_data['close'].values
    high_arr = m5_data['high'].values
    low_arr = m5_data['low'].values
    dates = m5_data.index

    tr = np.maximum(high_arr - low_arr, np.maximum(np.abs(high_arr - np.roll(close, 1)), np.abs(low_arr - np.roll(close, 1))))
    tr[0] = high_arr[0] - low_arr[0]
    atr = pd.Series(tr, index=dates).rolling(24).mean().values

    trades = []
    equity_curve = [initial_capital]
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
            pnl_gross = (exit_price - entry_price) * lots * oz_per_lot
        else:
            pnl_gross = (entry_price - exit_price) * lots * oz_per_lot

        # Apply transaction costs
        cost = entry_price * lots * oz_per_lot * cost_pct
        pnl_net = pnl_gross - cost

        equity += pnl_net
        equity_curve.append(equity)

        # Collect trade metadata
        trade = {
            'entry_time': dates[m5_idx],
            'exit_time': dates[exit_bar],
            'signal': signal,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'lots': lots,
            'pnl_gross': pnl_gross,
            'pnl_net': pnl_net,
            'cost': cost,
            'equity': equity,
            'bars_held': exit_bar - m5_idx,
            'atr': atr[m5_idx],
            'proba': p
        }
        trades.append(trade)

        blocked_until_idx = exit_bar

    if len(trades) == 0:
        return None

    df_trades = pd.DataFrame(trades)
    wins = df_trades[df_trades['pnl_net'] > 0]
    losses = df_trades[df_trades['pnl_net'] <= 0]

    gross_profit = wins['pnl_net'].sum()
    gross_loss = abs(losses['pnl_net'].sum())
    pf = gross_profit / gross_loss if gross_loss > 0 else 0

    equity_arr = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_arr)
    dd = (equity_arr - peak) / peak * 100
    max_dd = dd.min()

    return_pct = (equity - initial_capital) / initial_capital * 100
    win_rate = len(wins) / len(df_trades) * 100

    return {
        'return_pct': return_pct,
        'trades': len(df_trades),
        'win_rate': win_rate,
        'profit_factor': pf,
        'max_dd': max_dd,
        'final_equity': equity,
        'breached': equity <= breach_threshold,
        'trades_df': df_trades,
        'equity_curve': equity_arr
    }


def analyze_trade_distribution(trades_df):
    """Analyze win/loss distribution and concentration."""
    wins = trades_df[trades_df['pnl_net'] > 0]['pnl_net']
    losses = trades_df[trades_df['pnl_net'] <= 0]['pnl_net']

    # Sort by PnL
    sorted_pnl = trades_df.sort_values('pnl_net', ascending=False)
    top_5 = sorted_pnl.head(5)['pnl_net'].sum()
    top_10 = sorted_pnl.head(10)['pnl_net'].sum()
    total_pnl = trades_df['pnl_net'].sum()

    # Losing streaks
    trades_df['win'] = (trades_df['pnl_net'] > 0).astype(int)
    trades_df['streak'] = (trades_df['win'] != trades_df['win'].shift()).cumsum()
    losing_streaks = trades_df[trades_df['win'] == 0].groupby('streak').size()
    max_losing_streak = losing_streaks.max() if len(losing_streaks) > 0 else 0

    return {
        'avg_win': wins.mean() if len(wins) > 0 else 0,
        'median_win': wins.median() if len(wins) > 0 else 0,
        'avg_loss': losses.mean() if len(losses) > 0 else 0,
        'median_loss': losses.median() if len(losses) > 0 else 0,
        'largest_win': wins.max() if len(wins) > 0 else 0,
        'largest_loss': losses.min() if len(losses) > 0 else 0,
        'top_5_pct': top_5 / total_pnl * 100 if total_pnl > 0 else 0,
        'top_10_pct': top_10 / total_pnl * 100 if total_pnl > 0 else 0,
        'max_losing_streak': max_losing_streak
    }


def analyze_regime_breakdown(trades_df, m5_data):
    """Breakdown by year, month, session, volatility, trend."""
    trades_df = trades_df.copy()
    trades_df['year'] = trades_df['entry_time'].dt.year
    trades_df['month'] = trades_df['entry_time'].dt.month
    trades_df['hour'] = trades_df['entry_time'].dt.hour

    # Session (rough)
    def get_session(hour):
        if 0 <= hour < 8:
            return 'ASIA'
        elif 8 <= hour < 14:
            return 'LONDON'
        elif 14 <= hour < 20:
            return 'NY'
        else:
            return 'LATE'
    trades_df['session'] = trades_df['hour'].apply(get_session)

    # Volatility regime (ATR quartiles)
    atr_vals = trades_df['atr'].dropna()
    if len(atr_vals) > 0:
        q25, q75 = atr_vals.quantile([0.25, 0.75])
        def get_vol_regime(atr):
            if atr < q25:
                return 'LOW'
            elif atr < q75:
                return 'MED'
            else:
                return 'HIGH'
        trades_df['vol_regime'] = trades_df['atr'].apply(get_vol_regime)
    else:
        trades_df['vol_regime'] = 'UNKNOWN'

    # Trend regime (daily SMA from features)
    # We'll compute on-the-fly from m5_data
    close = m5_data['close']
    daily_close = close.resample('1D').last()
    daily_sma50 = daily_close.rolling(50).mean()
    daily_trend = (daily_close > daily_sma50).astype(int).reindex(m5_data.index, method='ffill')

    trades_df['trend_regime'] = trades_df['entry_time'].map(lambda t: daily_trend.loc[t] if t in daily_trend.index else np.nan)
    trades_df['trend_regime'] = trades_df['trend_regime'].map({1: 'BULL', 0: 'BEAR'})

    # Breakdown
    breakdown = {}

    for dim in ['year', 'month', 'session', 'vol_regime', 'trend_regime']:
        grp = trades_df.groupby(dim)
        stats = []
        for name, g in grp:
            wins = g[g['pnl_net'] > 0]
            gross_profit = wins['pnl_net'].sum()
            gross_loss = abs(g[g['pnl_net'] <= 0]['pnl_net'].sum())
            pf = gross_profit / gross_loss if gross_loss > 0 else 0
            wr = len(wins) / len(g) * 100 if len(g) > 0 else 0
            total_pnl = g['pnl_net'].sum()

            stats.append({
                dim: name,
                'trades': len(g),
                'win_rate': wr,
                'pf': pf,
                'total_pnl': total_pnl
            })

        breakdown[dim] = pd.DataFrame(stats)

    return breakdown


def stability_checks(trades_df):
    """Monthly PF, quarterly Sharpe, top trade concentration."""
    trades_df = trades_df.copy()
    trades_df['year_month'] = trades_df['entry_time'].dt.to_period('M')

    monthly_stats = []
    for ym, g in trades_df.groupby('year_month'):
        wins = g[g['pnl_net'] > 0]
        gross_profit = wins['pnl_net'].sum()
        gross_loss = abs(g[g['pnl_net'] <= 0]['pnl_net'].sum())
        pf = gross_profit / gross_loss if gross_loss > 0 else 0
        total_pnl = g['pnl_net'].sum()

        monthly_stats.append({
            'year_month': str(ym),
            'trades': len(g),
            'pf': pf,
            'total_pnl': total_pnl
        })

    df_monthly = pd.DataFrame(monthly_stats)

    # Sharpe by quarter
    trades_df['quarter'] = trades_df['entry_time'].dt.to_period('Q')
    quarterly_returns = trades_df.groupby('quarter')['pnl_net'].sum()
    sharpe_quarterly = quarterly_returns.mean() / quarterly_returns.std() if quarterly_returns.std() > 0 else 0

    # Top 5 trade concentration
    sorted_pnl = trades_df.sort_values('pnl_net', ascending=False)
    top_5_pnl = sorted_pnl.head(5)['pnl_net'].sum()
    total_pnl = trades_df['pnl_net'].sum()
    top_5_pct = top_5_pnl / total_pnl * 100 if total_pnl > 0 else 0

    # Edge without top 5 trades
    pnl_without_top5 = trades_df[~trades_df.index.isin(sorted_pnl.head(5).index)]['pnl_net'].sum()

    return {
        'monthly_pf': df_monthly,
        'sharpe_quarterly': sharpe_quarterly,
        'top_5_concentration_pct': top_5_pct,
        'pnl_without_top5': pnl_without_top5
    }


def null_tests(m5_data, m5_features, feat_cols, proba_real, signal_times, threshold, hold_bars):
    """Null hypothesis tests: random, shuffled, shifted, reversed."""
    results = {}

    # 1. Random probabilities
    np.random.seed(42)
    proba_random = np.random.uniform(0, 1, len(proba_real))
    r_random = backtest_with_cost(m5_data, proba_random, signal_times, threshold, hold_bars)
    results['random'] = r_random

    # 2. Shuffled probabilities
    proba_shuffled = proba_real.copy()
    np.random.seed(42)
    np.random.shuffle(proba_shuffled)
    r_shuffled = backtest_with_cost(m5_data, proba_shuffled, signal_times, threshold, hold_bars)
    results['shuffled'] = r_shuffled

    # 3. Shifted probabilities (+1, +5, +20 bars)
    for shift in [1, 5, 20]:
        proba_shifted = np.roll(proba_real, shift)
        r_shifted = backtest_with_cost(m5_data, proba_shifted, signal_times, threshold, hold_bars)
        results[f'shifted_{shift}'] = r_shifted

    # 4. Reversed signal (1 - proba)
    proba_reversed = 1 - proba_real
    r_reversed = backtest_with_cost(m5_data, proba_reversed, signal_times, threshold, hold_bars)
    results['reversed'] = r_reversed

    return results


def main():
    start = datetime.now()
    print("=" * 80)
    print("DIAGNOSTIC ANALYSIS — Him V2 MultiScale — Locked Config")
    print("=" * 80)
    print(f"Locked config: threshold={LOCKED_CONFIG['threshold']}, hold={LOCKED_CONFIG['hold_bars']} bars")
    print(f"Period: 2025-2026 (validation data)")
    print("=" * 80)

    print("\n[1/7] Loading data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m5_period = m5[m5.index >= '2025-01-01']
    print(f"  Bars: {len(m5_period):,}")

    print("\n[2/7] Loading model...")
    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))

    print("\n[3/7] Building features...")
    m5_features = build_multiscale_features(m5)
    feat_cols = ['ret_1bar', 'ret_4bar', 'ret_16bar', 'ret_96bar', 'ret_8bar', 'ret_32bar', 'ret_64bar',
                 'range_pos_6h', 'range_pos_12h', 'range_pos_24h', 'vwap_dev_4h', 'vwap_dev_12h', 'vwap_dev_24h',
                 'atr_3h_pct', 'atr_12h_pct', 'atr_24h_pct', 'vol_ratio_short', 'vol_ratio_long',
                 'rsi_14', 'bb_pos', 'vol_zscore', 'cos_hour', 'sin_hour', 'cos_dow',
                 'pullback_high_4h', 'pullback_low_4h', 'pullback_high_12h', 'pullback_low_12h',
                 'pullback_high_24h', 'pullback_low_24h', 'spread_zscore', 'consec_up', 'consec_down',
                 'multi_scale_consensus', 'daily_sma50', 'daily_sma100', 'daily_ret_5d']

    m5_feat = m5_features[m5_features.index >= '2025-01-01'][feat_cols].dropna()
    proba = model.predict(xgb.DMatrix(m5_feat.values, feature_names=feat_cols))
    print(f"  Features: {len(feat_cols)}")
    print(f"  Signals: {len(proba):,}")
    print(f"  Proba: mean={proba.mean():.3f}, std={proba.std():.3f}")

    # =====================================================================
    # TEST 1: Cost Sensitivity
    # =====================================================================
    print("\n" + "=" * 80)
    print("TEST 1: COST SENSITIVITY")
    print("=" * 80)

    cost_mults = [0.0, 0.5, 1.0, 2.0, 3.0]
    cost_results = []

    for cm in cost_mults:
        r = backtest_with_cost(m5_period, proba, m5_feat.index, LOCKED_CONFIG['threshold'], LOCKED_CONFIG['hold_bars'], cost_multiplier=cm)
        if r:
            cost_results.append({
                'cost_mult': cm,
                'return_pct': float(r['return_pct']),
                'pf': float(r['profit_factor']),
                'max_dd': float(r['max_dd']),
                'breached': bool(r['breached']),
                'trades': int(r['trades'])
            })
        else:
            cost_results.append({
                'cost_mult': cm,
                'return_pct': 0.0,
                'pf': 0.0,
                'max_dd': 0.0,
                'breached': True,
                'trades': 0
            })

    df_cost = pd.DataFrame(cost_results)
    print(df_cost.to_string(index=False))

    # =====================================================================
    # TEST 2: Null Tests
    # =====================================================================
    print("\n" + "=" * 80)
    print("TEST 2: NULL HYPOTHESIS TESTS")
    print("=" * 80)

    null_results = null_tests(m5_period, m5_features, feat_cols, proba, m5_feat.index, LOCKED_CONFIG['threshold'], LOCKED_CONFIG['hold_bars'])

    print(f"{'Test':<15} {'Return%':<12} {'Trades':<10} {'WR%':<10} {'PF':<10} {'Breached':<10}")
    print("-" * 80)
    print(f"{'REAL':<15} {cost_results[2]['return_pct']:<+12.1f} {cost_results[2]['trades']:<10} {'N/A':<10} {cost_results[2]['pf']:<10.2f} {cost_results[2]['breached']}")

    for name, r in null_results.items():
        if r:
            print(f"{name:<15} {r['return_pct']:<+12.1f} {r['trades']:<10} {r['win_rate']:<10.1f} {r['profit_factor']:<10.2f} {r['breached']}")
        else:
            print(f"{name:<15} {'BREACH':<12} {0:<10} {'N/A':<10} {'N/A':<10} {'True'}")

    # =====================================================================
    # TEST 3: Trade Distribution
    # =====================================================================
    print("\n" + "=" * 80)
    print("TEST 3: TRADE DISTRIBUTION")
    print("=" * 80)

    baseline_result = backtest_with_cost(m5_period, proba, m5_feat.index, LOCKED_CONFIG['threshold'], LOCKED_CONFIG['hold_bars'], cost_multiplier=1.0)
    if baseline_result:
        dist = analyze_trade_distribution(baseline_result['trades_df'])
        print(f"  Total trades: {baseline_result['trades']}")
        print(f"  Avg win: ${dist['avg_win']:.2f}")
        print(f"  Median win: ${dist['median_win']:.2f}")
        print(f"  Avg loss: ${dist['avg_loss']:.2f}")
        print(f"  Median loss: ${dist['median_loss']:.2f}")
        print(f"  Largest win: ${dist['largest_win']:.2f}")
        print(f"  Largest loss: ${dist['largest_loss']:.2f}")
        print(f"  Top 5 trades: {dist['top_5_pct']:.1f}% of total PnL")
        print(f"  Top 10 trades: {dist['top_10_pct']:.1f}% of total PnL")
        print(f"  Max losing streak: {dist['max_losing_streak']}")

    # =====================================================================
    # TEST 4: Regime Breakdown
    # =====================================================================
    print("\n" + "=" * 80)
    print("TEST 4: REGIME BREAKDOWN")
    print("=" * 80)

    if baseline_result:
        breakdown = analyze_regime_breakdown(baseline_result['trades_df'], m5_period)

        for dim_name, df_dim in breakdown.items():
            print(f"\n{dim_name.upper()}:")
            print(df_dim.to_string(index=False))

    # =====================================================================
    # TEST 5: Stability Checks
    # =====================================================================
    print("\n" + "=" * 80)
    print("TEST 5: STABILITY CHECKS")
    print("=" * 80)

    if baseline_result:
        stability = stability_checks(baseline_result['trades_df'])

        print("\nMONTHLY PROFIT FACTOR:")
        print(stability['monthly_pf'].to_string(index=False))

        print(f"\nSharpe (quarterly): {stability['sharpe_quarterly']:.3f}")
        print(f"Top 5 trades: {stability['top_5_concentration_pct']:.1f}% of total PnL")
        print(f"PnL without top 5 trades: ${stability['pnl_without_top5']:.2f}")

        # Edge without top 5
        total_pnl = baseline_result['trades_df']['pnl_net'].sum()
        return_without_top5 = stability['pnl_without_top5'] / 10000 * 100
        print(f"Return without top 5 trades: {return_without_top5:+.1f}%")

    # =====================================================================
    # VERDICT
    # =====================================================================
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    if baseline_result:
        # Criteria:
        # 1. Positive PnL at 1x cost
        # 2. Beats random/shuffled by >2x
        # 3. PF > 1.05
        # 4. PnL without top 5 trades > 0
        # 5. Sharpe > 0.5

        beats_random = baseline_result['return_pct'] > (null_results['random']['return_pct'] * 2 if null_results['random'] else 0)
        pf_ok = baseline_result['profit_factor'] > 1.05
        pnl_stable = stability['pnl_without_top5'] > 0
        sharpe_ok = stability['sharpe_quarterly'] > 0.5

        if beats_random and pf_ok and pnl_stable and sharpe_ok:
            verdict = "✓ REAL WEAK EDGE"
            explanation = "Beats null tests, PF > 1.05, stable without top trades, Sharpe > 0.5"
        elif beats_random and pf_ok:
            verdict = "⚠ MARGINAL EDGE"
            explanation = "Beats null tests but unstable (top trade concentration or low Sharpe)"
        else:
            verdict = "✗ NOISE"
            explanation = "Does not consistently beat null tests or PF too low"

        print(f"\n  {verdict}")
        print(f"  {explanation}")
        print(f"\n  Baseline (1x cost): {baseline_result['return_pct']:+.1f}%, PF {baseline_result['profit_factor']:.2f}")
        print(f"  Random: {null_results['random']['return_pct']:+.1f}%" if null_results['random'] else "  Random: BREACH")
        print(f"  Sharpe (Q): {stability['sharpe_quarterly']:.3f}")
        print(f"  Top 5 concentration: {stability['top_5_concentration_pct']:.1f}%")

    # Save outputs
    with open(OUTPUT_DIR / "cost_sensitivity.json", 'w') as f:
        json.dump(cost_results, f, indent=2)

    null_summary = {k: {'return_pct': float(v['return_pct']), 'trades': int(v['trades']), 'breached': bool(v['breached'])} if v else {'breached': True} for k, v in null_results.items()}
    with open(OUTPUT_DIR / "null_tests.json", 'w') as f:
        json.dump(null_summary, f, indent=2)

    if baseline_result:
        baseline_result['trades_df'].to_csv(OUTPUT_DIR / "trades.csv", index=False)
        stability['monthly_pf'].to_csv(OUTPUT_DIR / "monthly_pf.csv", index=False)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"\n  Time: {elapsed:.0f}s")
    print(f"  Files: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
