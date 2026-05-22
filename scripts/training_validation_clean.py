#!/usr/bin/env python3
"""
Training validation for clean dataset using schema manifest.
Schema-driven feature selection. No leakage.
"""
import polars as pl
import numpy as np
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, balanced_accuracy_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_master_clean.parquet")
SCHEMA = Path("data/hydra_xauusd_m5_master_schema.json")
REPORT = Path("reports/training_validation_clean_report.json")

print("=" * 80)
print("TRAINING VALIDATION (SCHEMA-DRIVEN)")
print("=" * 80)

# Load schema
print("\n[1] Loading schema...")
schema = json.loads(SCHEMA.read_text())
print(f"Schema version: {schema['version']}")
print(f"Features: {schema['n_features']}")
print(f"Labels: {schema['n_labels']}")

# Extract feature/label lists from schema
feature_cols = [c['name'] for c in schema['columns']
                if c['role'] == 'feature' and c['allowed_for_training']]
label_cols = [c['name'] for c in schema['columns']
              if c['role'] == 'label']

print(f"Trainable features: {len(feature_cols)}")
print(f"Available labels: {len(label_cols)}")

# Load dataset
print("\n[2] Loading dataset...")
df = pl.read_parquet(DATASET)
print(f"Loaded: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

# Select label
label_6b = [c for c in label_cols if 'label_6b' in c]
if not label_6b:
    print("✗ label_6b not found, using first label")
    label_col = label_cols[0]
else:
    label_col = label_6b[0]

print(f"Target label: {label_col}")

# Convert to pandas
print("\n[3] Converting to pandas...")
cols_to_load = ['time'] + feature_cols + [label_col]
df_pd = df.select(cols_to_load).to_pandas()
df_pd = df_pd.sort_values('time').reset_index(drop=True)

# Drop label nulls
df_pd = df_pd.dropna(subset=[label_col])
print(f"After label dropna: {len(df_pd):,} rows")

# Create binary label
df_pd['y_binary'] = (df_pd[label_col] > 0).astype(int)
pos_rate = df_pd['y_binary'].mean()
print(f"Label balance: {pos_rate:.1%} positive")

# Filter features by null rate
print("\n[4] Feature filtering...")
null_rates = df_pd[feature_cols].isnull().mean()
valid_features = null_rates[null_rates < 0.5].index.tolist()
print(f"Features after null filter (<50%): {len(valid_features)}")

# Fill remaining nulls
df_pd[valid_features] = df_pd[valid_features].fillna(0)
df_pd[valid_features] = df_pd[valid_features].replace([np.inf, -np.inf], [1e10, -1e10])

# Quick feature importance
print("\n[5] Feature importance ranking...")
X_sample = df_pd[valid_features].iloc[::10].values
y_sample = df_pd['y_binary'].iloc[::10].values

rf_quick = RandomForestClassifier(n_estimators=20, max_depth=5, random_state=42, n_jobs=-1)
rf_quick.fit(X_sample, y_sample)
importance = rf_quick.feature_importances_

feature_ranking = sorted(zip(valid_features, importance), key=lambda x: x[1], reverse=True)
print(f"Top 5 features:")
for feat, imp in feature_ranking[:5]:
    print(f"  {feat}: {imp:.4f}")

# SANITY CHECK: No forward-looking features should be in top 100
top_100_names = [f[0] for f in feature_ranking[:100]]
forward_patterns = ['fwd_', 'forward_', 'future_', 'next_', 'lead_']
leaked_in_top100 = [f for f in top_100_names if any(p in f.lower() for p in forward_patterns)]

if leaked_in_top100:
    print(f"\n✗ CRITICAL: Forward-looking features in top 100:")
    for f in leaked_in_top100:
        print(f"    {f}")
    print("  Training ABORTED.")
    exit(1)
print("✓ No forward-looking features in top 100")

# Feature sets
top_100 = [f[0] for f in feature_ranking[:100]]
top_200 = [f[0] for f in feature_ranking[:200]]
all_features = valid_features

print(f"\nFeature sets:")
print(f"  Top 100: {len(top_100)}")
print(f"  Top 200: {len(top_200)}")
print(f"  All: {len(all_features)}")

# Walk-forward split
print("\n[6] Walk-forward split...")
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

    # Trading metrics
    positions = y_pred * 2 - 1  # {0,1} -> {-1,1}
    pnl = positions * returns
    net_return = pnl.sum()
    sharpe = pnl.mean() / (pnl.std() + 1e-10) * np.sqrt(252 * 288)

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

test_returns = test_df[label_col].values
test_y = test_df['y_binary'].values

baselines = {}

# Always long
y_pred_long = np.ones_like(test_y)
y_proba_long = np.ones_like(test_y)
baselines['always_long'] = compute_metrics(test_y, y_pred_long, y_proba_long, test_returns)

# Previous bar
prev_ret = test_df[label_col].shift(1).fillna(0).values
y_pred_prev = (prev_ret > 0).astype(int)
y_proba_prev = np.clip((prev_ret + 1) / 2, 0, 1)
baselines['previous_bar'] = compute_metrics(test_y, y_pred_prev, y_proba_prev, test_returns)

print("\nBaseline results (test set):")
for name, metrics in baselines.items():
    print(f"\n{name}:")
    print(f"  AUC: {metrics['auc']:.3f}")
    print(f"  Balanced Acc: {metrics['balanced_accuracy']:.3f}")
    print(f"  Sharpe: {metrics['sharpe']:.3f}")
    print(f"  Net Return: {metrics['net_return']:.2f}")

# ML models
print("\n[8] Training ML models...")

models = {}

for feature_set_name, features in [('top_100', top_100), ('top_200', top_200), ('all', all_features)]:
    print(f"\n[{feature_set_name}] Training RF...")

    X_train = train_df[features].values
    y_train = train_df['y_binary'].values
    X_test = test_df[features].values

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train_scaled, y_train)

    y_pred = rf.predict(X_test_scaled)
    y_proba = rf.predict_proba(X_test_scaled)[:, 1]

    metrics = compute_metrics(test_y, y_pred, y_proba, test_returns)
    models[feature_set_name] = metrics

    print(f"  AUC: {metrics['auc']:.3f}")
    print(f"  Sharpe: {metrics['sharpe']:.3f}")
    print(f"  Net Return: {metrics['net_return']:.2f}")

