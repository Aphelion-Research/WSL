"""
Him V2 Threshold Grid Search (OOS only)
========================================
Test thresholds [0.50, 0.55, 0.60, 0.65, 0.70, 0.75] on OOS data only.
No training. Locked model. Find best threshold for forward trading.

Output: Sharpe, PF, DD, trades for each threshold → recommend best.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from research_core.execution import simulate_trades, SimulationConfig, CostModel
from research_core.diagnostics import compute_stability_metrics

# Paths
DATA_PATH = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
MODEL_PATH = Path("models/Him/Him_V2_MultiScale.json")
OUTPUT_PATH = Path("output_him_v2/threshold_grid_oos.json")

# OOS period
OOS_START = "2024-01-01"

# Locked execution params
HOLD_BARS = 16  # 80 min
STOP_ATR = 1.5
TP_ATR = 3.0

# Threshold grid
THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]


def build_multiscale_features(m5):
    """Build multi-timeframe features."""
    close = m5['close']
    high = m5['high']
    low = m5['low']
    volume = m5['tick_volume']
    spread = m5['spread']

    f = pd.DataFrame(index=m5.index)

    # Multi-scale returns (match model feature order)
    for bars in [1, 4, 16, 96, 8, 32, 64]:
        f[f'ret_{bars}bar'] = close.pct_change(bars)

    # Range position
    for bars, suffix in [(72, '6h'), (144, '12h'), (288, '24h')]:
        rh = close.rolling(bars).max()
        rl = close.rolling(bars).min()
        rng = (rh - rl).replace(0, np.nan)
        f[f'range_pos_{suffix}'] = (close - rl) / rng

    # VWAP deviation
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        tp = (high + low + close) / 3
        vol = volume.replace(0, 1)
        vwap = (tp * vol).rolling(bars).sum() / vol.rolling(bars).sum()
        f[f'vwap_dev_{suffix}'] = close - vwap

    # ATR
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
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
    f['consec_up'] = (close > close.shift(1)).astype(int)
    f['consec_down'] = (close < close.shift(1)).astype(int)
    for col in ['consec_up', 'consec_down']:
        f[col] = f[col].groupby((f[col] != f[col].shift()).cumsum()).cumsum()

    # Multi-scale consensus
    ret_cols = [c for c in f.columns if c.startswith('ret_') and 'bar' in c]
    f['multi_scale_consensus'] = f[ret_cols].apply(lambda x: (x > 0).sum(), axis=1)

    # Daily aggregates
    daily = m5[['close']].resample('D').last().ffill()
    daily['sma50'] = daily['close'].rolling(50).mean()
    daily['sma100'] = daily['close'].rolling(100).mean()
    daily['ret_5d'] = daily['close'].pct_change(5)

    f['daily_sma50'] = daily['sma50'].reindex(m5.index, method='ffill')
    f['daily_sma100'] = daily['sma100'].reindex(m5.index, method='ffill')
    f['daily_ret_5d'] = daily['ret_5d'].reindex(m5.index, method='ffill')

    return f


def main():
    print("=" * 60)
    print("Him V2 Threshold Grid Search (OOS Only)")
    print("=" * 60)
    print(f"Model: {MODEL_PATH}")
    print(f"OOS: {OOS_START} onward")
    print(f"Thresholds: {THRESHOLDS}")
    print(f"Hold: {HOLD_BARS} bars, Stop: {STOP_ATR} ATR, TP: {TP_ATR} ATR")
    print()

    # Load data
    print("Loading M5 data...")
    m5 = pd.read_parquet(DATA_PATH)
    m5['time'] = pd.to_datetime(m5['time'])
    m5 = m5.set_index('time')
    oos = m5[m5.index >= OOS_START]
    print(f"  OOS: {len(oos):,} bars ({oos.index[0]} to {oos.index[-1]})")

    # Load model
    print("Loading model...")
    model = xgb.Booster()
    model.load_model(str(MODEL_PATH))

    # Build features
    print("Building features...")
    features = build_multiscale_features(oos)

    # Get predictions
    print("Generating predictions...")
    dmat = xgb.DMatrix(features.dropna())
    predictions = pd.Series(model.predict(dmat), index=features.dropna().index)
    print(f"  Predictions: {len(predictions):,}")

    # Compute ATR
    print("Computing ATR...")
    tr = pd.concat([
        oos['high'] - oos['low'],
        (oos['high'] - oos['close'].shift(1)).abs(),
        (oos['low'] - oos['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean()

    # Configure simulation
    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=HOLD_BARS,
        stop_loss_atr_mult=STOP_ATR,
        take_profit_atr_mult=TP_ATR,
        cost_model=CostModel.xauusd_baseline(),
        position_size_oz=10.0,
    )

    # Run grid search
    results = {}
    print("\n" + "=" * 60)
    print("Running threshold grid search...")
    print("=" * 60)

    for threshold in THRESHOLDS:
        print(f"\nThreshold: {threshold}")

        # Generate signals
        signals = pd.Series(0, index=predictions.index)
        signals[predictions > threshold] = 1  # Long only

        # Simulate
        result = simulate_trades(signals, oos, config, atr)

        metrics = result['metrics']
        stability = compute_stability_metrics(result['trades'], result['equity_curve'])

        # Store results
        results[str(threshold)] = {
            'threshold': threshold,
            'num_trades': metrics['num_trades'],
            'win_rate': metrics['win_rate'],
            'sharpe': metrics['sharpe'],
            'total_pnl_net': metrics['total_pnl_net'],
            'max_drawdown': metrics['max_drawdown'],
            'profit_factor': metrics['total_pnl_net'] / abs(metrics['total_pnl_net'] - 2 * metrics['total_pnl_net']) if metrics['total_pnl_net'] != 0 else 0,
            'avg_win': metrics.get('avg_win', 0),
            'avg_loss': metrics.get('avg_loss', 0),
            'top_5_trades_pct': stability['top_5_trades_pct'],
            'stability_verdict': stability['verdict'],
        }

        print(f"  Trades: {metrics['num_trades']}")
        print(f"  Sharpe: {metrics['sharpe']:.2f}")
        print(f"  PnL: ${metrics['total_pnl_net']:.2f}")
        print(f"  Win Rate: {metrics['win_rate']:.2%}")
        print(f"  Max DD: ${metrics['max_drawdown']:.2f}")

    # Summary table
    print("\n" + "=" * 60)
    print("THRESHOLD COMPARISON")
    print("=" * 60)
    print(f"\n{'Threshold':<12} {'Trades':<8} {'Sharpe':<10} {'PnL':<12} {'Win%':<8} {'MaxDD':<12}")
    print("-" * 70)

    for threshold in THRESHOLDS:
        r = results[str(threshold)]
        print(f"{r['threshold']:<12.2f} {r['num_trades']:<8} {r['sharpe']:<10.2f} ${r['total_pnl_net']:<11.2f} {r['win_rate']*100:<7.1f} ${r['max_drawdown']:<11.2f}")

    # Find best threshold
    best_sharpe = max(results.values(), key=lambda x: x['sharpe'])
    best_pnl = max(results.values(), key=lambda x: x['total_pnl_net'])

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print(f"\nBest Sharpe: {best_sharpe['threshold']:.2f} (Sharpe: {best_sharpe['sharpe']:.2f})")
    print(f"Best PnL: {best_pnl['threshold']:.2f} (PnL: ${best_pnl['total_pnl_net']:.2f})")

    # Save results
    OUTPUT_PATH.parent.mkdir(exist_ok=True, parents=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump({
            'timestamp': pd.Timestamp.now().isoformat(),
            'oos_period': f"{OOS_START} to {oos.index[-1].strftime('%Y-%m-%d')}",
            'thresholds_tested': THRESHOLDS,
            'results': results,
            'best_sharpe_threshold': best_sharpe['threshold'],
            'best_pnl_threshold': best_pnl['threshold'],
        }, f, indent=2)

    print(f"\nResults saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
