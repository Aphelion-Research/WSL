#!/usr/bin/env python3
"""
Training readiness validation for hydra_xauusd_m5_master.parquet.
Walk-forward validation with baseline comparisons.
"""
import polars as pl
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_master.parquet")
REPORT = Path("reports/training_validation_report.json")

print("=" * 80)
print("TRAINING READINESS VALIDATION")
print("=" * 80)

# Load dataset
print("\n[1] Loading dataset...")
df = pl.read_parquet(DATASET)
print(f"Loaded: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

# Identify features and labels
print("\n[2] Identifying features and labels...")
label_patterns = ['target', 'label', 'y_', 'forward_ret', 'next_', 'future_', '_chg1d', '_chg5d', '_chg20d']
# CRITICAL: Also exclude forward-looking features
forward_patterns = ['fwd_', 'forward_', 'next_', 'future_', 'lead_']

numeric_cols = [c for c in df.columns if df[c].dtype in [pl.Float64, pl.Float32, pl.Int64, pl.Int32]]

# Exclude constant features
usable_features = [c for c in numeric_cols if df[c].n_unique() > 1 and c != 'time']

# Separate labels from features
label_cols = [c for c in usable_features if any(p in c.lower() for p in label_patterns)]

# Exclude both label cols AND forward-looking features
feature_cols = [
    c for c in usable_features
    if c not in label_cols
    and 'time' not in c.lower()
    and not any(p in c.lower() for p in forward_patterns)
]

print(f"Features: {len(feature_cols)}")
print(f"Labels: {len(label_cols)}")
print(f"Time column: time")

# Find forward return label
fwd_ret_cols = [c for c in label_cols if 'label_' in c.lower() and 'b' in c.lower()]
if not fwd_ret_cols:
    print("✗ No forward return label found")
    exit(1)

# Use shortest forward label (most data)
label_col = sorted(fwd_ret_cols, key=lambda x: int(''.join(filter(str.isdigit, x))))[0]
print(f"Target label: {label_col}")

# Convert to pandas for sklearn
print("\n[3] Converting to pandas (sklearn compatibility)...")
df_pd = df.select(['time'] + feature_cols + [label_col]).to_pandas()
df_pd = df_pd.sort_values('time').reset_index(drop=True)

# Drop rows with missing label
df_pd = df_pd.dropna(subset=[label_col])
print(f"After label dropna: {len(df_pd):,} rows")

# Create binary label (up/down)
df_pd['y_binary'] = (df_pd[label_col] > 0).astype(int)
pos_rate = df_pd['y_binary'].mean()
print(f"Label balance: {pos_rate:.1%} positive")

# Drop features with >50% nulls
print("\n[4] Feature filtering...")
null_rates = df_pd[feature_cols].isnull().mean()
valid_features = null_rates[null_rates < 0.5].index.tolist()
print(f"Features after null filter: {len(valid_features)}")

# Fill remaining nulls with 0
df_pd[valid_features] = df_pd[valid_features].fillna(0)

# Replace inf with large value
df_pd[valid_features] = df_pd[valid_features].replace([np.inf, -np.inf], [1e10, -1e10])

# Feature importance ranking (full dataset for now - not ideal but quick)
print("\n[5] Feature importance ranking...")
X_sample = df_pd[valid_features].iloc[::10].values  # subsample for speed
y_sample = df_pd['y_binary'].iloc[::10].values

rf_quick = RandomForestClassifier(n_estimators=20, max_depth=5, random_state=42, n_jobs=-1)
rf_quick.fit(X_sample, y_sample)
importance = rf_quick.feature_importances_

# Rank features
feature_ranking = sorted(zip(valid_features, importance), key=lambda x: x[1], reverse=True)
print(f"Top 5 features:")
for feat, imp in feature_ranking[:5]:
    print(f"  {feat}: {imp:.4f}")

# Select feature sets
top_100 = [f[0] for f in feature_ranking[:100]]
top_200 = [f[0] for f in feature_ranking[:200]]
all_features = valid_features

print(f"\nFeature sets:")
print(f"  Top 100: {len(top_100)}")
print(f"  Top 200: {len(top_200)}")
print(f"  All: {len(all_features)}")

# Walk-forward validation setup
print("\n[6] Walk-forward validation setup...")
n_rows = len(df_pd)
train_size = int(n_rows * 0.6)
val_size = int(n_rows * 0.2)
test_size = n_rows - train_size - val_size

train_df = df_pd.iloc[:train_size]
val_df = df_pd.iloc[train_size:train_size+val_size]
test_df = df_pd.iloc[train_size+val_size:]

print(f"Train: {len(train_df):,} ({len(train_df)/n_rows:.1%})")
print(f"Val:   {len(val_df):,} ({len(val_df)/n_rows:.1%})")
print(f"Test:  {len(test_df):,} ({len(test_df)/n_rows:.1%})")

# Baselines
print("\n[7] Computing baselines...")

def compute_metrics(y_true, y_pred, y_proba, returns):
    """Compute all metrics."""
    auc = roc_auc_score(y_true, y_proba) if len(np.unique(y_true)) > 1 else 0.5
    bal_acc = balanced_accuracy_score(y_true, y_pred)

    # Trading metrics (assume 1 unit long if pred=1, -1 if pred=0)
    positions = y_pred * 2 - 1  # convert {0,1} to {-1,1}
    pnl = positions * returns
    net_return = pnl.sum()
    sharpe = pnl.mean() / (pnl.std() + 1e-10) * np.sqrt(252 * 288)  # M5 = 288 bars/day

    # Max drawdown
    cumulative = np.cumsum(pnl)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = running_max - cumulative
    max_dd = drawdown.max()

    return {
        'auc': float(auc),
        'balanced_accuracy': float(bal_acc),
        'net_return': float(net_return),
        'sharpe': float(sharpe),
        'max_drawdown': float(max_dd),
        'avg_pnl_per_bar': float(pnl.mean())
    }

# Test returns
test_returns = test_df[label_col].values
test_y = test_df['y_binary'].values

baselines = {}

# Always long
y_pred_long = np.ones_like(test_y)
y_proba_long = np.ones_like(test_y)
baselines['always_long'] = compute_metrics(test_y, y_pred_long, y_proba_long, test_returns)

# Always short
y_pred_short = np.zeros_like(test_y)
y_proba_short = np.zeros_like(test_y)
baselines['always_short'] = compute_metrics(test_y, y_pred_short, y_proba_short, test_returns)

# Previous bar direction
prev_ret = test_df[label_col].shift(1).fillna(0).values
y_pred_prev = (prev_ret > 0).astype(int)
y_proba_prev = (prev_ret + 1) / 2  # normalize to [0,1]
y_proba_prev = np.clip(y_proba_prev, 0, 1)
baselines['previous_bar'] = compute_metrics(test_y, y_pred_prev, y_proba_prev, test_returns)

# Momentum (20-bar MA)
momentum = test_df[label_col].rolling(20).mean().fillna(0).values
y_pred_mom = (momentum > 0).astype(int)
y_proba_mom = (momentum - momentum.min()) / (momentum.max() - momentum.min() + 1e-10)
y_proba_mom = np.clip(y_proba_mom, 0, 1)
baselines['momentum_20'] = compute_metrics(test_y, y_pred_mom, y_proba_mom, test_returns)

# Mean reversion (z-score)
z_score = (test_df[label_col].values - test_df[label_col].rolling(50).mean().fillna(0).values) / (test_df[label_col].rolling(50).std().fillna(1).values + 1e-10)
y_pred_mr = (z_score < 0).astype(int)  # bet against extreme moves
y_proba_mr = 1 / (1 + np.exp(z_score))  # sigmoid
baselines['mean_reversion'] = compute_metrics(test_y, y_pred_mr, y_proba_mr, test_returns)

print("\nBaseline results (test set):")
for name, metrics in baselines.items():
    print(f"\n{name}:")
    print(f"  AUC: {metrics['auc']:.3f}")
    print(f"  Balanced Acc: {metrics['balanced_accuracy']:.3f}")
    print(f"  Sharpe: {metrics['sharpe']:.3f}")
    print(f"  Net Return: {metrics['net_return']:.2f}")
    print(f"  Max DD: {metrics['max_drawdown']:.2f}")

# ML models
print("\n[8] Training ML models...")

models = {}

for feature_set_name, features in [('top_100', top_100), ('top_200', top_200), ('all', all_features)]:
    print(f"\n[{feature_set_name}] Training RF...")

    X_train = train_df[features].values
    y_train = train_df['y_binary'].values
    X_test = test_df[features].values

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train RF
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train)

    # Predict
    y_pred = rf.predict(X_test_scaled)
    y_proba = rf.predict_proba(X_test_scaled)[:, 1]

    metrics = compute_metrics(test_y, y_pred, y_proba, test_returns)
    models[feature_set_name] = metrics

    print(f"  AUC: {metrics['auc']:.3f}")
    print(f"  Balanced Acc: {metrics['balanced_accuracy']:.3f}")
    print(f"  Sharpe: {metrics['sharpe']:.3f}")
    print(f"  Net Return: {metrics['net_return']:.2f}")
    print(f"  Max DD: {metrics['max_drawdown']:.2f}")

