#!/usr/bin/env python3
"""
Cost-aware training experiment on label_288b.
Proper cost modeling, fold validation, baseline comparison.
"""
import polars as pl
import numpy as np
import pandas as pd
from pathlib import Path
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, balanced_accuracy_score, f1_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Try LightGBM
try:
    import lightgbm as lgb
    HAS_LGBM = True
except:
    HAS_LGBM = False
    print("⚠ LightGBM not available")

DATASET = Path("data/hydra_xauusd_m5_master_clean.parquet")
SCHEMA = Path("data/hydra_xauusd_m5_master_schema.json")
OUTPUT_MD = Path("reports/cost_aware_label_288b_report.md")
OUTPUT_JSON = Path("reports/cost_aware_label_288b_summary.json")
OUTPUT_CSV = Path("runs/cost_aware_label_288b_results.csv")

OUTPUT_CSV.parent.mkdir(exist_ok=True)

print("=" * 80)
print("COST-AWARE TRAINING: LABEL_288B")
print("=" * 80)

# Load schema
schema = json.loads(SCHEMA.read_text())

# Extract features (strict filtering)
forbidden_patterns = ['fwd', 'forward', 'future', 'next', 'lead', 'target', 'label', 'y_']

feature_cols = [
    c['name'] for c in schema['columns']
    if c['role'] == 'feature'
    and c.get('allowed_for_training', False)
    and not c.get('is_forward_looking', False)
    and not any(p in c['name'].lower() for p in forbidden_patterns)
]

print(f"\nSchema-driven features: {len(feature_cols)}")

# Load dataset
df = pl.read_parquet(DATASET)
print(f"Dataset: {df.shape[0]:,} rows × {df.shape[1]:,} cols")

# Load close prices
raw_df = pl.read_parquet('data/mt5_history/XAUUSD_M5_dukascopy.parquet')
close_prices = raw_df.select(['time', 'close']).to_pandas()

# Convert to pandas
df_pd = df.to_pandas()
df_pd = df_pd.merge(close_prices, on='time', how='left')
df_pd = df_pd.sort_values('time').reset_index(drop=True)

# Get label
LABEL = 'label_288b'
HORIZON = 288

if LABEL not in df_pd.columns:
    print(f"✗ {LABEL} not found")
    exit(1)

# Filter nulls
df_pd = df_pd.dropna(subset=[LABEL, 'close'])
print(f"After label dropna: {len(df_pd):,} rows")

# Balance
y_balance = df_pd[LABEL].mean()
print(f"Label balance: {y_balance:.3f}")

# Features
valid_features = [f for f in feature_cols if f in df_pd.columns]
print(f"Valid features: {len(valid_features)}")

# Fill nulls
df_pd[valid_features] = df_pd[valid_features].fillna(0).replace([np.inf, -np.inf], [1e10, -1e10])

# Compute forward return (for trading metrics)
df_pd['fwd_ret'] = np.log(df_pd['close'].shift(-HORIZON) / df_pd['close'])

# ============================================================================
# CHRONOLOGICAL FOLDS
# ============================================================================
print("\n" + "=" * 80)
print("FOLD SETUP")
print("=" * 80)

N_FOLDS = 5
EMBARGO = HORIZON  # 288 bars

n_rows = len(df_pd)
fold_size = n_rows // N_FOLDS

folds = []
for i in range(N_FOLDS):
    train_end = (i + 1) * fold_size
    test_start = train_end + EMBARGO
    test_end = min(test_start + fold_size, n_rows)

    if test_start >= n_rows:
        break

    train_idx = list(range(train_end))
    test_idx = list(range(test_start, test_end))

    folds.append({
        'fold': i + 1,
        'train_idx': train_idx,
        'test_idx': test_idx,
        'train_size': len(train_idx),
        'test_size': len(test_idx)
    })

print(f"Folds: {len(folds)}")
for fold in folds:
    print(f"  Fold {fold['fold']}: train={fold['train_size']:,}, test={fold['test_size']:,}, embargo={EMBARGO}")

# ============================================================================
# COST SCENARIOS
# ============================================================================
COST_SCENARIOS = [0, 1, 2, 5]  # bps

