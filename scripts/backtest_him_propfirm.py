"""
Prop firm backtest for "Him" model.
Rules: 10K, 50x leverage, 2% daily loss on equity (floating), 10% total loss fixed ($9000 breach).
Trend filter: LONG only in bull, SHORT only in bear.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import xgboost as xgb
import json

DATA_DIR = Path("data")
MODEL_PATH = Path("models/Him/Him.json")
OUTPUT_DIR = Path("models/Him")


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


def run_propfirm_backtest(m15, features, proba, config):
    """
    Prop firm backtest with proper risk management.

    Config keys:
      threshold: confidence threshold
      trend_filter: bool - only long in bull, short in bear
      long_only_bull: bool - only take long trades in bull regime
      risk_per_trade: fraction of equity to risk (default 0.01)
      stop_atr_mult: ATR multiplier for stop loss (default 1.5)
      tp_atr_mult: ATR multiplier for take profit (default 3.0)
    """
    threshold = config['threshold']
    trend_filter = config.get('trend_filter', True)
    long_only_bull = config.get('long_only_bull', False)
    risk_pct = config.get('risk_per_trade', 0.01)
    stop_mult = config.get('stop_atr_mult', 1.5)
    tp_mult = config.get('tp_atr_mult', 3.0)
    leverage = 50
    initial_capital = 10000.0
    daily_loss_limit = 0.02  # 2% of equity (floating)
    total_loss_breach = 9000.0  # 10% of initial = $9000 minimum equity

    equity = initial_capital
    peak_equity = initial_capital
    daily_start_equity = initial_capital
    current_date = None
    daily_pnl = 0.0

    trades = []
    equity_curve = []
    breached = False
    breach_reason = None

    close = m15['close'].values
    high = m15['high'].values
    low = m15['low'].values
    dates = m15.index

    # ATR for position sizing (use 12-bar ATR = 3h)
    tr = np.maximum(high - low, np.maximum(
        np.abs(high - np.roll(close, 1)),
        np.abs(low - np.roll(close, 1))
    ))
    tr[0] = high[0] - low[0]
    atr = pd.Series(tr).rolling(12).mean().values

    daily_bull = features['daily_bull'].values
    daily_bear = features['daily_bear'].values

    i = 0
    in_position = False

    while i < len(proba):
        dt = dates[i]

        # Check breach
        if equity <= total_loss_breach:
            breached = True
            breach_reason = f"Total loss breach: equity ${equity:.0f} <= ${total_loss_breach:.0f}"
            break

        # New day reset
        if current_date is None or dt.date() != current_date:
            current_date = dt.date()
            daily_start_equity = equity
            daily_pnl = 0.0

        # Check daily loss limit (2% of current day start equity)
        daily_limit = daily_start_equity * daily_loss_limit
        if daily_pnl <= -daily_limit:
            # Skip rest of day
            while i < len(proba) and dates[i].date() == current_date:
                equity_curve.append({'time': dates[i], 'equity': equity})
                i += 1
            continue

        if not in_position and not np.isnan(proba[i]) and not np.isnan(atr[i]) and atr[i] > 0:
            p = proba[i]
            signal = None

            if p > threshold:
                signal = 'LONG'
            elif p < (1 - threshold):
                signal = 'SHORT'

            # Apply trend filter
            if signal and trend_filter:
                if signal == 'LONG' and daily_bull[i] != 1:
                    signal = None
                if signal == 'SHORT' and daily_bear[i] != 1:
                    signal = None

            # Long-only bull mode
            if signal and long_only_bull:
                if signal == 'SHORT':
                    signal = None
                if signal == 'LONG' and daily_bull[i] != 1:
                    signal = None

            if signal:
                entry_price = close[i]
                stop_distance = atr[i] * stop_mult
                tp_distance = atr[i] * tp_mult

                # Position size: risk X% of equity
                risk_amount = equity * risk_pct
                # Lots = risk / (stop distance in price) * point value
                # For XAU/USD: 1 lot = 100 oz, so $1 move = $100/lot
                oz_per_lot = 100
                dollar_per_pip = oz_per_lot  # $1 move in gold = $100 per lot
                lots = risk_amount / (stop_distance * oz_per_lot)

                # Cap by leverage
                max_lots = (equity * leverage) / (entry_price * oz_per_lot)
                lots = min(lots, max_lots)

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

                # Simulate trade over next bars (max 16 bars = 4h horizon)
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
                    else:  # SHORT
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

                # If no stop/tp hit, exit at close of bar 16
                if exit_price is None:
                    exit_bar = min(i + 16, len(close) - 1)
                    exit_price = close[exit_bar]
                    exit_reason = 'timeout'

                if signal == 'LONG':
                    trade_pnl = (exit_price - entry_price) * lots * oz_per_lot
                else:
                    trade_pnl = (entry_price - exit_price) * lots * oz_per_lot

                equity += trade_pnl
                daily_pnl += trade_pnl
                peak_equity = max(peak_equity, equity)

                trades.append({
                    'entry_time': str(dt),
                    'exit_time': str(dates[exit_bar]),
                    'signal': signal,
                    'entry_price': float(entry_price),
                    'exit_price': float(exit_price),
                    'stop_price': float(stop_price),
                    'tp_price': float(tp_price),
                    'lots': float(lots),
                    'pnl': float(trade_pnl),
                    'exit_reason': exit_reason,
                    'proba': float(p),
                    'equity_after': float(equity),
                })

                # Skip to exit bar
                for k in range(i, exit_bar + 1):
                    equity_curve.append({'time': dates[k], 'equity': equity})
                i = exit_bar + 1
                continue

        equity_curve.append({'time': dt, 'equity': equity})
        i += 1

    # Results
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]

    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1

    # Max drawdown from equity curve
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

    # Monthly breakdown
    monthly = {}
    for t in trades:
        month = t['entry_time'][:7]
        if month not in monthly:
            monthly[month] = {'trades': 0, 'wins': 0, 'pnl': 0}
        monthly[month]['trades'] += 1
        if t['pnl'] > 0:
            monthly[month]['wins'] += 1
        monthly[month]['pnl'] += t['pnl']

    results = {
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
    }

    return results, trades, equity_curve


def main():
    print("Loading data and building features...")
    m15 = load_m15()
    features = build_features(m15)

    # Trim warmup
    features = features.iloc[96 * 3:]
    m15 = m15.loc[features.index]

    # Clean
    feature_cols = [c for c in features.columns if features[c].notna().mean() > 0.9]
    valid = features[feature_cols].notna().all(axis=1)
    features = features[valid]
    m15 = m15.loc[features.index]

    # OOS period: last year
    oos_start = pd.Timestamp('2025-05-20')
    oos_end = pd.Timestamp('2026-05-20')
    oos_mask = (features.index >= oos_start) & (features.index <= oos_end)

    m15_oos = m15[oos_mask]
    features_oos = features[oos_mask]

    print(f"OOS period: {m15_oos.index[0]} to {m15_oos.index[-1]}")
    print(f"OOS bars: {len(m15_oos)}")

    # Load model and predict
    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))

    dmatrix = xgb.DMatrix(features_oos[feature_cols].values, feature_names=feature_cols)
    proba = model.predict(dmatrix)

    print(f"Predictions: mean={proba.mean():.4f}, >0.55: {(proba>0.55).sum()}, >0.60: {(proba>0.60).sum()}, >0.65: {(proba>0.65).sum()}")

    # Run multiple configurations
    configs = [
        {'name': 'Aggressive (0.55, trend-filter)', 'threshold': 0.55, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Moderate (0.58, trend-filter)', 'threshold': 0.58, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Conservative (0.60, trend-filter)', 'threshold': 0.60, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Ultra-conservative (0.65, trend-filter)', 'threshold': 0.65, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Long-only Bull (0.55)', 'threshold': 0.55, 'trend_filter': False, 'long_only_bull': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Long-only Bull (0.60)', 'threshold': 0.60, 'trend_filter': False, 'long_only_bull': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Tight stop (0.58, trend, 1.0 ATR stop)', 'threshold': 0.58, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.0, 'tp_atr_mult': 2.5},
        {'name': 'Wide RR (0.58, trend, 2:4 ATR)', 'threshold': 0.58, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 2.0, 'tp_atr_mult': 4.0},
    ]

    all_results = {}

    print(f"\n{'='*80}")
    print(f"PROP FIRM BACKTEST: Him Model | 10K | 50x | 2% daily / 10% total loss")
    print(f"Period: {oos_start.date()} to {oos_end.date()}")
    print(f"{'='*80}")

    print(f"\n{'Config':<40} {'Trades':<8} {'WR%':<8} {'PF':<6} {'Return%':<10} {'MaxDD%':<9} {'Breach'}")
    print(f"{'-'*90}")

    for cfg in configs:
        results, trades, eq_curve = run_propfirm_backtest(m15_oos, features_oos, proba, cfg)
        all_results[cfg['name']] = results

        breach_str = "YES" if results['breached'] else "NO"
        print(f"{cfg['name']:<40} {results['total_trades']:<8} {results['win_rate']:<8.1f} {results['profit_factor']:<6.2f} {results['return_pct']:<10.1f} {results['max_drawdown_pct']:<9.1f} {breach_str}")

    # Print best config details
    best_name = max(
        [k for k, v in all_results.items() if not v['breached']],
        key=lambda k: all_results[k]['return_pct'],
        default=None
    )

    if best_name:
        best = all_results[best_name]
        print(f"\n{'='*80}")
        print(f"BEST NON-BREACH CONFIG: {best_name}")
        print(f"{'='*80}")
        print(f"  Final equity:  ${best['final_equity']:.0f}")
        print(f"  Return:        {best['return_pct']:.1f}%")
        print(f"  Trades:        {best['total_trades']}")
        print(f"  Win rate:      {best['win_rate']:.1f}%")
        print(f"  Profit factor: {best['profit_factor']:.2f}")
        print(f"  Max drawdown:  {best['max_drawdown_pct']:.1f}%")
        print(f"  Peak equity:   ${best['peak_equity']:.0f}")
        print(f"  Avg win:       ${best['avg_win']:.2f}")
        print(f"  Avg loss:      ${best['avg_loss']:.2f}")
        print(f"  Exit reasons:  TP={best['exit_reasons']['tp']}, Stop={best['exit_reasons']['stop']}, Timeout={best['exit_reasons']['timeout']}")

        print(f"\n  Monthly breakdown:")
        print(f"  {'Month':<10} {'Trades':<8} {'Wins':<8} {'WR%':<8} {'PnL':<12}")
        print(f"  {'-'*46}")
        cumulative = 10000
        for month in sorted(best['monthly'].keys()):
            m = best['monthly'][month]
            wr = m['wins'] / m['trades'] * 100 if m['trades'] > 0 else 0
            cumulative += m['pnl']
            print(f"  {month:<10} {m['trades']:<8} {m['wins']:<8} {wr:<8.1f} ${m['pnl']:<+11.0f} (eq: ${cumulative:.0f})")

    # Save all results
    save_results = {
        'backtest_date': '2026-05-27',
        'oos_period': f"{oos_start.date()} to {oos_end.date()}",
        'oos_bars': len(m15_oos),
        'model': 'Him',
        'rules': {
            'initial_capital': 10000,
            'leverage': 50,
            'daily_loss_limit': '2% of equity (floating)',
            'total_loss_limit': '10% of initial ($9000 breach)',
        },
        'configs': all_results,
    }

    output_file = OUTPUT_DIR / "propfirm_backtest.json"
    with open(output_file, 'w') as f:
        json.dump(save_results, f, indent=2, default=str)

    print(f"\nResults saved: {output_file}")


if __name__ == "__main__":
    main()
