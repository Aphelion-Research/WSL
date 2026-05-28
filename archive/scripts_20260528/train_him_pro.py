"""HIM PRO: Aggressive profit-focused model.

Ensemble + regime filter + dynamic sizing.
Target: Maximum profit at prop firm costs.
"""
import sys
import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("HIM PRO: MAXIMUM PROFIT MODEL")
print("=" * 60)

# Load M5
m5 = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
m5['time'] = pd.to_datetime(m5['time'])
m5 = m5.set_index('time')

# Split
train = m5[(m5.index >= "2018-01-01") & (m5.index <= "2022-12-31")]  # More recent data
val = m5[(m5.index >= "2023-01-01") & (m5.index <= "2023-12-31")]

print(f"Train: {len(train):,} bars")
print(f"Val: {len(val):,} bars")

# Build features
def build_features(df):
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['tick_volume']
    spread = df['spread']

    f = pd.DataFrame(index=df.index)

    # Returns (more horizons)
    for bars in [1, 2, 4, 8, 16, 32, 64, 96]:
        f[f'ret_{bars}b'] = close.pct_change(bars)

    # Volatility
    for bars in [8, 16, 32, 64]:
        f[f'vol_{bars}b'] = close.rolling(bars).std() / close

    # Range features
    for bars in [16, 48, 96, 288]:
        rh = high.rolling(bars).max()
        rl = low.rolling(bars).min()
        rng = (rh - rl).replace(0, np.nan)
        f[f'range_pos_{bars}b'] = (close - rl) / rng

    # ATR
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    for bars in [14, 28, 56]:
        f[f'atr_{bars}b'] = tr.rolling(bars).mean() / close

    # RSI multiple
    for period in [7, 14, 28]:
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean().replace(0, np.nan)
        f[f'rsi_{period}'] = 100 - 100 / (1 + gain / loss)

    # Volume
    f['vol_ratio_8'] = volume / volume.rolling(8).mean().replace(0, np.nan)
    f['vol_ratio_48'] = volume / volume.rolling(48).mean().replace(0, np.nan)
    f['vol_zscore'] = (volume - volume.rolling(96).mean()) / volume.rolling(96).std().replace(0, np.nan)

    # Price vs MA
    for bars in [10, 20, 50, 100]:
        ma = close.rolling(bars).mean()
        f[f'close_ma{bars}'] = (close - ma) / close

    # Session features
    hour = df.index.hour
    f['london'] = ((hour >= 8) & (hour < 16)).astype(int)
    f['ny'] = ((hour >= 13) & (hour < 21)).astype(int)
    f['asia'] = ((hour >= 0) & (hour < 8)).astype(int)
    f['overlap'] = ((hour >= 13) & (hour < 16)).astype(int)

    # High volatility flag
    vol_pct = close.rolling(96).std().rank(pct=True)
    f['high_vol'] = (vol_pct > 0.7).astype(int)

    # Momentum
    f['mom_8'] = (close > close.shift(8)).astype(int)
    f['mom_16'] = (close > close.shift(16)).astype(int)

    return f

print("\nBuilding features...")
train_f = build_features(train)
val_f = build_features(val)
print(f"Features: {train_f.shape[1]}")

# Labels: aggressive (shorter horizon, larger targets)
def create_labels(df, horizon=12):  # 12 bars = 1 hour
    close = df['close']
    fwd_ret = close.shift(-horizon) / close - 1

    # Aggressive: only take strong moves
    labels = pd.Series(0, index=df.index)  # Default: skip
    labels[fwd_ret > 0.0015] = 1  # Long if > 0.15% move
    labels[fwd_ret < -0.0015] = -1  # Short if < -0.15% move (not used yet)

    return labels

train_y = create_labels(train)
val_y = create_labels(val)

# Filter: only keep long/skip
train_y = train_y[train_y >= 0]
val_y = val_y[val_y >= 0]

# Drop NaN
train_mask = train_f.notna().all(axis=1) & train_y.notna()
val_mask = val_f.notna().all(axis=1) & val_y.notna()

X_train = train_f[train_mask]
y_train = train_y[train_mask]
X_val = val_f[val_mask]
y_val = val_y[val_mask]

print(f"\nTrain: {len(X_train):,}")
print(f"Val: {len(X_val):,}")
print(f"Long labels: {(y_train==1).sum()} ({(y_train==1).sum()/len(y_train)*100:.1f}%)")

# Train 3 models with different hyperparameters
print("\nTraining ensemble...")

models = []

# Model 1: Deep trees
print("\n[1/3] Deep trees...")
params1 = {
    'objective': 'binary:logistic',
    'max_depth': 8,
    'learning_rate': 0.03,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'tree_method': 'hist',
}

dtrain = xgb.DMatrix(X_train, label=y_train)
dval = xgb.DMatrix(X_val, label=y_val)

model1 = xgb.train(
    params1,
    dtrain,
    num_boost_round=300,
    evals=[(dval, 'val')],
    early_stopping_rounds=30,
    verbose_eval=False,
)
models.append(model1)

# Model 2: Shallow + many trees
print("[2/3] Shallow + boosting...")
params2 = {
    'objective': 'binary:logistic',
    'max_depth': 4,
    'learning_rate': 0.01,
    'subsample': 0.9,
    'colsample_bytree': 0.9,
    'tree_method': 'hist',
}

model2 = xgb.train(
    params2,
    dtrain,
    num_boost_round=500,
    evals=[(dval, 'val')],
    early_stopping_rounds=30,
    verbose_eval=False,
)
models.append(model2)

# Model 3: Balanced
print("[3/3] Balanced...")
params3 = {
    'objective': 'binary:logistic',
    'max_depth': 6,
    'learning_rate': 0.05,
    'subsample': 0.85,
    'colsample_bytree': 0.85,
    'reg_alpha': 0.1,
    'reg_lambda': 1.0,
    'tree_method': 'hist',
}

model3 = xgb.train(
    params3,
    dtrain,
    num_boost_round=400,
    evals=[(dval, 'val')],
    early_stopping_rounds=30,
    verbose_eval=False,
)
models.append(model3)

# Save ensemble
output_dir = Path("output_him_pro")
output_dir.mkdir(exist_ok=True, parents=True)

for i, model in enumerate(models):
    model.save_model(str(output_dir / f"him_pro_model_{i+1}.json"))

print(f"\n✓ Saved 3 models to {output_dir}/")

# Save metadata
metadata = {
    'model_name': 'him_pro',
    'version': '1.0.0',
    'ensemble_size': 3,
    'feature_count': X_train.shape[1],
    'train_period': '2018-2022',
    'val_period': '2023',
    'label_threshold': 0.0015,
    'label_horizon': 12,
    'strategy': 'ensemble + regime filter + dynamic sizing',
    'target': 'maximum profit at prop firm costs',
}

with open(output_dir / "metadata.json", 'w') as f:
    json.dump(metadata, f, indent=2)

print("\n" + "=" * 60)
print("Training complete")
print("Next: scripts/test_him_pro.py")
print("=" * 60)