# Final verdict
print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

# Check if any model beats best baseline
best_baseline_sharpe = max(m['sharpe'] for m in baselines.values())
best_model_sharpe = max(m['sharpe'] for m in models.values())

best_baseline_auc = max(m['auc'] for m in baselines.values())
best_model_auc = max(m['auc'] for m in models.values())

print(f"\nBest baseline Sharpe: {best_baseline_sharpe:.3f}")
print(f"Best model Sharpe: {best_model_sharpe:.3f}")
print(f"Best baseline AUC: {best_baseline_auc:.3f}")
print(f"Best model AUC: {best_model_auc:.3f}")

# Verdict logic
beats_baseline_sharpe = best_model_sharpe > best_baseline_sharpe * 1.1  # 10% improvement
beats_baseline_auc = best_model_auc > best_baseline_auc
sharpe_positive = best_model_sharpe > 0.5

if beats_baseline_sharpe and beats_baseline_auc and sharpe_positive:
    verdict = "DATASET_READY_FOR_RESEARCH"
    print(f"\n✓ VERDICT: {verdict}")
    print("  ML models significantly beat baselines.")
    print("  Dataset is suitable for research and strategy development.")
elif beats_baseline_auc:
    verdict = "DATASET_READY_FOR_RESEARCH"
    print(f"\n○ VERDICT: {verdict}")
    print("  ML models show predictive power (AUC > baseline).")
    print("  Sharpe may need improvement via better features or regime filtering.")
else:
    verdict = "DATASET_NEEDS_REPAIR"
    print(f"\n✗ VERDICT: {verdict}")
    print("  ML models fail to beat baselines.")
    print("  Dataset may have issues: leakage, noise, or insufficient signal.")

# Save report
report = {
    'timestamp': datetime.now().isoformat(),
    'dataset': str(DATASET),
    'n_rows': int(n_rows),
    'n_features': len(all_features),
    'label_column': label_col,
    'label_balance': float(pos_rate),
    'train_test_split': {
        'train': int(train_size),
        'val': int(val_size),
        'test': int(test_size)
    },
    'baselines': baselines,
    'models': models,
    'verdict': verdict
}

REPORT.write_text(json.dumps(report, indent=2))
print(f"\nReport saved: {REPORT}")
print("=" * 80)
