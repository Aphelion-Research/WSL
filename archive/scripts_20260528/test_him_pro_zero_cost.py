"""Test Him Pro at zero costs to isolate edge."""
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from research_core.execution import simulate_trades, SimulationConfig, CostModel

print("=" * 60)
print("HIM PRO AT ZERO COSTS")
print("=" * 60)

# Load OOS
m5 = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
m5['time'] = pd.to_datetime(m5['time'])
m5 = m5.set_index('time')
oos = m5[m5.index >= "2024-01-01"]
print(f"OOS: {len(oos):,} bars")

# Build features
close = oos['close']
high = oos['high']
low = oos['low']
volume = oos['tick_volume']

f = pd.DataFrame(index=oos.index)

for bars in [1, 2, 4, 8, 16, 32, 64, 96]:
    f[f'ret_{bars}b'] = close.pct_change(bars)

for bars in [8, 16, 32, 64]:
    f[f'vol_{bars}b'] = close.rolling(bars).std() / close

for bars in [16, 48, 96, 288]:
    rh = high.rolling(bars).max()
    rl = low.rolling(bars).min()
    rng = (rh - rl).replace(0, np.nan)
    f[f'range_pos_{bars}b'] = (close - rl) / rng

tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
for bars in [14, 28, 56]:
    f[f'atr_{bars}b'] = tr.rolling(bars).mean() / close

for period in [7, 14, 28]:
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean().replace(0, np.nan)
    f[f'rsi_{period}'] = 100 - 100 / (1 + gain / loss)

f['vol_ratio_8'] = volume / volume.rolling(8).mean().replace(0, np.nan)
f['vol_ratio_48'] = volume / volume.rolling(48).mean().replace(0, np.nan)
f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

for bars in [10, 20, 50, 100]:
    ma = close.rolling(bars).mean()
    f[f'close_ma{bars}'] = (close - ma) / close

hour = oos.index.hour
f['london'] = ((hour >= 8) & (hour < 16)).astype(int)
f['ny'] = ((hour >= 13) & (hour < 21)).astype(int)
f['asia'] = ((hour >= 0) & (hour < 8)).astype(int)
f['overlap'] = ((hour >= 13) & (hour < 16)).astype(int)

vol_pct = close.rolling(96).std().rank(pct=True)
f['high_vol'] = (vol_pct > 0.7).astype(int)

f['mom_8'] = (close > close.shift(8)).astype(int)
f['mom_16'] = (close > close.shift(16)).astype(int)

# Load ensemble
models = []
for i in range(1, 4):
    model = xgb.Booster()
    model.load_model(f"output_him_pro/him_pro_model_{i}.json")
    models.append(model)

# Predict
X = f.dropna()
dmat = xgb.DMatrix(X)

preds = []
for model in models:
    preds.append(model.predict(dmat))
pred = pd.Series(np.mean(preds, axis=0), index=X.index)

# ATR
atr = tr.rolling(14).mean()

# Zero costs
zero_cost = CostModel(
    spread_points=0.0,
    slippage_points=0.0,
    commission_per_lot=0.0,
)

print("\nTesting at ZERO costs...")
for threshold in [0.50, 0.55, 0.60, 0.65, 0.70]:
    signals = pd.Series(0, index=pred.index)
    signals[pred > threshold] = 1

    config = SimulationConfig(
        signal_at_bar_i_entry_at_bar_i_plus_n=1,
        hold_bars=12,
        stop_loss_atr_mult=1.5,
        take_profit_atr_mult=3.0,
        cost_model=zero_cost,
        position_size_oz=10.0,
    )

    result = simulate_trades(signals, oos, config, atr)

    print(f"\nThreshold {threshold:.2f}:")
    print(f"  Trades: {len(result['trades'])}")
    print(f"  PnL: ${result['metrics']['total_pnl_net']:.2f}")
    print(f"  Win Rate: {result['metrics']['win_rate']:.1%}")
    if len(result['trades']) > 0:
        print(f"  Avg/trade: ${result['metrics']['total_pnl_net']/len(result['trades']):.2f}")

print("\n" + "=" * 60)
