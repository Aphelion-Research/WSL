"""Test TUI once without loop."""
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).parent.parent))

MODEL_PATH = "output_him_v2/him_profit_max.json"
THRESHOLD = 0.65
LOOKBACK_BARS = 300

print("Loading model...")
model = xgb.Booster()
model.load_model(MODEL_PATH)
print("✓ Model loaded")

print("\nGetting latest M5 data from domdata...")
# domdata gives M1, need 5x bars for M5 resample
cmd = f"domdata xaurates --count {LOOKBACK_BARS * 5}"
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.returncode != 0:
    print(f"ERROR: domdata failed: {result.stderr}")
    sys.exit(1)

# Parse JSON array
bars = json.loads(result.stdout)

df = pd.DataFrame(bars)
df['time'] = pd.to_datetime(df['time'], unit='s')
df = df.set_index('time')

# Resample to M5
df = df.resample('5min').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'tick_volume': 'sum',
    'spread': 'mean',
}).dropna()

df = df.tail(LOOKBACK_BARS)
print(f"✓ Got {len(df)} M5 bars")

# Build features (abbreviated)
print("\nBuilding features...")
close = df['close']
high = df['high']
low = df['low']
volume = df['tick_volume']
spread = df['spread']

f = pd.DataFrame(index=df.index)

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

hour = df.index.hour + df.index.minute / 60
f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
f['cos_dow'] = np.cos(2 * np.pi * df.index.dayofweek / 5)

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

# Daily features (fill with dummy values for live - need 100 days of data)
daily = df[['close']].resample('D').last().ffill()
daily['sma50'] = daily['close'].rolling(50).mean()
daily['sma100'] = daily['close'].rolling(100).mean()
daily['ret_5d'] = daily['close'].pct_change(5)
f['daily_sma50'] = daily['sma50'].reindex(df.index, method='ffill').fillna(close.iloc[-1])
f['daily_sma100'] = daily['sma100'].reindex(df.index, method='ffill').fillna(close.iloc[-1])
f['daily_ret_5d'] = daily['ret_5d'].reindex(df.index, method='ffill').fillna(0.0)

atr_14 = tr.rolling(14).mean()

print(f"✓ Built {f.shape[1]} features")

# Predict
print("\nPredicting...")
X = f.iloc[-1:]
if X.isna().any().any():
    print("ERROR: Features contain NaN")
    print(X.isna().sum())
    sys.exit(1)

dmat = xgb.DMatrix(X)
pred = model.predict(dmat)[0]

# Signal
signal = "BUY" if pred > THRESHOLD else "WAIT"
current_price = close.iloc[-1]
current_atr = atr_14.iloc[-1]
stop_loss = current_price - 1.5 * current_atr
take_profit = current_price + 3.0 * current_atr

print("\n" + "=" * 60)
print("HIM PROFIT MAX SIGNAL")
print("=" * 60)
print(f"Time:        {df.index[-1]}")
print(f"Price:       ${current_price:.2f}")
print(f"ATR (14):    ${current_atr:.2f}")
print(f"Confidence:  {pred:.3f} (threshold: {THRESHOLD})")
print(f"Signal:      {signal}")
if signal == "BUY":
    print(f"\nEntry:       ${current_price:.2f}")
    print(f"Stop Loss:   ${stop_loss:.2f} (-${current_price - stop_loss:.2f})")
    print(f"Take Profit: ${take_profit:.2f} (+${take_profit - current_price:.2f})")
    print(f"\nRisk/Reward: 1:{(take_profit - current_price) / (current_price - stop_loss):.1f}")
print("=" * 60)