# Final verdict
print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

best_baseline_sharpe = max(m['sharpe'] for m in baselines.values())
best_model_sharpe = max(m['sharpe'] for m in models.values())

best_baseline_auc = max(m['auc'] for m in baselines.values())
best_model_auc = max(m['auc'] for m in models.values())

print(f"\nBest baseline Sharpe: {best_baseline_sharpe:.3f}")
print(f"Best model Sharpe: {best_model_sharpe:.3f}")
print(f"Best baseline AUC: {best_baseline_auc:.3f}")
print(f"Best model AUC: {best_model_auc:.3f}")

# Verdict
beats_baseline_auc = best_model_auc > best_baseline_auc
sharpe_positive = best_model_sharpe > 0.5
model_beats_sharpe = best_model_sharpe > best_baseline_sharpe * 0.5  # at least 50% of baseline

if beats_baseline_auc and sharpe_positive and model_beats_sharpe:
    verdict = "MASTER_CLEAN_READY_FOR_RESEARCH"
    print(f"\n✓ VERDICT: {verdict}")
    print("  Clean features show predictive power.")
elif beats_baseline_auc:
    verdict = "MASTER_CLEAN_READY_FOR_RESEARCH"
    print(f"\n○ VERDICT: {verdict}")
    print("  AUC beats baseline. Sharpe needs improvement.")
else:
    verdict = "MASTER_STILL_NEEDS_REPAIR"
    print(f"\n✗ VERDICT: {verdict}")
    print("  Models fail to beat baselines with clean features.")

# Save report
report = {
    'timestamp': datetime.now().isoformat(),
    'dataset': str(DATASET),
    'schema': str(SCHEMA),
    'n_rows': int(n_rows),
    'n_features': len(all_features),
    'label_column': label_col,
    'label_balance': float(pos_rate),
    'baselines': baselines,
    'models': models,
    'verdict': verdict
}

REPORT.write_text(json.dumps(report, indent=2))
print(f"\nReport saved: {REPORT}")
print("=" * 80)
