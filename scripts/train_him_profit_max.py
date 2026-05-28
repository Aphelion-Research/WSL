"""Him Profit Max: Zero-cost labels + tuned for prop firm costs.

Strategy:
1. Train on ALL moves (not aggressive filter)
2. Binary classification: up/down at 16-bar horizon
3. Tune hyperparameters for selectivity (high threshold = fewer trades)
4. Prop firm costs: $1/trade → need >$1 edge per trade
"""
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("HIM PROFIT MAX: TUNED FOR PROP FIRM")
print("=" * 60)

# Load M5
m5 = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
m5['time'] = pd.to_datetime(m5['time'])
m5 = m5.set_index('time')

# Split
train = m5[(m5.index >= "2015-01-01") & (m5.index <= "2022-12-31")]
val = m5[(m5.index >= "2023-01-01") & (m5.index <= "2023-12-31")]

print(f"Train: {len(train):,} bars")
print(f"Val: {len(val):,} bars")

# Build features (Him V2 feature set)
def build_features(df):
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    spread = df['spread']

    f = pd.DataFrame(index=df.index)

    # Returns
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
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    for bars, suffix in [(36, '3h'), (144, '12h'), (288, '24h')]:
        atr = tr.rolling(bars).mean()
        f[f'atr_{suffix}_pct'] = atr / close

    # Volume
    f['vol_ratio_short'] = volume / volume.rolling(48).mean().replace(0, np.nan)
    f['vol_ratio_long'] = volume / volume.rolling(288).mean().replace(0, np.nan)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, np.nan)
    f['rsi_14'] = 100 - 100 / (1 + gain / loss)

    # Bollinger
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std().replace(0, np.nan)
    f['bb_pos'] = (close - bb_mid) / (2 * bb_std)

    # Volume z-score
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Session
    hour = df.index.hour + df.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * df.index.dayofweek / 5)

    # Pullback
    for bars, suffix in [(48, '4h'), (144, '12h'), (288, '24h')]:
        rh = high.rolling(bars).max()
        rl = low.rolling(bars).min()
        f[f'pullback_high_{suffix}'] = (rh - close) / close
        f[f'pullback_low_{suffix}'] = (close - rl) / close

    # Spread z-score
    f['spread_zscore'] = (spread - spread.rolling(288).mean()) / spread.rolling(288).std().replace(0, np.nan)

    # Consecutive
    f['consec_up'] = (close > close.shift(1)).astype(int)
    f['consec_down'] = (close < close.shift(1)).astype(int)
    for col in ['consec_up', 'consec_down']:
        f[col] = f[col].groupby((f[col] != f[col].shift()).cumsum()).cumsum()

    # Multi-scale consensus
    ret_cols = [c for c in f.columns if c.startswith('ret_') and 'bar' in c]
    f['multi_scale_consensus'] = f[ret_cols].apply(lambda x: (x > 0).sum(), axis=1)

    # Daily
    daily = df[['close']].resample('D').last().ffill()
    daily['sma50'] = daily['close'].rolling(50).mean()
    daily['sma100'] = daily['close'].rolling(100).mean()
    daily['ret_5d'] = daily['close'].pct_change(5)
    f['daily_sma50'] = daily['sma50'].reindex(df.index, method='ffill')
    f['daily_sma100'] = daily['sma100'].reindex(df.index, method='ffill')
    f['daily_ret_5d'] = daily['ret_5d'].reindex(df.index, method='ffill')

    return f

print("\nBuilding features...")
train_f = build_features(train)
val_f = build_features(val)
print(f"Features: {train_f.shape[1]}")

# Labels: simple forward returns (zero-cost)
def create_labels(df, horizon=16):
    close = df['close']
    fwd_ret = close.shift(-horizon) / close - 1
    return (fwd_ret > 0).astype(int)

train_y = create_labels(train)
val_y = create_labels(val)

# Drop NaN
train_mask = train_f.notna().all(axis=1) & train_y.notna()
val_mask = val_f.notna().all(axis=1) & val_y.notna()

X_train = train_f[train_mask]
y_train = train_y[train_mask]
X_val = val_f[val_mask]
y_val = val_y[val_mask]

print(f"\nTrain: {len(X_train):,}")
print(f"Val: {len(X_val):,}")
print(f"Positive labels: {y_train.sum()} ({y_train.sum()/len(y_train)*100:.1f}%)")

# Train with higher regularization + lower LR for selectivity
print("\nTraining...")

params = {
    'objective': 'binary:logistic',
    'max_depth': 5,  # Shallower
    'learning_rate': 0.02,  # Slower
    'subsample': 0.7,
    'colsample_bytree': 0.7,
    'min_child_weight': 5,  # More conservative
    'reg_alpha': 0.5,  # Higher L1
    'reg_lambda': 2.0,  # Higher L2
    'tree_method': 'hist',
    'scale_pos_weight': 1.0,
}

dtrain = xgb.DMatrix(X_train, label=y_train)
dval = xgb.DMatrix(X_val, label=y_val)

model = xgb.train(
    params,
    dtrain,
    num_boost_round=300,
    evals=[(dtrain, 'train'), (dval, 'val')],
    early_stopping_rounds=30,
    verbose_eval=20,
)

# Save
output_dir = Path("output_him_v2")
model.save_model(str(output_dir / "him_profit_max.json"))

print(f"\n✓ Saved to {output_dir}/him_profit_max.json")

# Metadata
metadata = {
    'model_name': 'him_profit_max',
    'version': '1.0.0',
    'feature_count': X_train.shape[1],
    'train_period': '2015-2022',
    'val_period': '2023',
    'label_type': 'zero_cost_binary',
    'label_horizon': 16,
    'strategy': 'Him V2 features + high regularization for selectivity',
    'target_costs': 'prop_firm_$1_per_trade',
}

with open(output_dir / "him_profit_max_metadata.json", 'w') as f:
    json.dump(metadata, f, indent=2)

print("\n" + "=" * 60)
print("Next: scripts/test_him_profit_max.py")
print("=" * 60)