print(f"\nCost scenarios: {COST_SCENARIOS} bps")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def compute_trading_metrics(y_true, y_pred, returns, cost_bps):
    """Compute trading metrics with costs."""
    # Positions: {0,1} -> {-1, +1}
    positions = y_pred * 2 - 1

    # Gross PnL
    pnl_gross = positions * returns

    # Cost
    position_changes = np.abs(np.diff(positions, prepend=0))
    cost_per_flip = cost_bps / 10000
    costs = position_changes * cost_per_flip

    # Net PnL
    pnl_net = pnl_gross - costs

    # Metrics
    gross_return = pnl_gross.sum()
    net_return = pnl_net.sum()
    cost_paid = costs.sum()
    turnover = position_changes.sum()

    # Sharpe (annualized)
    if pnl_net.std() > 0:
        sharpe = pnl_net.mean() / pnl_net.std() * np.sqrt(252 * 288)
    else:
        sharpe = 0

    # Max drawdown
    cum = np.cumsum(pnl_net)
    running_max = np.maximum.accumulate(cum)
    drawdown = running_max - cum
    max_dd = drawdown.max()

    return {
        'gross_return': float(gross_return),
        'net_return': float(net_return),
        'cost_paid': float(cost_paid),
        'turnover': float(turnover),
        'sharpe': float(sharpe),
        'max_drawdown': float(max_dd),
        'avg_return_per_bar': float(pnl_net.mean()),
        'avg_return_per_trade': float(pnl_net.sum() / (turnover / 2 + 1e-10))
    }

def compute_classification_metrics(y_true, y_pred, y_proba):
    """Compute classification metrics."""
    try:
        auc = roc_auc_score(y_true, y_proba)
    except:
        auc = 0.5

    bal_acc = balanced_accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)

    pred_pos_rate = y_pred.mean()
    true_pos_rate = y_true.mean()

    return {
        'auc': float(auc),
        'balanced_accuracy': float(bal_acc),
        'f1': float(f1),
        'precision': float(precision),
        'recall': float(recall),
        'pred_positive_rate': float(pred_pos_rate),
        'class_balance': float(true_pos_rate)
    }

# ============================================================================
# BASELINE MODELS
# ============================================================================
print("\n" + "=" * 80)
print("BASELINE EVALUATION")
print("=" * 80)

baseline_results = []

for fold in folds:
    test_idx = fold['test_idx']
    test_df = df_pd.iloc[test_idx].copy()

    y_test = test_df[LABEL].values
    ret_test = test_df['fwd_ret'].values

    # Drop NaNs
    valid = ~(np.isnan(y_test) | np.isnan(ret_test))
    y_test = y_test[valid]
    ret_test = ret_test[valid]

    if len(y_test) < 10:
        continue

    # Baselines
    baselines = {
        'always_long': np.ones_like(y_test),
        'always_short': np.zeros_like(y_test),
        'random': np.random.binomial(1, 0.5, len(y_test))
    }

    # Previous bar
    prev_ret = np.log(test_df['close'] / test_df['close'].shift(1)).values[valid]
    baselines['previous_bar'] = (prev_ret > 0).astype(int)

    # Momentum
    for w in [12, 72]:
        mom = test_df['close'].rolling(w).mean().values[valid]
        mom_signal = (test_df['close'].values[valid] > mom).astype(int)
        baselines[f'momentum_{w}'] = mom_signal

    # Mean reversion
    for w in [12, 72]:
        mean = test_df['close'].rolling(w).mean().values[valid]
        std = test_df['close'].rolling(w).std().values[valid] + 1e-10
        z = (test_df['close'].values[valid] - mean) / std
        mr_signal = (z < 0).astype(int)
        baselines[f'mean_reversion_{w}'] = mr_signal

    # Evaluate each baseline × cost scenario
    for baseline_name, y_pred in baselines.items():
        for cost_bps in COST_SCENARIOS:
            y_proba = y_pred  # For baselines, use pred as proba

            class_metrics = compute_classification_metrics(y_test, y_pred, y_proba)
            trade_metrics = compute_trading_metrics(y_test, y_pred, ret_test, cost_bps)

            baseline_results.append({
                'model': baseline_name,
                'fold': fold['fold'],
                'cost_bps': cost_bps,
                **class_metrics,
                **trade_metrics
            })

