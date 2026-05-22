#!/usr/bin/env python3
"""
Baseline and label sanity audit.
Verify labels, baselines, and metrics before feature engineering.
"""
import polars as pl
import numpy as np
import pandas as pd
from pathlib import Path
import json
from datetime import datetime

DATASET = Path("data/hydra_xauusd_m5_master_clean.parquet")
SCHEMA = Path("data/hydra_xauusd_m5_master_schema.json")
OUTPUT_MD = Path("reports/label_baseline_sanity_report.md")
OUTPUT_JSON = Path("reports/label_baseline_sanity.json")

print("=" * 80)
print("LABEL & BASELINE SANITY AUDIT")
print("=" * 80)

# Load
df = pl.read_parquet(DATASET)
schema = json.loads(SCHEMA.read_text())

print(f"\nDataset: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

# Get label columns
label_cols = [c['name'] for c in schema['columns'] if c['role'] == 'label']
print(f"Label columns: {len(label_cols)}")

# Convert to pandas for easier analysis
df_pd = df.to_pandas()
df_pd = df_pd.sort_values('time').reset_index(drop=True)

# ============================================================================
# 1. LABEL ALIGNMENT AUDIT
# ============================================================================
print("\n" + "=" * 80)
print("1. LABEL ALIGNMENT AUDIT")
print("=" * 80)

# Find OHLC columns or reconstruct from returns
close_col = None
if 'close' in df_pd.columns:
    close_col = 'close'
else:
    # Close not in clean dataset, reconstruct from returns
    print("\n⚠ Close column not in clean dataset")
    print("  Loading raw source to get OHLC...")

    # Load raw Dukascopy
    raw_df = pl.read_parquet('data/mt5_history/XAUUSD_M5_dukascopy.parquet')
    raw_pd = raw_df.select(['time', 'close']).to_pandas()

    # Merge with clean dataset
    df_pd = df_pd.merge(raw_pd, on='time', how='left')
    close_col = 'close'

    if df_pd[close_col].isna().sum() > 0:
        print(f"  ✗ Failed to merge close prices ({df_pd[close_col].isna().sum()} NaNs)")
        exit(1)

    print(f"  ✓ Merged close prices from raw source")

print(f"\nClose column: {close_col}")

# Find label_6b for inspection
label_6b = [c for c in label_cols if 'label_6b' in c]
if not label_6b:
    print("✗ label_6b not found")
    label_inspect = label_cols[0]
else:
    label_inspect = label_6b[0]

print(f"Inspecting: {label_inspect}")

# Extract horizon from label name
import re
horizon_match = re.search(r'(\d+)b', label_inspect)
horizon = int(horizon_match.group(1)) if horizon_match else 6

# Compute forward return manually
df_pd['close_t'] = df_pd[close_col]
df_pd['close_t_plus_h'] = df_pd[close_col].shift(-horizon)
df_pd['computed_fwd_ret'] = np.log(df_pd['close_t_plus_h'] / df_pd['close_t'])
df_pd['stored_label'] = df_pd[label_inspect]

# Previous bar direction
df_pd['prev_close'] = df_pd[close_col].shift(1)
df_pd['prev_ret'] = np.log(df_pd['close_t'] / df_pd['prev_close'])
df_pd['prev_direction'] = (df_pd['prev_ret'] > 0).astype(int)

# Target direction
df_pd['target_direction'] = (df_pd['computed_fwd_ret'] > 0).astype(int)

# Sample rows
print(f"\nSample rows (showing label computation):")
print(f"Horizon: {horizon} bars")

sample_df = df_pd[['time', 'close_t', 'close_t_plus_h', 'computed_fwd_ret',
                     'stored_label', 'prev_direction', 'target_direction']].iloc[100:120]

print("\nFirst 20 sample rows:")
print(sample_df.to_string(index=False))

# Check label alignment
if isinstance(df_pd['stored_label'].iloc[0], (int, float)):
    # Numeric label - check if it matches computed
    correlation = df_pd[['computed_fwd_ret', 'stored_label']].corr().iloc[0, 1]
    print(f"\nCorrelation (computed vs stored): {correlation:.4f}")

    if abs(correlation) < 0.9:
        print(f"✗ WARNING: Low correlation, possible label bug")
    else:
        print(f"✓ Labels aligned (high correlation)")
else:
    print("⚠ Label is not numeric, skipping correlation check")

# Check if features leak future
print(f"\nChecking feature leak...")
# Features should not contain t+h data
# Check: features at row t should be computable with data up to t only

feature_cols = [c['name'] for c in schema['columns']
                if c['role'] == 'feature' and c['allowed_for_training']]

# Spot check: no feature should correlate strongly with future returns
sample_features = feature_cols[:10]
future_ret = df_pd['computed_fwd_ret'].shift(-horizon)

max_leak_corr = 0
leak_feature = None

for feat in sample_features:
    if feat not in df_pd.columns:
        continue
    corr = df_pd[[feat, 'computed_fwd_ret']].corr().iloc[0, 1]
    if abs(corr) > abs(max_leak_corr):
        max_leak_corr = corr
        leak_feature = feat

print(f"Max feature correlation with fwd return: {abs(max_leak_corr):.4f} ({leak_feature})")

if abs(max_leak_corr) > 0.5:
    print(f"✗ CRITICAL: Feature {leak_feature} leaks future (corr={max_leak_corr:.4f})")
    verdict = "LABEL_ALIGNMENT_BUG_FOUND"
else:
    print(f"✓ No obvious feature leakage detected")

# ============================================================================
# 2. PREVIOUS-BAR BASELINE AUDIT
# ============================================================================
print("\n" + "=" * 80)
print("2. PREVIOUS-BAR BASELINE AUDIT")
print("=" * 80)

# Direction autocorrelation
print(f"\nDirection autocorrelation:")
for lag in [1, 3, 6, 12, 24, 48]:
    if 'target_direction' in df_pd.columns:
        lagged = df_pd['target_direction'].shift(lag)
        valid = ~(df_pd['target_direction'].isna() | lagged.isna())

        if valid.sum() > 0:
            autocorr = df_pd.loc[valid, 'target_direction'].corr(lagged[valid])
            print(f"  Lag {lag}b: {autocorr:.4f}")

# Why is previous-bar so good?
# Check direction persistence
direction_changes = (df_pd['target_direction'].diff().abs() == 1).sum()
total_transitions = len(df_pd) - 1

persistence_rate = 1 - (direction_changes / total_transitions)
print(f"\nDirection persistence rate: {persistence_rate:.2%}")
print(f"  (How often direction stays same from one bar to next)")

if persistence_rate > 0.7:
    print(f"  ⚠ HIGH persistence - explains strong previous-bar baseline")
elif persistence_rate > 0.6:
    print(f"  ○ MODERATE persistence")
else:
    print(f"  ✓ LOW persistence")

# Check if prev-bar accidentally uses future
# This should be impossible but verify
prev_bar_uses_t = df_pd['prev_direction'].shift(-1)  # shift forward
future_corr = df_pd[['prev_direction', 'target_direction']].corr().iloc[0, 1]

print(f"\nPrev-bar vs target correlation: {future_corr:.4f}")
if future_corr > 0.6:
    print(f"  Explains AUC=0.87 (high autocorrelation)")

# ============================================================================
# 3. COST AND SHARPE AUDIT
# ============================================================================
print("\n" + "=" * 80)
print("3. COST AND SHARPE AUDIT")
print("=" * 80)

print("\nMetric formulas used in training_validation_clean.py:")
print("  positions = y_pred * 2 - 1  (convert {0,1} to {-1,1})")
print("  pnl = positions * returns")
print("  net_return = pnl.sum()")
print("  sharpe = pnl.mean() / (pnl.std() + 1e-10) * sqrt(252 * 288)")
print("           where 288 = M5 bars per day")

# Check return units
sample_returns = df_pd['computed_fwd_ret'].dropna()
ret_mean = sample_returns.mean()
ret_std = sample_returns.std()
ret_min = sample_returns.min()
ret_max = sample_returns.max()

print(f"\nReturn statistics:")
print(f"  Mean: {ret_mean:.6f}")
print(f"  Std:  {ret_std:.6f}")
print(f"  Min:  {ret_min:.6f}")
print(f"  Max:  {ret_max:.6f}")

if abs(ret_mean) < 0.001:
    print(f"  Units: LOG RETURNS (centered near 0)")
elif abs(ret_mean) < 0.1:
    print(f"  Units: PERCENT (decimal form)")
else:
    print(f"  Units: UNKNOWN (check scale)")

# Sharpe scale check
print(f"\nSharpe annualization factor: sqrt(252 * 288) = {np.sqrt(252 * 288):.1f}")
print(f"  This assumes:")
print(f"    - 252 trading days/year")
print(f"    - 288 M5 bars/day (24h market)")
print(f"    - Returns in decimal form")

print(f"\nIf baseline Sharpe = 170:")
daily_sharpe = 170 / np.sqrt(252 * 288)
print(f"  Daily Sharpe ≈ {daily_sharpe:.2f}")
print(f"  Per-bar Sharpe ≈ {daily_sharpe / np.sqrt(288):.2f}")

if daily_sharpe > 10:
    print(f"  ✗ SUSPICIOUS: Daily Sharpe {daily_sharpe:.1f} >> 5 (realistic max)")
    print(f"  Possible issues:")
    print(f"    - Wrong annualization")
    print(f"    - No transaction costs")
    print(f"    - Label leakage")
    print(f"    - Overfitted test period")

# Transaction cost estimate
# XAUUSD typical spread: 0.3-0.5 USD/oz
# Price ~2000 USD/oz → spread = 0.05% per round-trip
spread_bps = 5  # 5 basis points
spread_decimal = spread_bps / 10000

print(f"\nTransaction cost assumption:")
print(f"  Spread: {spread_bps} bps = {spread_decimal:.5f} per round-trip")

# ============================================================================
# 4. LABEL HORIZON TOURNAMENT
# ============================================================================
print("\n" + "=" * 80)
print("4. LABEL HORIZON TOURNAMENT")
print("=" * 80)

# Find all binary labels
label_candidates = [c for c in label_cols if 'label_' in c and 'fwd_ret' not in c.lower()]

print(f"\nLabel candidates: {len(label_candidates)}")

results = []

for label_name in label_candidates:
    if label_name not in df_pd.columns:
        continue

    # Extract horizon
    horizon_match = re.search(r'(\d+)b', label_name)
    if not horizon_match:
        continue

    h = int(horizon_match.group(1))

    print(f"\n[{label_name}] Horizon: {h} bars ({h*5} minutes)")

    # Get label
    y = df_pd[label_name].dropna()

    if len(y) < 1000:
        print(f"  ✗ Insufficient data ({len(y)} rows)")
        continue

    # Balance
    if y.dtype in [int, float]:
        balance = y.mean()
        print(f"  Balance: {balance:.3f}")
    else:
        print(f"  ✗ Non-numeric label")
        continue

    # Direction autocorrelation
    y_shift1 = df_pd[label_name].shift(1)
    valid = ~(df_pd[label_name].isna() | y_shift1.isna())

    if valid.sum() > 100:
        autocorr_1 = df_pd.loc[valid, label_name].corr(y_shift1[valid])
        print(f"  Autocorr(1): {autocorr_1:.4f}")
    else:
        autocorr_1 = np.nan

    # Baseline metrics (simplified for speed)
    # Use last 20% as test
    n = len(df_pd)
    test_start = int(n * 0.8)

    test_df = df_pd.iloc[test_start:].copy()
    test_y = test_df[label_name].dropna()

    if len(test_y) < 100:
        print(f"  ✗ Insufficient test data")
        continue

    # Previous-bar baseline
    # Need forward return for this label
    fwd_ret_col = f'fwd_ret_{h}b'
    if fwd_ret_col not in test_df.columns:
        # Compute it
        test_df['_temp_fwd_ret'] = np.log(test_df[close_col].shift(-h) / test_df[close_col])
        fwd_ret_col = '_temp_fwd_ret'

    # Align test data
    test_sub = test_df[[label_name, fwd_ret_col, close_col]].dropna()

    if len(test_sub) < 100:
        print(f"  ✗ Insufficient aligned test data")
        continue

    y_test = test_sub[label_name].values
    ret_test = test_sub[fwd_ret_col].values

    # Previous bar
    prev_ret = np.log(test_sub[close_col] / test_sub[close_col].shift(1)).values
    prev_ret = prev_ret[1:]  # drop first NaN
    y_test_prev = y_test[1:]
    ret_test_prev = ret_test[1:]

    if len(y_test_prev) < 100:
        continue

    # Baseline: follow previous bar direction
    pred_prev = (prev_ret > 0).astype(int)

    # AUC (simple accuracy for binary)
    from sklearn.metrics import balanced_accuracy_score
    try:
        prev_acc = balanced_accuracy_score(y_test_prev, pred_prev)
    except:
        prev_acc = np.nan

    # Sharpe (with positions)
    positions = pred_prev * 2 - 1
    pnl = positions * ret_test_prev

    # Apply transaction cost
    # Cost incurred on every position flip
    position_changes = np.abs(np.diff(positions, prepend=0))
    costs = position_changes * spread_decimal
    pnl_net = pnl - costs

    net_return = pnl_net.sum()
    sharpe_raw = pnl_net.mean() / (pnl_net.std() + 1e-10) * np.sqrt(252 * 288)

    # Always-long return
    long_pnl = ret_test_prev
    long_net = long_pnl.sum()

    print(f"  Prev-bar acc: {prev_acc:.3f}")
    print(f"  Prev-bar Sharpe (cost-adj): {sharpe_raw:.1f}")
    print(f"  Always-long return: {long_net:.4f}")

    # Suitable for ML?
    suitable = (prev_acc < 0.85) and (abs(balance - 0.5) < 0.2) and (len(test_sub) > 1000)

    print(f"  ML suitable: {'✓' if suitable else '✗'}")

    results.append({
        'label': label_name,
        'horizon_bars': h,
        'horizon_minutes': h * 5,
        'balance': float(balance),
        'autocorr_1': float(autocorr_1) if not np.isnan(autocorr_1) else None,
        'prev_bar_acc': float(prev_acc) if not np.isnan(prev_acc) else None,
        'prev_bar_sharpe': float(sharpe_raw) if not np.isnan(sharpe_raw) else None,
        'always_long_return': float(long_net),
        'ml_suitable': bool(suitable)
    })

# ============================================================================
# 5. VERDICT
# ============================================================================
print("\n" + "=" * 80)
print("FINAL VERDICT")
print("=" * 80)

# Determine verdict
verdict = "BEST_LABEL_HORIZON_FOUND"

# Check for bugs
if abs(max_leak_corr) > 0.5:
    verdict = "LABEL_ALIGNMENT_BUG_FOUND"
    print(f"\n✗ VERDICT: {verdict}")
    print(f"  Feature {leak_feature} leaks future (corr={max_leak_corr:.4f})")

elif daily_sharpe > 10:
    verdict = "COST_METRIC_BUG_FOUND"
    print(f"\n✗ VERDICT: {verdict}")
    print(f"  Daily Sharpe {daily_sharpe:.1f} >> 5 (unrealistic)")

elif not results or not any(r['ml_suitable'] for r in results):
    verdict = "NO_USABLE_LABEL_YET"
    print(f"\n⚠ VERDICT: {verdict}")
    print(f"  All labels either too easy (acc>0.85) or imbalanced")

else:
    # Find best label
    suitable = [r for r in results if r['ml_suitable']]
    best = min(suitable, key=lambda x: x['prev_bar_acc'])

    print(f"\n✓ VERDICT: {verdict}")
    print(f"  Best label: {best['label']}")
    print(f"  Horizon: {best['horizon_bars']}b ({best['horizon_minutes']}min)")
    print(f"  Prev-bar acc: {best['prev_bar_acc']:.3f}")
    print(f"  Balance: {best['balance']:.3f}")

# Save results
report = {
    'timestamp': datetime.now().isoformat(),
    'dataset': str(DATASET),
    'verdict': verdict,
    'label_alignment': {
        'label_inspected': label_inspect,
        'horizon': int(horizon),
        'max_feature_leak_corr': float(max_leak_corr),
        'leak_feature': leak_feature
    },
    'baseline_audit': {
        'direction_persistence': float(persistence_rate),
        'prev_target_corr': float(future_corr)
    },
    'metric_audit': {
        'return_mean': float(ret_mean),
        'return_std': float(ret_std),
        'sharpe_annualization_factor': float(np.sqrt(252 * 288)),
        'daily_sharpe_if_170': float(daily_sharpe),
        'spread_bps': spread_bps
    },
    'label_tournament': results
}

OUTPUT_JSON.write_text(json.dumps(report, indent=2))
print(f"\nReport saved: {OUTPUT_JSON}")

# Save tournament CSV
if results:
    import pandas as pd
    pd.DataFrame(results).to_csv('runs/label_horizon_tournament.csv', index=False)
    print(f"Tournament CSV saved: runs/label_horizon_tournament.csv")

print("=" * 80)
