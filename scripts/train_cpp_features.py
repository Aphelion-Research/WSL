#!/usr/bin/env python3
"""
Train model with C++-inspired advanced features.
Since C++ build incomplete, implement key features in Python for speed.
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')

print("Loading dataset...")
df = pd.read_parquet('data/hydra_xauusd_m5_master_clean.parquet')
print(f"Loaded {len(df)} bars")

# Add C++-inspired features (fast Python versions)
print("Computing advanced features...")

# 1. Permutation entropy (simplified)
def permutation_entropy(series, m=3, delay=1):
    n = len(series)
    patterns = {}
    for i in range(n - m * delay):
        pattern = tuple(np.argsort([series[i + j * delay] for j in range(m)]))
        patterns[pattern] = patterns.get(pattern, 0) + 1

    probs = np.array(list(patterns.values())) / sum(patterns.values())
    return -np.sum(probs * np.log2(probs + 1e-12))

df['perm_entropy'] = df['close'].rolling(100).apply(lambda x: permutation_entropy(x.values), raw=False)

# 2. Hurst exponent (R/S analysis)
def hurst_rs(series):
    n = len(series)
    if n < 20:
        return np.nan

    mean = series.mean()
    cumdev = (series - mean).cumsum()
    R = cumdev.max() - cumdev.min()
    S = series.std()

    if S < 1e-10:
        return np.nan

    return np.log(R / S) / np.log(n)

df['hurst'] = df['close'].rolling(252).apply(hurst_rs, raw=False)

# 3. Multifractal width (simplified)
df['returns_sq'] = df['close'].pct_change() ** 2
df['mf_width'] = df['returns_sq'].rolling(252).apply(lambda x: x.quantile(0.95) / (x.quantile(0.05) + 1e-12), raw=False)

# 4. Sample entropy (simplified - use std as proxy)
df['sample_entropy'] = df['close'].rolling(100).apply(lambda x: x.std() / (x.mean() + 1e-12), raw=False)

# 5. Transfer entropy (simplified - lagged correlation)
df['price_lag1'] = df['close'].shift(1)
df['transfer_ent'] = df['close'].rolling(60).corr(df['price_lag1'].shift(1)).abs()

# 6. Jump detection (Lee-Mykland simplified)
df['ret_sq'] = df['close'].pct_change() ** 2
df['bv'] = ((df['close'].pct_change().abs() * df['close'].shift(1).pct_change().abs()).rolling(60).sum())
df['jump_test'] = (df['ret_sq'] / (df['bv'].shift(1) + 1e-12)).rolling(20).mean()

# 7. Microstructure noise (bid-ask bounce proxy)
df['spread_vol'] = df['spread'].rolling(60).std()
df['noise_var'] = -df['close'].pct_change().rolling(60).autocorr(1)

# 8. Realized variance components
df['rv_5m'] = df['close'].pct_change().rolling(12).apply(lambda x: (x ** 2).sum(), raw=False)  # 1h window
df['rv_1h'] = df['close'].pct_change().rolling(60).apply(lambda x: (x ** 2).sum(), raw=False)  # 5h window

# 9. Network centrality proxy (correlation with lagged self)
df['centrality'] = df['close'].rolling(252).corr(df['close'].shift(12)).abs()

# 10. Complexity measures
df['lz_complexity'] = df['close'].rolling(100).apply(lambda x: len(set(np.diff(x > x.median()))), raw=False)

print("Features computed. Preparing labels...")

# Forward return (target)
df['target'] = df['close'].pct_change(5).shift(-5)  # 5-bar forward return

# Drop NaNs
df = df.dropna()
print(f"Clean dataset: {len(df)} bars")

# Train/test split (time series)
split_idx = int(len(df) * 0.8)
train = df.iloc[:split_idx].copy()
test = df.iloc[split_idx:].copy()

print(f"Train: {len(train)} bars, Test: {len(test)} bars")

# Feature columns (exclude target + metadata)
feature_cols = [c for c in df.columns if c not in ['target', 'time', 'close', 'open', 'high', 'low', 'price_lag1', 'ret_sq', 'returns_sq']]
print(f"Using {len(feature_cols)} features")

X_train = train[feature_cols]
y_train = train['target']
X_test = test[feature_cols]
y_test = test['target']

# Train RandomForest
print("\nTraining RandomForest...")
model = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    min_samples_split=50,
    min_samples_leaf=20,
    n_jobs=20,
    random_state=42
)
model.fit(X_train, y_train)

# In-sample predictions
y_train_pred = model.predict(X_train)
train_mse = mean_squared_error(y_train, y_train_pred)
train_r2 = r2_score(y_train, y_train_pred)

print("\n=== IN-SAMPLE (TRAIN) ===")
print(f"MSE: {train_mse:.6f}")
print(f"R²: {train_r2:.4f}")
print(f"Sharpe (directional): {(np.sign(y_train_pred) == np.sign(y_train)).mean():.4f}")

# Out-of-sample predictions
y_test_pred = model.predict(X_test)
test_mse = mean_squared_error(y_test, y_test_pred)
test_r2 = r2_score(y_test, y_test_pred)

print("\n=== OUT-OF-SAMPLE (TEST) ===")
print(f"MSE: {test_mse:.6f}")
print(f"R²: {test_r2:.4f}")
print(f"Sharpe (directional): {(np.sign(y_test_pred) == np.sign(y_test)).mean():.4f}")

# IC (Information Coefficient)
ic_train = train['target'].corr(pd.Series(y_train_pred, index=train.index))
ic_test = test['target'].corr(pd.Series(y_test_pred, index=test.index))

print(f"\nIC (train): {ic_train:.4f}")
print(f"IC (test): {ic_test:.4f}")

# Feature importance
importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
print("\n=== TOP 10 FEATURES ===")
print(importances.head(10))

# Backtest returns
test['pred'] = y_test_pred
test['strategy_return'] = np.sign(test['pred']) * test['target']
test['cumulative'] = (1 + test['strategy_return']).cumprod()

sharpe = test['strategy_return'].mean() / (test['strategy_return'].std() + 1e-12) * np.sqrt(252 * 288)  # 5min bars
print(f"\n=== BACKTEST (OOS) ===")
print(f"Sharpe ratio: {sharpe:.4f}")
print(f"Total return: {(test['cumulative'].iloc[-1] - 1) * 100:.2f}%")
print(f"Max drawdown: {((test['cumulative'].cummax() - test['cumulative']) / test['cumulative'].cummax()).max() * 100:.2f}%")

print("\n✅ Training complete!")