print(f"Baseline results: {len(baseline_results)} entries")

# ============================================================================
# ML MODELS
# ============================================================================
print("\n" + "=" * 80)
print("ML MODEL TRAINING")
print("=" * 80)

# Feature sets
from sklearn.ensemble import RandomForestClassifier as RFC_quick
X_sample = df_pd[valid_features].iloc[::10].values
y_sample = df_pd[LABEL].iloc[::10].values
rf_quick = RFC_quick(n_estimators=20, max_depth=5, random_state=42, n_jobs=-1)
rf_quick.fit(X_sample, y_sample)
importance = rf_quick.feature_importances_

feature_ranking = sorted(zip(valid_features, importance), key=lambda x: x[1], reverse=True)

top_100 = [f[0] for f in feature_ranking[:100]]
top_200 = [f[0] for f in feature_ranking[:200]]
all_features = valid_features

feature_sets = {
    'top_100': top_100,
    'top_200': top_200,
    'all': all_features
}

# Models
models_config = []

if HAS_LGBM:
    models_config.append(('lgbm', 'LightGBM'))

models_config.extend([
    ('gb', 'GradientBoosting'),
    ('rf', 'RandomForest')
])

ml_results = []

for model_type, model_name in models_config:
    for feature_set_name, features in feature_sets.items():
        print(f"\n[{model_name} / {feature_set_name}]")

        for fold in folds:
            train_idx = fold['train_idx']
            test_idx = fold['test_idx']

            X_train = df_pd.iloc[train_idx][features].values
            y_train = df_pd.iloc[train_idx][LABEL].values
            X_test = df_pd.iloc[test_idx][features].values
            y_test = df_pd.iloc[test_idx][LABEL].values
            ret_test = df_pd.iloc[test_idx]['fwd_ret'].values

            # Drop NaNs
            valid_train = ~np.isnan(y_train)
            valid_test = ~(np.isnan(y_test) | np.isnan(ret_test))

            X_train = X_train[valid_train]
            y_train = y_train[valid_train]
            X_test = X_test[valid_test]
            y_test = y_test[valid_test]
            ret_test = ret_test[valid_test]

            if len(X_train) < 100 or len(X_test) < 10:
                print(f"  Fold {fold['fold']}: insufficient data")
                continue

            # Scale
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train
            if model_type == 'lgbm':
                model = lgb.LGBMClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1, verbose=-1)
            elif model_type == 'gb':
                model = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
            else:  # rf
                model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

            model.fit(X_train_scaled, y_train)

            # Predict
            y_pred = model.predict(X_test_scaled)
            y_proba = model.predict_proba(X_test_scaled)[:, 1]

            # Evaluate for each cost scenario
            for cost_bps in COST_SCENARIOS:
                class_metrics = compute_classification_metrics(y_test, y_pred, y_proba)
                trade_metrics = compute_trading_metrics(y_test, y_pred, ret_test, cost_bps)

                ml_results.append({
                    'model': f'{model_name}_{feature_set_name}',
                    'fold': fold['fold'],
                    'cost_bps': cost_bps,
                    **class_metrics,
                    **trade_metrics
                })

            print(f"  Fold {fold['fold']}: AUC={class_metrics['auc']:.3f}")

print(f"\nML results: {len(ml_results)} entries")

# ============================================================================
# AGGREGATE & VERDICT
# ============================================================================
print("\n" + "=" * 80)
print("AGGREGATION & VERDICT")
print("=" * 80)

# Combine results
all_results = baseline_results + ml_results
df_results = pd.DataFrame(all_results)

# Save CSV
df_results.to_csv(OUTPUT_CSV, index=False)
print(f"Results CSV: {OUTPUT_CSV}")

# Aggregate by model × cost
agg = df_results.groupby(['model', 'cost_bps']).agg({
    'auc': 'mean',
    'balanced_accuracy': 'mean',
    'sharpe': ['mean', 'std'],
    'net_return': ['mean', 'std'],
    'gross_return': 'mean',
    'cost_paid': 'mean',
    'turnover': 'mean'
}).reset_index()

