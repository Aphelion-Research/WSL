"""Retrain Him V2 with ZERO cost labels.

Assume broker covers all costs. Train model to find edge before costs.
"""
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("RETRAIN HIM V2 WITH ZERO COST LABELS")
print("=" * 60)

# Load M5
print("\nLoading M5 data...")
m5 = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
m5['time'] = pd.to_datetime(m5['time'])
m5 = m5.set_index('time')

# Split
train = m5[(m5.index >= "2015-01-01") & (m5.index <= "2022-12-31")]
val = m5[(m5.index >= "2023-01-01") & (m5.index <= "2023-12-31")]

print(f"Train: {len(train):,} bars")
print(f"Val: {len(val):,} bars")

# Build features (Him V2 pattern)
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

    # VWAP
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

    # Time
    hour = df.index.hour + df.index.minute / 60
    f['cos_hour'] = np.cos(2 * np.pi * hour / 24)
    f['sin_hour'] = np.sin(2 * np.pi * hour / 24)
    f['cos_dow'] = np.cos(2 * np.pi * df.index.dayofweek / 5)

    # Pullbacks
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

    # Consensus
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
train_features = build_features(train)
val_features = build_features(val)
print(f"Features: {train_features.shape[1]} columns")

# Create ZERO COST labels
print("\nCreating zero-cost labels...")

def create_labels(df, horizon=16):
    """Simple forward return at horizon bars."""
    close = df['close']
    fwd_ret = close.shift(-horizon) / close - 1
    labels = (fwd_ret > 0).astype(int)  # 1 if up, 0 if down
    return labels

train_labels = create_labels(train)
val_labels = create_labels(val)

print(f"Train labels: {(train_labels==1).sum()} up, {(train_labels==0).sum()} down")

# Drop NaN
train_mask = train_features.notna().all(axis=1) & train_labels.notna()
val_mask = val_features.notna().all(axis=1) & val_labels.notna()

X_train = train_features[train_mask]
y_train = train_labels[train_mask]
X_val = val_features[val_mask]
y_val = val_labels[val_mask]

print(f"\nTrain: {len(X_train):,} samples")
print(f"Val: {len(X_val):,} samples")

# Train
print("\nTraining XGBoost (zero-cost labels)...")
dtrain = xgb.DMatrix(X_train, label=y_train)
dval = xgb.DMatrix(X_val, label=y_val)

params = {
    'objective': 'binary:logistic',
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'tree_method': 'hist',
}

model = xgb.train(
    params,
    dtrain,
    num_boost_round=200,
    evals=[(dtrain, 'train'), (dval, 'val')],
    early_stopping_rounds=20,
    verbose_eval=20,
)

print(f"\nBest iteration: {model.best_iteration}")

# Save
output_dir = Path("output_him_v2")
output_dir.mkdir(exist_ok=True, parents=True)
model_path = output_dir / "him_v2_zero_cost.json"
model.save_model(str(model_path))
print(f"\n✓ Model saved to {model_path}")

print("\n" + "=" * 60)
print("Next: Test with scripts/him_v2_zero_cost_test.py (update model path)")
print("=" * 60)
