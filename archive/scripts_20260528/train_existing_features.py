#!/usr/bin/env python3
"""Train on existing feature dataset (no raw prices)."""

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

# Target: forward return
target_col = 'fwd_ret_5b'
if target_col not in df.columns:
    print(f"ERROR: {target_col} not found. Available: {df.columns.tolist()[:10]}")
    exit(1)

# Drop label columns (leakage)
label_cols = [c for c in df.columns if c.startswith('label_') or c.startswith('fwd_ret_')]
feature_cols = [c for c in df.columns if c not in label_cols + ['time']]

print(f"Using {len(feature_cols)} features, target: {target_col}")

# Drop NaNs
df = df.dropna(subset=[target_col])
print(f"Clean dataset: {len(df)} bars")

# Train/test split (80/20)
split_idx = int(len(df) * 0.8)
train = df.iloc[:split_idx].copy()
test = df.iloc[split_idx:].copy()

print(f"Train: {len(train)} bars, Test: {len(test)} bars")

X_train = train[feature_cols].fillna(0)
y_train = train[target_col]
X_test = test[feature_cols].fillna(0)
y_test = test[target_col]

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

# In-sample
y_train_pred = model.predict(X_train)
train_mse = mean_squared_error(y_train, y_train_pred)
train_r2 = r2_score(y_train, y_train_pred)

print("\n=== IN-SAMPLE (TRAIN) ===")
print(f"MSE: {train_mse:.6f}")
print(f"R²: {train_r2:.4f}")
print(f"Directional accuracy: {(np.sign(y_train_pred) == np.sign(y_train)).mean():.4f}")

# Out-of-sample
y_test_pred = model.predict(X_test)
test_mse = mean_squared_error(y_test, y_test_pred)
test_r2 = r2_score(y_test, y_test_pred)

print("\n=== OUT-OF-SAMPLE (TEST) ===")
print(f"MSE: {test_mse:.6f}")
print(f"R²: {test_r2:.4f}")
print(f"Directional accuracy: {(np.sign(y_test_pred) == np.sign(y_test)).mean():.4f}")

# IC
ic_train = train[target_col].corr(pd.Series(y_train_pred, index=train.index))
ic_test = test[target_col].corr(pd.Series(y_test_pred, index=test.index))

print(f"\nIC (train): {ic_train:.4f}")
print(f"IC (test): {ic_test:.4f}")

# Backtest
test['pred'] = y_test_pred
test['strategy_return'] = np.sign(test['pred']) * test[target_col]
test['cumulative'] = (1 + test['strategy_return']).cumprod()

sharpe = test['strategy_return'].mean() / (test['strategy_return'].std() + 1e-12) * np.sqrt(252 * 288)
max_dd = ((test['cumulative'].cummax() - test['cumulative']) / test['cumulative'].cummax()).max()

print(f"\n=== BACKTEST (OOS) ===")
print(f"Sharpe ratio: {sharpe:.4f}")
print(f"Total return: {(test['cumulative'].iloc[-1] - 1) * 100:.2f}%")
print(f"Max drawdown: {max_dd * 100:.2f}%")

# Feature importance
importances = pd.Series(model.feature_importances_, index=feature_cols).sort_values(ascending=False)
print("\n=== TOP 15 FEATURES ===")
for i, (feat, imp) in enumerate(importances.head(15).items(), 1):
    print(f"{i:2}. {feat:40} {imp:.4f}")

print("\n✅ Training complete!")