agg.columns = ['_'.join(col).strip('_') for col in agg.columns.values]

# Find best ML model at 5 bps
ml_5bps = df_results[(df_results['model'].str.contains('LightGBM|Gradient|Random')) &
                      (df_results['cost_bps'] == 5)]

if len(ml_5bps) > 0:
    best_ml = ml_5bps.groupby('model').agg({'net_return': 'mean', 'sharpe': 'mean'}).sort_values('sharpe', ascending=False).iloc[0]
    best_ml_name = ml_5bps.groupby('model').agg({'sharpe': 'mean'}).sort_values('sharpe', ascending=False).index[0]

    # Count winning folds
    best_ml_folds = ml_5bps[ml_5bps['model'] == best_ml_name]

    # Compare to best baseline
    baseline_5bps = df_results[(~df_results['model'].str.contains('LightGBM|Gradient|Random')) &
                                (df_results['cost_bps'] == 5)]

    best_baseline = baseline_5bps.groupby('model').agg({'sharpe': 'mean'}).sort_values('sharpe', ascending=False).iloc[0]
    best_baseline_name = baseline_5bps.groupby('model').agg({'sharpe': 'mean'}).sort_values('sharpe', ascending=False).index[0]

    # Verdict logic
    ml_sharpe = best_ml['sharpe']
    ml_return = best_ml['net_return']

    # Fold stability: count folds where ML > best baseline
    baseline_sharpe_by_fold = baseline_5bps[baseline_5bps['model'] == best_baseline_name].set_index('fold')['sharpe']
    ml_sharpe_by_fold = best_ml_folds.set_index('fold')['sharpe']

    wins = 0
    for fold_id in ml_sharpe_by_fold.index:
        if fold_id in baseline_sharpe_by_fold.index:
            if ml_sharpe_by_fold[fold_id] > baseline_sharpe_by_fold[fold_id]:
                wins += 1

    print(f"\nBest ML: {best_ml_name}")
    print(f"  Sharpe: {ml_sharpe:.2f}")
    print(f"  Net return: {ml_return:.4f}")
    print(f"  Wins vs baseline: {wins}/{len(best_ml_folds)} folds")

    print(f"\nBest baseline: {best_baseline_name}")
    print(f"  Sharpe: {best_baseline['sharpe']:.2f}")

    # Verdict
    if ml_return > 0 and ml_sharpe > 1 and wins >= 4:
        verdict = "EDGE_FOUND"
    elif ml_return > 0 and ml_sharpe > 0.5 and wins >= 3:
        verdict = "EDGE_WEAK"
    elif ml_return < 0 or wins < 3:
        verdict = "NO_EDGE_AFTER_COSTS"
    else:
        verdict = "EDGE_WEAK"

    # Sanity checks
    if ml_sharpe > 10:
        print(f"\n⚠ WARNING: Sharpe {ml_sharpe:.1f} > 10 (suspicious)")
        print(f"  Formula: pnl.mean() / pnl.std() * sqrt(252 * 288)")
        print(f"  Daily Sharpe: {ml_sharpe / 269.4:.2f}")

else:
    verdict = "VALIDATION_BUG_FOUND"
    print("✗ No ML results at 5 bps")

print(f"\n{'='*80}")
print(f"VERDICT: {verdict}")
print(f"{'='*80}")

# Save summary
summary = {
    'timestamp': datetime.now().isoformat(),
    'dataset': str(DATASET),
    'label': LABEL,
    'horizon': HORIZON,
    'n_folds': len(folds),
    'embargo': EMBARGO,
    'n_features': len(valid_features),
    'verdict': verdict,
    'best_ml': {
        'model': best_ml_name if len(ml_5bps) > 0 else None,
        'sharpe': float(ml_sharpe) if len(ml_5bps) > 0 else None,
        'net_return': float(ml_return) if len(ml_5bps) > 0 else None,
        'wins_vs_baseline': int(wins) if len(ml_5bps) > 0 else None
    } if len(ml_5bps) > 0 else {},
    'cost_scenarios': COST_SCENARIOS
}

OUTPUT_JSON.write_text(json.dumps(summary, indent=2))
print(f"\nSummary: {OUTPUT_JSON}")

print("="*80)
