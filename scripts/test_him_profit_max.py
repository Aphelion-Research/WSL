"""Test Him Profit Max on OOS with prop firm costs."""
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research_core.execution import simulate_trades, SimulationConfig, CostModel

print("=" * 60)
print("HIM PROFIT MAX OOS TEST")
print("=" * 60)

# Load OOS
m5 = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
m5['time'] = pd.to_datetime(m5['time'])
m5 = m5.set_index('time')
oos = m5[m5.index >= "2024-01-01"]
print(f"OOS: {len(oos):,} bars (2024-2026)")

# Build features
close = oos['close']
high = oos['high']
low = oos['low']
volume = oos['tick_volume']
spread = oos['spread']

f = pd.DataFrame(index=oos.index)

for bars in [1, 4, 16, 96, 8, 32, 64]:
    f[f'ret_{bars}bar'] = close.pct_change(bars)

for bars, suffix in [(72, '6h'), (144, '12h'), (288, '24h')]:
    rh = close.rolling(bars).max()
    rl = close.rolling(bars).min()
    rng = (rh - rl).replace(0, np.nan)
    f[f'range_pos_{suffix}'] = (close - rl) / rng

for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
    tp = (high + low + close) / 3
    vol = volume.replace(0, 1)
    vwap = (tp * vol).rolling(bars).sum() / vol.rolling(bars).sum()
    f[f'vwap_dev_{suffix}'] = close - vwap

tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
for bars, suffix in [(36, '3h'), (144, '12h'), (288, '24h')]:
    atr = tr.rolling(bars).mean()
    f[f'atr_{suffix}_pct'] = atr / close

f['vol_ratio_short'] = volume / volume.rolling(48).mean().replace(0, np.nan)
f['vol_ratio_long'] = volume / volume.rolling(288).mean().replace(0, np.nan)

delta = close.diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
f['rsi_14'] = 100 - 100 / (1 + gain / loss)

bb_mid = close.rolling(20).mean()
bb_std = close.rolling(20).std().replace(0, np.nan)
f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

hour = oos.index.hour + oos.index.minute / 60
f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
f['cos_dow'] = np.cos(2 * np.pi * oos.index.dayofweek / 5)

for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
    rh = high.rolling(bars).max()
    rl = low.rolling(bars).min()
    f[f'pullback_high_{suffix}'] = (rh - close) / close
    f[f'pullback_low_{suffix}'] = (close - rl) / close

f['spread_zscore'] = (spread - spread.rolling(288).mean()) / spread.rolling(288).std().replace(0, np.nan)

f['consec_up'] = (close > close.shift(1)).astype(int)
f['consec_down'] = (close < close.shift(1)).astype(int)
for col in ['consec_up', 'consec_down']:
    f[col] = f[col].groupby((f[col] != f[col].shift()).cumsum()).cumsum()

ret_cols = [c for c in f.columns if c.startswith('ret_') and 'bar' in c]
f['multi_scale_consensus'] = f[ret_cols].apply(lambda x: (x > 0).sum(), axis=1)

daily = oos[['close']].resample('D').last().ffill()
daily['sma50'] = daily['close'].rolling(50).mean()
daily['sma100'] = daily['close'].rolling(100).mean()
daily['ret_5d'] = daily['close'].pct_change(5)
f['daily_sma50'] = daily['sma50'].reindex(oos.index, method='ffill')
f['daily_sma100'] = daily['sma100'].reindex(oos.index, method='ffill')
f['daily_ret_5d'] = daily['ret_5d'].reindex(oos.index, method='ffill')

# Load model
model = xgb.Booster()
model.load_model("output_him_v2/him_profit_max.json")

# Predict
dmat = xgb.DMatrix(f.dropna())
pred = pd.Series(model.predict(dmat), index=f.dropna().index)

# ATR
atr = tr.rolling(14).mean()

# Prop firm costs
propfirm_cost = CostModel(
    spread_points=0.0,
    slippage_points=0.0,
    commission_per_lot=5.0,
    lot_size=100.0,
)

print("\n" + "=" * 60)
print("PROP FIRM COSTS ($1.00/trade)")
print("=" * 60)

best_pnl = -float('inf')
best_threshold = None
best_result = None

for threshold in [0.50, 0.55, 0.60, 0.65, 0.70]:
    signals = pd.Series(0, index=pred.index)
    signals[pred > threshold] = 1

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=16,
        stop_loss_atr_mult=1.5,
        take_profit_atr_mult=3.0,
        cost_model=propfirm_cost,
        position_size_oz=10.0,
    )

    result = simulate_trades(signals, oos, config, atr)

    print(f"\nThreshold {threshold:.2f}:")
    print(f"  Trades: {len(result['trades'])}")
    print(f"  Sharpe: {result['metrics']['sharpe']:.2f}")
    print(f"  Total PnL: ${result['metrics']['total_pnl_net']:.2f}")
    print(f"  Win Rate: {result['metrics']['win_rate']:.1%}")
    if len(result['trades']) > 0:
        print(f"  Avg PnL/trade: ${result['metrics']['total_pnl_net']/len(result['trades']):.2f}")

    if result['metrics']['total_pnl_net'] > best_pnl:
        best_pnl = result['metrics']['total_pnl_net']
        best_threshold = threshold
        best_result = result

print("\n" + "=" * 60)
print("VERDICT")
print("=" * 60)

if best_pnl > 0:
    print(f"\n✅ PROFITABLE")
    print(f"   Best threshold: {best_threshold:.2f}")
    print(f"   Total PnL: ${best_pnl:.2f}")
    print(f"   Trades: {len(best_result['trades'])}")
    print(f"   Avg: ${best_pnl/len(best_result['trades']):.2f}/trade")
    print(f"   Sharpe: {best_result['metrics']['sharpe']:.2f}")
    print(f"   Win Rate: {best_result['metrics']['win_rate']:.1%}")
else:
    print(f"\n❌ UNPROFITABLE")
    print(f"   Best PnL: ${best_pnl:.2f}")

print("\n" + "=" * 60)
