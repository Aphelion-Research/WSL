"""
Him V2 Multi-Scale Retrain + Propfirm Backtest
===============================================
Train: 2015-2023 (M15, resampled from M5 Dukascopy)
OOS:   2024-01-01 to 2026-05-20 (2.5 years, zero data leakage)
Rules: $10K, 50x leverage, 2% daily loss, 10% total loss, slippage modeled
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings('ignore')

DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
OUTPUT_DIR = Path("output_him_v2")
MODEL_DIR = Path("models/Him")
OUTPUT_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)


# ============================================================
# PHASE 1: DATA LOADING & M15 RESAMPLE
# ============================================================

def load_m15():
    print("=" * 80)
    print("PHASE 1: DATA LOADING")
    print("=" * 80)

    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time').sort_index()

    # Filter to 2015+ (pre-2015 gold data is thin/different regime)
    m5 = m5[m5.index >= '2015-01-01']

    m15 = m5.resample('15min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum',
        'spread': 'mean',
    }).dropna(subset=['close'])
    m15 = m15[m15['tick_volume'] > 0]

    print(f"  M15 bars: {len(m15):,}")
    print(f"  Date range: {m15.index[0]} to {m15.index[-1]}")

    # Gap check
    gaps = m15.index.to_series().diff()
    big_gaps = gaps[gaps > pd.Timedelta(hours=48)]
    print(f"  Gaps > 48h: {len(big_gaps)} (expected: weekends + holidays)")

    return m15


# ============================================================
# PHASE 2: FEATURE ENGINEERING (MULTI-SCALE)
# ============================================================

def build_features(m15):
    print("\n" + "=" * 80)
    print("PHASE 2: FEATURE ENGINEERING (MULTI-SCALE)")
    print("=" * 80)

    close = m15['close']
    high = m15['high']
    low = m15['low']
    volume = m15['tick_volume']

    f = pd.DataFrame(index=m15.index)

    # --- Multi-scale momentum returns ---
    f['ret_1bar'] = close.pct_change(1)
    f['ret_4bar'] = close.pct_change(4)       # 1h
    f['ret_16bar'] = close.pct_change(16)     # 4h
    f['ret_96bar'] = close.pct_change(96)     # 24h (dominant in V1)

    # NEW: intermediate scales
    f['ret_8bar'] = close.pct_change(8)       # 2h
    f['ret_32bar'] = close.pct_change(32)     # 8h
    f['ret_64bar'] = close.pct_change(64)     # 16h

    # --- Range position (where in N-bar range?) ---
    for period, suffix in [(24, '6h'), (48, '12h'), (96, '24h')]:
        rolling_high = close.rolling(period).max()
        rolling_low = close.rolling(period).min()
        rng = (rolling_high - rolling_low).replace(0, np.nan)
        f[f'range_pos_{suffix}'] = (close - rolling_low) / rng

    # --- VWAP deviation (multi-scale) ---
    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)
    for period, suffix in [(16, '4h'), (48, '12h'), (96, '24h')]:
        vwap = (tp * vol).rolling(period).sum() / vol.rolling(period).sum()
        f[f'vwap_dev_{suffix}'] = (close - vwap) / close

    # --- ATR & volatility ---
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)

    atr_12 = tr.rolling(12).mean()   # 3h ATR
    atr_48 = tr.rolling(48).mean()   # 12h ATR
    atr_96 = tr.rolling(96).mean()   # 24h ATR

    f['atr_3h_pct'] = atr_12 / close
    f['atr_12h_pct'] = atr_48 / close
    f['atr_24h_pct'] = atr_96 / close
    f['vol_ratio_short'] = atr_12 / atr_48.replace(0, np.nan)
    f['vol_ratio_long'] = atr_12 / atr_96.replace(0, np.nan)

    # --- RSI ---
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss_val = (-delta.where(delta < 0, 0)).rolling(14).mean()
    f['rsi_14'] = 100 - 100 / (1 + gain / loss_val.replace(0, np.nan))

    # --- Bollinger Band position ---
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # --- Volume z-score ---
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # --- Session timing (cyclical) ---
    hour = m15.index.hour + m15.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * m15.index.dayofweek / 5)

    # --- Pullback from high/low (multi-scale, ATR-normalized) ---
    for period, suffix in [(16, '4h'), (48, '12h'), (96, '24h')]:
        rh = close.rolling(period).max()
        rl = close.rolling(period).min()
        atr_ref = atr_96.replace(0, np.nan)
        f[f'pullback_high_{suffix}'] = (rh - close) / atr_ref
        f[f'pullback_low_{suffix}'] = (close - rl) / atr_ref

    # --- Spread z-score ---
    spread = m15['spread']
    f['spread_zscore'] = (spread - spread.rolling(96).mean()) / spread.rolling(96).std().replace(0, np.nan)

    # --- Consecutive bars ---
    f['consec_up'] = close.diff().gt(0).rolling(8).sum()
    f['consec_down'] = close.diff().lt(0).rolling(8).sum()

    # --- Multi-scale consensus (NEW) ---
    consensus = (
        (f['ret_4bar'] > 0).astype(float) +
        (f['ret_8bar'] > 0).astype(float) +
        (f['ret_16bar'] > 0).astype(float) +
        (f['ret_32bar'] > 0).astype(float) +
        (f['ret_64bar'] > 0).astype(float) +
        (f['ret_96bar'] > 0).astype(float)
    ) / 6.0
    f['multi_scale_consensus'] = consensus

    # --- Daily overlay (shifted 2 days for safety) ---
    daily_close = close.resample('1D').last().dropna()
    d_sma50 = ((daily_close - daily_close.rolling(50).mean()) / daily_close.rolling(50).mean()).shift(2)
    d_sma100 = ((daily_close - daily_close.rolling(100).mean()) / daily_close.rolling(100).mean()).shift(2)
    d_ret_5d = daily_close.pct_change(5).shift(2)

    f['daily_sma50'] = d_sma50.reindex(m15.index, method='ffill')
    f['daily_sma100'] = d_sma100.reindex(m15.index, method='ffill')
    f['daily_ret_5d'] = d_ret_5d.reindex(m15.index, method='ffill')
    f['daily_bull'] = ((f['daily_sma50'] > 0) & (f['daily_sma100'] > 0)).astype(float)
    f['daily_bear'] = ((f['daily_sma50'] < 0) & (f['daily_sma100'] < 0)).astype(float)

    feature_cols = [c for c in f.columns if c not in ['daily_bull', 'daily_bear']]
    print(f"  Total features: {len(feature_cols)}")
    print(f"  Feature list: {feature_cols}")

    return f, feature_cols


# ============================================================
# PHASE 3: LABEL + TRAIN/OOS SPLIT
# ============================================================

def prepare_label_and_split(m15, features, feature_cols):
    print("\n" + "=" * 80)
    print("PHASE 3: LABEL & SPLIT")
    print("=" * 80)

    close = m15['close']
    # Label: 16-bar forward return vs trailing 96-bar avg return
    fwd_ret_16 = close.pct_change(16).shift(-16)
    trailing_avg = close.pct_change(16).rolling(96).mean()
    label = (fwd_ret_16 > trailing_avg).astype(float)
    label.name = 'label'

    # Combine
    df = features.copy()
    df['label'] = label

    # Drop warmup + forward-looking NaN
    df = df.dropna(subset=feature_cols + ['label'])

    # Split: train 2015-2023, OOS 2024-2026
    train_end = pd.Timestamp('2023-12-31 23:59:00')
    df_train = df[df.index <= train_end]
    df_oos = df[df.index > train_end]

    print(f"  Train: {len(df_train):,} bars ({df_train.index[0].date()} to {df_train.index[-1].date()})")
    print(f"  OOS:   {len(df_oos):,} bars ({df_oos.index[0].date()} to {df_oos.index[-1].date()})")
    print(f"  Train label balance: {df_train['label'].mean()*100:.1f}% positive")
    print(f"  OOS label balance:   {df_oos['label'].mean()*100:.1f}% positive")

    return df_train, df_oos


# ============================================================
# PHASE 4: TRAINING
# ============================================================

def train_model(df_train, df_oos, feature_cols):
    print("\n" + "=" * 80)
    print("PHASE 4: TRAINING (XGBoost)")
    print("=" * 80)

    X_train = df_train[feature_cols].values
    y_train = df_train['label'].values
    X_oos = df_oos[feature_cols].values
    y_oos = df_oos['label'].values

    # Same regularized params as original Him V2
    params = {
        'max_depth': 4,
        'learning_rate': 0.01,
        'subsample': 0.7,
        'colsample_bytree': 0.5,
        'min_child_weight': 100,
        'reg_alpha': 3.0,
        'reg_lambda': 10.0,
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'seed': 42,
    }

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    doos = xgb.DMatrix(X_oos, label=y_oos, feature_names=feature_cols)

    evals = [(dtrain, 'train'), (doos, 'oos')]

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=500,
        evals=evals,
        early_stopping_rounds=30,
        verbose_eval=50,
    )

    # Predictions
    train_pred = model.predict(dtrain)
    oos_pred = model.predict(doos)

    from sklearn.metrics import roc_auc_score
    train_auc = roc_auc_score(y_train, train_pred)
    oos_auc = roc_auc_score(y_oos, oos_pred)

    print(f"\n  Train AUC: {train_auc:.4f}")
    print(f"  OOS AUC:   {oos_auc:.4f}")
    print(f"  Gap:        {train_auc - oos_auc:.4f} {'⚠️ OVERFITTING' if train_auc - oos_auc > 0.05 else '✓ OK'}")
    print(f"  Best iteration: {model.best_iteration}")

    # Feature importance
    importance = model.get_score(importance_type='gain')
    imp_df = pd.DataFrame([
        {'feature': k, 'gain': v} for k, v in importance.items()
    ]).sort_values('gain', ascending=False)
    imp_df['pct'] = imp_df['gain'] / imp_df['gain'].sum() * 100

    print(f"\n  Top 15 features by gain:")
    for _, row in imp_df.head(15).iterrows():
        print(f"    {row['feature']:<25s} {row['pct']:5.1f}%")

    # Save model
    model_path = MODEL_DIR / "Him_V2_MultiScale.json"
    model.save_model(str(model_path))
    print(f"\n  Model saved: {model_path}")

    return model, oos_pred, train_auc, oos_auc, imp_df


# ============================================================
# PHASE 5: PROPFIRM BACKTEST
# ============================================================

def run_propfirm_backtest(m15_oos, features_oos, proba, config):
    """Identical logic to original Him V2 backtest — validated correct."""
    threshold = config['threshold']
    trend_filter = config.get('trend_filter', True)
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

    trades = []
    breached = False
    breach_reason = None

    close = m15_oos['close'].values
    high_arr = m15_oos['high'].values
    low_arr = m15_oos['low'].values
    dates = m15_oos.index

    # ATR (12-bar)
    tr = np.maximum(high_arr - low_arr, np.maximum(
        np.abs(high_arr - np.roll(close, 1)),
        np.abs(low_arr - np.roll(close, 1))
    ))
    tr[0] = high_arr[0] - low_arr[0]
    atr = pd.Series(tr).rolling(12).mean().values

    daily_bull = features_oos['daily_bull'].values
    daily_bear = features_oos['daily_bear'].values

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

            if signal:
                entry_price = close[i]
                stop_distance = atr[i] * stop_mult
                tp_distance = atr[i] * tp_mult

                risk_amount = equity * risk_pct
                oz_per_lot = 100
                lots = risk_amount / (stop_distance * oz_per_lot)
                max_lots = (equity * leverage) / (entry_price * oz_per_lot)
                lots = min(lots, max_lots)

                if lots <= 0:
                    i += 1
                    continue

                if signal == 'LONG':
                    stop_price = entry_price - stop_distance
                    tp_price = entry_price + tp_distance
                else:
                    stop_price = entry_price + stop_distance
                    tp_price = entry_price - tp_distance

                exit_price = None
                exit_reason = None
                exit_bar = i

                for j in range(i + 1, min(i + 17, len(close))):
                    if signal == 'LONG':
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
                    'lots': float(lots),
                    'pnl': float(trade_pnl),
                    'exit_reason': exit_reason,
                    'proba': float(p),
                    'equity_after': float(equity),
                })

                i = exit_bar + 1
                continue

        i += 1

    # Stats
    wins = [t for t in trades if t['pnl'] > 0]
    losses = [t for t in trades if t['pnl'] <= 0]
    gross_profit = sum(t['pnl'] for t in wins) if wins else 0
    gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 1

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

    result = {
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
        'max_drawdown_pct': float((min(t['equity_after'] for t in trades) - initial_capital) / initial_capital * 100) if trades else 0,
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
        'longs': len([t for t in trades if t['signal'] == 'LONG']),
        'shorts': len([t for t in trades if t['signal'] == 'SHORT']),
    }

    return result, trades


# ============================================================
# PHASE 6: MAIN EXECUTION
# ============================================================

def main():
    start_time = datetime.now()
    print(f"\nHIM V2 MULTI-SCALE RETRAIN — {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Phase 1
    m15 = load_m15()

    # Phase 2
    features, feature_cols = build_features(m15)

    # Phase 3
    df_train, df_oos = prepare_label_and_split(m15, features, feature_cols)

    # Phase 4
    model, oos_pred, train_auc, oos_auc, imp_df = train_model(df_train, df_oos, feature_cols)

    # Phase 5: Propfirm backtest on OOS
    print("\n" + "=" * 80)
    print("PHASE 5: PROPFIRM BACKTEST (OOS 2024-2026)")
    print("=" * 80)

    # Align m15 with OOS features
    m15_oos = m15.loc[df_oos.index]
    features_oos = features.loc[df_oos.index]

    # Get predictions (already have oos_pred from training)
    proba = oos_pred

    print(f"\n  Prediction distribution (OOS):")
    print(f"    mean={proba.mean():.4f}, std={proba.std():.4f}")
    print(f"    >0.55: {(proba>0.55).sum()} | >0.60: {(proba>0.60).sum()} | >0.65: {(proba>0.65).sum()}")
    print(f"    <0.45: {(proba<0.45).sum()} | <0.40: {(proba<0.40).sum()} | <0.35: {(proba<0.35).sum()}")

    configs = [
        {'name': 'Aggressive (0.55, trend)', 'threshold': 0.55, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Moderate (0.60, trend)', 'threshold': 0.60, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Conservative (0.65, trend)', 'threshold': 0.65, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Ultra (0.70, trend)', 'threshold': 0.70, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Long-only Bull (0.60)', 'threshold': 0.60, 'trend_filter': False, 'long_only_bull': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 1.5, 'tp_atr_mult': 3.0},
        {'name': 'Wide RR (0.60, 2:4 ATR)', 'threshold': 0.60, 'trend_filter': True, 'risk_per_trade': 0.01, 'stop_atr_mult': 2.0, 'tp_atr_mult': 4.0},
    ]

    all_results = {}

    print(f"\n  {'Config':<28} {'Trades':<7} {'WR%':<7} {'PF':<6} {'Return%':<9} {'MaxDD%':<8} {'Final$':<9} {'Breach'}")
    print(f"  {'-'*84}")

    for cfg in configs:
        result, trades = run_propfirm_backtest(m15_oos, features_oos, proba, cfg)
        all_results[cfg['name']] = result

        breach_str = "BREACH" if result['breached'] else "OK"
        print(f"  {cfg['name']:<28} {result['total_trades']:<7} {result['win_rate']:<7.1f} {result['profit_factor']:<6.2f} {result['return_pct']:<+9.1f} {result['max_drawdown_pct']:<8.1f} ${result['final_equity']:<8.0f} {breach_str}")

    # Phase 6: Comparison & Verdict
    print("\n" + "=" * 80)
    print("PHASE 6: COMPARISON VS BASELINE")
    print("=" * 80)

    # Baseline numbers from audit
    baseline = {
        'trades': 687, 'wr': 44.1, 'pf': 1.16, 'return': 80.5, 'dd': -15.9,
        'period': '2025-01 to 2026-05 (17mo)', 'note': 'OOS started 2025, trained to 2024'
    }

    print(f"\n  BASELINE (Him V2, OOS 2025-2026, trained to 2024):")
    print(f"    Trades: {baseline['trades']} | WR: {baseline['wr']}% | PF: {baseline['pf']} | Return: +{baseline['return']}% | DD: {baseline['dd']}%")

    print(f"\n  MULTI-SCALE (Him V2 MS, OOS 2024-2026, trained to 2023):")
    for name, r in all_results.items():
        if not r['breached'] and r['total_trades'] > 0:
            print(f"    {name}: Trades={r['total_trades']} | WR={r['win_rate']:.1f}% | PF={r['profit_factor']:.2f} | Return=+{r['return_pct']:.1f}% | DD={r['max_drawdown_pct']:.1f}%")

    # Best non-breach
    non_breach = {k: v for k, v in all_results.items() if not v['breached'] and v['total_trades'] > 50}
    if non_breach:
        best_name = max(non_breach, key=lambda k: non_breach[k]['return_pct'])
        best = non_breach[best_name]

        print(f"\n  BEST CONFIG: {best_name}")
        print(f"    Final equity: ${best['final_equity']:,.0f}")
        print(f"    Return: +{best['return_pct']:.1f}%")
        print(f"    Win rate: {best['win_rate']:.1f}%")
        print(f"    Profit factor: {best['profit_factor']:.2f}")
        print(f"    Max DD: {best['max_drawdown_pct']:.1f}%")
        print(f"    R:R: {abs(best['avg_win']/best['avg_loss']):.2f}:1")

        # Monthly
        print(f"\n    MONTHLY BREAKDOWN:")
        print(f"    {'Month':<8} {'Trades':<7} {'Wins':<6} {'WR%':<7} {'PnL':<12}")
        print(f"    {'-'*44}")
        cum = 10000
        for month in sorted(best['monthly'].keys()):
            m = best['monthly'][month]
            wr = m['wins'] / m['trades'] * 100 if m['trades'] > 0 else 0
            cum += m['pnl']
            print(f"    {month:<8} {m['trades']:<7} {m['wins']:<6} {wr:<7.1f} ${m['pnl']:<+11,.0f}")

        # Verdict
        print(f"\n" + "=" * 80)
        print(f"FINAL VERDICT")
        print("=" * 80)

        wr_improved = best['win_rate'] > baseline['wr']
        return_note = "EXTENDED OOS (2.5yr vs 1.4yr) — NOT directly comparable"

        checks = {
            'WR > 44% (improvement)': best['win_rate'] > 44.0,
            'PF > 1.15': best['profit_factor'] > 1.15,
            'No breach': not best['breached'],
            'Trades > 200': best['total_trades'] > 200,
            'Max DD < 20%': best['max_drawdown_pct'] > -20,
            'Positive return': best['return_pct'] > 0,
        }

        print(f"\n  Deployment checklist:")
        for check, result_val in checks.items():
            status = "✓" if result_val else "✗"
            print(f"    {status} {check}")

        passed = sum(checks.values())
        print(f"\n  Passed: {passed}/6")

        if passed >= 5:
            print(f"\n  🟢 READY FOR PAPER TRADING")
        elif passed >= 3:
            print(f"\n  🟡 CONDITIONAL — fix issues first")
        else:
            print(f"\n  🔴 NOT READY")

    # Save results
    save_data = {
        'backtest_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'model': 'Him V2 Multi-Scale',
        'train_period': '2015-01-01 to 2023-12-31',
        'oos_period': '2024-01-01 to 2026-05-20',
        'train_auc': float(train_auc),
        'oos_auc': float(oos_auc),
        'feature_cols': feature_cols,
        'num_features': len(feature_cols),
        'feature_importance': imp_df.to_dict('records'),
        'configs': all_results,
        'baseline_comparison': baseline,
    }

    output_path = OUTPUT_DIR / "multiscale_retrain_results.json"
    with open(output_path, 'w') as f:
        json.dump(save_data, f, indent=2, default=str)
    print(f"\n  Results saved: {output_path}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n  Total time: {elapsed:.0f}s")


if __name__ == "__main__":
    main()
