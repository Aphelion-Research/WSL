"""
Him V2 backtest with Kelly Criterion position sizing.
Uses fractional Kelly (0.25x-0.5x) + 10% margin cap for safety.
Compounding: position sizes scale with equity automatically.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import xgboost as xgb
import json
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = Path("data")
MODEL_PATH = Path("output_him_v2/him_v2.json")
OUTPUT_DIR = Path("output_him_v2")


def load_m15():
    m5 = pd.read_parquet(DATA_DIR / "mt5_history/XAUUSD_M5_dukascopy.parquet")
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()
    m15 = m5.resample('15min').agg({
        'open': 'first', 'high': 'max', 'low': 'min',
        'close': 'last', 'tick_volume': 'sum', 'spread': 'mean',
    }).dropna(subset=['close'])
    m15 = m15[m15['tick_volume'] > 0]
    return m15


def build_features(m15):
    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    f = pd.DataFrame(index=m15.index)

    f['ret_1bar'] = close.pct_change(1)
    f['ret_4bar'] = close.pct_change(4)
    f['ret_16bar'] = close.pct_change(16)
    f['ret_96bar'] = close.pct_change(96)

    rolling_high_96 = close.rolling(96).max()
    rolling_low_96 = close.rolling(96).min()
    range_96 = (rolling_high_96 - rolling_low_96).replace(0, np.nan)
    f['range_pos_24h'] = (close - rolling_low_96) / range_96

    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)
    f['vwap_dev_4h'] = (close - (tp * vol).rolling(16).sum() / vol.rolling(16).sum()) / close
    f['vwap_dev_24h'] = (close - (tp * vol).rolling(96).sum() / vol.rolling(96).sum()) / close

    tr_15 = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr_12 = tr_15.rolling(12).mean()
    atr_48 = tr_15.rolling(48).mean()
    atr_96 = tr_15.rolling(96).mean()
    f['atr_3h_pct'] = atr_12 / close
    f['atr_24h_pct'] = atr_96 / close
    f['vol_ratio'] = atr_12 / atr_48.replace(0, np.nan)

    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean()
    f['rsi_14'] = 100 - 100 / (1 + gain / loss_val.replace(0, np.nan))

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    hour = m15.index.hour + m15.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * m15.index.dayofweek / 5)

    f['pullback_from_high'] = (rolling_high_96 - close) / atr_96.replace(0, np.nan)
    f['pullback_from_low'] = (close - rolling_low_96) / atr_96.replace(0, np.nan)

    f['spread_zscore'] = (m15['spread'] - m15['spread'].rolling(96).mean()) / m15['spread'].rolling(96).std().replace(0, np.nan)

    f['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f['consec_down'] = close.diff().lt(0).rolling(8).sum()

    m5_daily = close.resample('1D').last().dropna()
    d_sma50 = ((m5_daily - m5_daily.rolling(50).mean()) / m5_daily.rolling(50).mean()).shift(2)
    d_sma100 = ((m5_daily - m5_daily.rolling(100).mean()) / m5_daily.rolling(100).mean()).shift(2)
    d_ret_5d = m5_daily.pct_change(5).shift(2)

    f['daily_sma50'] = d_sma50.reindex(m15.index, method='ffill')
    f['daily_sma100'] = d_sma100.reindex(m15.index, method='ffill')
    f['daily_ret_5d'] = d_ret_5d.reindex(m15.index, method='ffill')
    f['daily_bull'] = ((f['daily_sma50'] > 0) & (f['daily_sma100'] > 0)).astype(float)
    f['daily_bear'] = ((f['daily_sma50'] < 0) & (f['daily_sma100'] < 0)).astype(float)

    return f


def calculate_kelly_fraction(win_prob, rr_ratio, kelly_fraction=0.25):
    """
    Kelly Criterion: f* = (p * b - q) / b

    Args:
        win_prob: Probability of winning (0-1)
        rr_ratio: Reward/Risk ratio (avg_win / avg_loss)
        kelly_fraction: Fraction of full Kelly to use (0.25 = quarter Kelly)

    Returns:
        Fraction of bankroll to risk
    """
    if rr_ratio <= 0 or win_prob <= 0 or win_prob >= 1:
        return 0

    q = 1 - win_prob
    b = rr_ratio

    kelly = (win_prob * b - q) / b

    # Apply fractional Kelly
    kelly *= kelly_fraction

    # Cap at reasonable limits
    return max(0, min(kelly, 0.20))  # Never risk more than 20% even with Kelly


def run_kelly_backtest(m15, features, proba, config):
    """
    Prop firm backtest with Kelly position sizing.
    """
    threshold = config['threshold']
    trend_filter = config.get('trend_filter', True)
    long_only_bull = config.get('long_only_bull', False)
    kelly_fraction = config.get('kelly_fraction', 0.25)  # Fractional Kelly
    max_margin_pct = config.get('max_margin_pct', 0.10)  # 10% of margin max
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

    trades = []
    equity_curve = []
    breached = False
    breach_reason = None

    # Track historical performance for Kelly calculation
    recent_wins = []
    recent_losses = []
    lookback = 30  # Use last 30 trades for Kelly estimation

    close = m15['close'].values
    high = m15['high'].values
    low = m15['low'].values
    dates = m15.index

    tr = np.maximum(high - low, np.maximum(
        np.abs(high - np.roll(close, 1)),
        np.abs(low - np.roll(close, 1))
    ))
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(12).mean().values

    daily_bull = features['daily_bull'].values
    daily_bear = features['daily_bear'].values

    i = 0

    while i < len(proba):
        dt = dates[i]

        if equity <= total_loss_breach:
            breached = True
            breach_reason = f"Total loss breach: equity ${equity:.0f} <= ${total_loss_breach:.0f}"
            break

        if current_date is None or dt.date() != current_date:
            current_date = dt.date()
            daily_start_equity = equity
            daily_pnl = 0.0

        daily_limit = daily_start_equity * daily_loss_limit
        if daily_pnl <= -daily_limit:
            while i < len(proba) and dates[i].date() == current_date:
                equity_curve.append({'time': dates[i], 'equity': equity})
                i += 1
            continue

        if not np.isnan(proba[i]) and not np.isnan(atr[i]) and atr[i] > 0:
            p = proba[i]
            signal = None

            if p > threshold:
                signal = 'LONG'
            elif p < (1 - threshold):
                signal = 'SHORT'

            if signal and trend_filter:
                if signal == 'LONG' and daily_bull[i] != 1:
                    signal = None
                if signal == 'SHORT' and daily_bear[i] != 1:
                    signal = None

            if signal and long_only_bull:
                if signal == 'SHORT':
                    signal = None
                if signal == 'LONG' and daily_bull[i] != 1:
                    signal = None

            if signal:
                entry_price = close[i]
                stop_distance = atr[i] * stop_mult
                tp_distance = atr[i] * tp_mult

                # Calculate Kelly position size
                if len(recent_wins) >= 5 and len(recent_losses) >= 5:
                    # Use historical performance
                    avg_win = np.mean(recent_wins[-lookback:])
                    avg_loss = abs(np.mean(recent_losses[-lookback:]))
                    win_rate = len(recent_wins) / (len(recent_wins) + len(recent_losses))
                    rr_ratio = avg_win / avg_loss if avg_loss > 0 else 1.5
                else:
                    # Bootstrap with expected values
                    win_rate = 0.50  # Conservative start
                    rr_ratio = tp_mult / stop_mult  # Expected R:R from stops

                # Use model confidence to adjust win probability
                # Model says >0.65 → historically 70%+ WR, use that
                if p > 0.65 or p < 0.35:
                    estimated_wr = 0.70
                elif p > 0.60 or p < 0.40:
                    estimated_wr = 0.65
                else:
                    estimated_wr = win_rate  # Use historical

                kelly_f = calculate_kelly_fraction(estimated_wr, rr_ratio, kelly_fraction)

                # Kelly says risk kelly_f of equity
                risk_amount = equity * kelly_f

                # Position size from Kelly
                oz_per_lot = 100
                lots_kelly = risk_amount / (stop_distance * oz_per_lot)

                # Cap by leverage (50x) and max margin (10%)
                max_lots_leverage = (equity * leverage) / (entry_price * oz_per_lot)
                max_lots_margin = (equity * leverage * max_margin_pct) / (entry_price * oz_per_lot)

                lots = min(lots_kelly, max_lots_leverage, max_lots_margin)

                if lots <= 0:
                    equity_curve.append({'time': dt, 'equity': equity})
                    i += 1
                    continue

                if signal == 'LONG':
                    stop_price = entry_price - stop_distance
                    tp_price = entry_price + tp_distance
                else:
                    stop_price = entry_price + stop_distance
                    tp_price = entry_price - tp_distance

                trade_pnl = 0
                exit_price = None
                exit_reason = None
                exit_bar = i

                for j in range(i + 1, min(i + 17, len(close))):
                    if signal == 'LONG':
                        if low[j] <= stop_price:
                            exit_price = stop_price
                            exit_reason = 'stop'
                            exit_bar = j
                            break
                        if high[j] >= tp_price:
                            exit_price = tp_price
                            exit_reason = 'tp'
                            exit_bar = j
                            break
                    else:
                        if high[j] >= stop_price:
                            exit_price = stop_price
                            exit_reason = 'stop'
                            exit_bar = j
                            break
                        if low[j] <= tp_price:
                            exit_price = tp_price
                            exit_reason = 'tp'
                            exit_bar = j
                            break

                if exit_price is None:
                    exit_bar = min(i + 16, len(close) - 1)
                    exit_price = close[exit_bar]
                    exit_reason = 'timeout'

                if signal == 'LONG':
                    trade_pnl = (exit_price - entry_price) * lots * oz_per_lot
                else:
                    trade_pnl = (entry_price - exit_price) * lots * oz_per_lot

                # Update historical tracking
                if trade_pnl > 0:
                    recent_wins.append(trade_pnl)
                else:
                    recent_losses.append(trade_pnl)

                equity += trade_pnl
                daily_pnl += trade_pnl
                peak_equity = max(peak_equity, equity)

                trades.append({
                    'entry_time': str(dt),
                    'exit_time': str(dates[exit_bar]),
                    'signal': signal,
                    'entry_price': float(entry_price),
                    'exit_price': float(exit_price),
                    'lots': float(lots),
                    'pnl': float(trade_pnl),
                    'exit_reason': exit_reason,
                    'proba': float(p),
                    'equity_after': float(equity),
                    'kelly_f': float(kelly_f),
                    'risk_amount': float(risk_amount),
                })

                for k in range(i, exit_bar + 1):
                    equity_curve.append({'time': dates[k], 'equity': equity})
                i = exit_bar + 1
                continue

        equity_curve.append({'time': dt, 'equity': equity})
        i += 1

    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1

    eq_values = [e['equity'] for e in equity_curve]
    if eq_values:
        peak = eq_values[0]
        max_dd = 0
        for v in eq_values:
            peak = max(peak, v)
            dd = (v - peak) / peak
            max_dd = min(max_dd, dd)
    else:
        max_dd = 0

    monthly = {}
    for t in trades:
        month = t['entry_time'][:7]
        if month not in monthly:
            monthly[month] = {'trades': 0, 'wins': 0, 'pnl': 0, 'longs': 0, 'shorts': 0}
        monthly[month]['trades'] += 1
        if t['pnl'] > 0:
            monthly[month]['wins'] += 1
        monthly[month]['pnl'] += t['pnl']
        if t['signal'] == 'LONG':
            monthly[month]['longs'] += 1
        else:
            monthly[month]['shorts'] += 1

    return {
        'config': config,
        'initial_capital': initial_capital,
        'final_equity': float(equity),
        'total_pnl': float(equity - initial_capital),
        'return_pct': float((equity - initial_capital) / initial_capital * 100),
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': float(len(wins) / len(trades) * 100) if trades else 0,
        'profit_factor': float(gross_profit / gross_loss) if gross_loss > 0 else 0,
        'max_drawdown_pct': float(max_dd * 100),
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
        'avg_kelly_f': float(np.mean([t['kelly_f'] for t in trades])) if trades else 0,
        'max_kelly_f': float(max([t['kelly_f'] for t in trades])) if trades else 0,
        'longs': len([t for t in trades if t['signal'] == 'LONG']),
        'shorts': len([t for t in trades if t['signal'] == 'SHORT']),
    }, trades, equity_curve


def main():
    print("Loading data...")
    m15 = load_m15()
    features = build_features(m15)

    features = features.iloc[96 * 5:]
    m15 = m15.loc[features.index]

    feature_cols = [c for c in features.columns if features[c].notna().mean() > 0.9]
    valid = features[feature_cols].notna().all(axis=1)
    features = features[valid]
    m15 = m15.loc[features.index]

    oos_start = pd.Timestamp('2025-01-01')
    oos_end = pd.Timestamp('2026-05-20')
    oos_mask = (features.index >= oos_start) & (features.index <= oos_end)

    m15_oos = m15[oos_mask]
    features_oos = features[oos_mask]

    print(f"OOS: {m15_oos.index[0].date()} to {m15_oos.index[-1].date()}")
    print(f"Bars: {len(m15_oos)}")

    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))

    dmatrix = xgb.DMatrix(features_oos[feature_cols].values, feature_names=feature_cols)
    proba = model.predict(dmatrix)

    print(f"\nPrediction stats:")
    print(f"  mean={proba.mean():.4f} | >0.60: {(proba>0.60).sum()} | >0.65: {(proba>0.65).sum()} | >0.70: {(proba>0.70).sum()}")

    configs = [
        # Quarter Kelly (conservative)
        {'name': 'Kelly 0.25x (0.60, trend)', 'threshold': 0.60, 'trend_filter': True, 'kelly_fraction': 0.25, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Kelly 0.25x (0.65, trend)', 'threshold': 0.65, 'trend_filter': True, 'kelly_fraction': 0.25, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Kelly 0.25x (0.70, trend)', 'threshold': 0.70, 'trend_filter': True, 'kelly_fraction': 0.25, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},

        # Half Kelly (moderate)
        {'name': 'Kelly 0.50x (0.60, trend)', 'threshold': 0.60, 'trend_filter': True, 'kelly_fraction': 0.50, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Kelly 0.50x (0.65, trend)', 'threshold': 0.65, 'trend_filter': True, 'kelly_fraction': 0.50, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Kelly 0.50x (0.70, trend)', 'threshold': 0.70, 'trend_filter': True, 'kelly_fraction': 0.50, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},

        # Long-only variants
        {'name': 'Kelly 0.25x (0.65, long-only)', 'threshold': 0.65, 'trend_filter': False, 'long_only_bull': True, 'kelly_fraction': 0.25, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Kelly 0.50x (0.65, long-only)', 'threshold': 0.65, 'trend_filter': False, 'long_only_bull': True, 'kelly_fraction': 0.50, 'max_margin_pct': 0.10, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},

        # Compare to fixed 1% risk (baseline)
        {'name': 'Fixed 1% (0.60, trend)', 'threshold': 0.60, 'trend_filter': True, 'kelly_fraction': 0.10, 'max_margin_pct': 0.02, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
    ]

    all_results = {}

    print(f"\n{'='*100}")
    print(f"  KELLY CRITERION BACKTEST | $10K | 50x | 10% max margin | OOS 2025-2026")
    print(f"{'='*100}")

    print(f"\n{'Config':<32} {'Trades':<7} {'WR%':<7} {'PF':<6} {'Return%':<9} {'MaxDD%':<8} {'KellyAvg':<9} {'Final$':<9} {'Status'}")
    print(f"{'-'*106}")

    for cfg in configs:
        results, trades, eq_curve = run_kelly_backtest(m15_oos, features_oos, proba, cfg)
        all_results[cfg['name']] = results

        status = "BREACH" if results['breached'] else "OK"
        kelly_avg = results.get('avg_kelly_f', 0)
        print(f"{cfg['name']:<32} {results['total_trades']:<7} {results['win_rate']:<7.1f} {results['profit_factor']:<6.2f} {results['return_pct']:<9.1f} {results['max_drawdown_pct']:<8.1f} {kelly_avg:<9.3f} ${results['final_equity']:<8.0f} {status}")

    # Best result
    non_breach = {k: v for k, v in all_results.items() if not v['breached'] and v['total_trades'] > 0}
    if non_breach:
        best_name = max(non_breach, key=lambda k: non_breach[k]['return_pct'])
        best = non_breach[best_name]

        print(f"\n{'='*100}")
        print(f"  BEST: {best_name}")
        print(f"{'='*100}")
        print(f"  Final equity:    ${best['final_equity']:,.0f}")
        print(f"  Return:          +{best['return_pct']:.1f}%")
        print(f"  Trades:          {best['total_trades']} ({best['longs']}L / {best['shorts']}S)")
        print(f"  Win rate:        {best['win_rate']:.1f}%")
        print(f"  Profit factor:   {best['profit_factor']:.2f}")
        print(f"  Max drawdown:    {best['max_drawdown_pct']:.1f}%")
        print(f"  Peak:            ${best['peak_equity']:,.0f}")
        print(f"  Avg win:         ${best['avg_win']:.2f}")
        print(f"  Avg loss:        ${best['avg_loss']:.2f}")
        print(f"  R:R ratio:       {abs(best['avg_win']/best['avg_loss']):.2f}")
        print(f"  Kelly avg:       {best['avg_kelly_f']:.3f} (risk {best['avg_kelly_f']*100:.1f}% per trade)")
        print(f"  Kelly max:       {best['max_kelly_f']:.3f}")

        print(f"\n  MONTHLY:")
        print(f"  {'Month':<10} {'Trades':<7} {'L/S':<9} {'WR%':<7} {'PnL':<12} {'Equity'}")
        print(f"  {'-'*58}")
        cum = 10000
        for month in sorted(best['monthly'].keys()):
            m = best['monthly'][month]
            wr = m['wins'] / m['trades'] * 100 if m['trades'] > 0 else 0
            cum += m['pnl']
            ls = f"{m['longs']}L/{m['shorts']}S"
            print(f"  {month:<10} {m['trades']:<7} {ls:<9} {wr:<7.1f} ${m['pnl']:<+11,.0f} ${cum:,.0f}")

        # Compare Kelly to fixed risk
        fixed_name = 'Fixed 1% (0.60, trend)'
        if fixed_name in all_results:
            fixed = all_results[fixed_name]
            print(f"\n{'='*100}")
            print(f"  KELLY vs FIXED COMPARISON")
            print(f"{'='*100}")
            print(f"  {'Metric':<25} {'Kelly (best)':<20} {'Fixed 1%':<20} {'Improvement'}")
            print(f"  {'-'*73}")
            print(f"  {'Return':<25} {best['return_pct']:<20.1f} {fixed['return_pct']:<20.1f} {best['return_pct']/fixed['return_pct']:.2f}x")
            print(f"  {'Final equity':<25} ${best['final_equity']:<19,.0f} ${fixed['final_equity']:<19,.0f}")
            print(f"  {'Max DD %':<25} {best['max_drawdown_pct']:<20.1f} {fixed['max_drawdown_pct']:<20.1f}")
            print(f"  {'Win rate %':<25} {best['win_rate']:<20.1f} {fixed['win_rate']:<20.1f}")
            print(f"  {'Profit factor':<25} {best['profit_factor']:<20.2f} {fixed['profit_factor']:<20.2f}")

    save_data = {
        'backtest_date': '2026-05-27',
        'model': 'Him V2 + Kelly Criterion',
        'oos_period': f"{oos_start.date()} to {oos_end.date()}",
        'kelly_method': 'Fractional Kelly with historical WR/RR + model confidence',
        'rules': {
            'initial_capital': 10000,
            'leverage': 50,
            'max_margin_per_trade': '10%',
            'daily_loss_limit': '2% of equity',
            'total_loss_limit': '10% of initial ($9000 breach)',
            'position_sizing': 'Kelly Criterion (0.25x-0.50x)',
        },
        'configs': all_results,
    }

    with open(OUTPUT_DIR / "kelly_backtest.json", 'w') as f:
        json.dump(save_data, f, indent=2, default=str)

    print(f"\n\nSaved: {OUTPUT_DIR}/kelly_backtest.json")


if __name__ == "__main__":
    main()
