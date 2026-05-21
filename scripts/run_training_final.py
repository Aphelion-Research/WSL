#!/usr/bin/env python3
"""Walk-forward training on hydra_xauusd_m5_master.parquet."""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

try:
    import lightgbm as lgb
    HAS_LGBM = True
except ImportError:
    HAS_LGBM = False
    print("LightGBM not available")

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("XGBoost not available")


DATASET = Path("data/hydra_xauusd_m5_master.parquet")
LABEL = "label_12b"
FOLDS = 5
EMBARGO = 60
OUTPUT_DIR = Path("runs")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    print(f"Loading {DATASET}...")
    df = pd.read_parquet(DATASET)
    print(f"  {len(df)} rows, {len(df.columns)} cols")
    print(f"  Range: {df.index.min()} to {df.index.max()}")

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    if LABEL not in df.columns:
        raise ValueError(f"Label {LABEL} not found. Available: {label_cols}")

    # Drop rows with NaN label
    df = df[df[LABEL].notna()].copy()
    print(f"  After dropping NaN labels: {len(df)} rows")

    y = df[LABEL].astype(int).values
    X = df[feature_cols].values

    pos = (y == 1).sum()
    neg = (y == 0).sum()
    print(f"  Labels: {pos} long ({pos/(pos+neg)*100:.1f}%), {neg} short ({neg/(pos+neg)*100:.1f}%)")
    print(f"  Features: {len(feature_cols)}")

    return X, y, feature_cols, df.index


def walk_forward_split(n, folds, embargo):
    """Generate chronological train/test indices with embargo."""
    fold_size = n // folds
    splits = []
    for i in range(folds):
        test_start = i * fold_size
        test_end = test_start + fold_size if i < folds - 1 else n
        train_end = test_start - embargo if test_start >= embargo else 0
        if train_end < fold_size:
            continue
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)
        splits.append((train_idx, test_idx))
    return splits


def evaluate(y_true, y_pred_proba):
    y_pred = (y_pred_proba >= 0.5).astype(int)
    acc = accuracy_score(y_true, y_pred)
    try:
        auc = roc_auc_score(y_true, y_pred_proba)
    except:
        auc = 0.5

    # Net returns (simplified: assume ATR = 1%)
    returns = np.where(y_pred == 1, 0.015, -0.015)
    correct = (y_pred == y_true)
    net_returns = returns * np.where(correct, 1, -1)
    cumul = (1 + net_returns).prod() - 1
    mean_ret = net_returns.mean()
    std_ret = net_returns.std() + 1e-10
    sharpe = mean_ret / std_ret * np.sqrt(252)

    return {
        'auc': auc,
        'acc': acc,
        'net_ret_pct': cumul * 100,
        'sharpe': sharpe
    }


def train_model(model_name, X_train, y_train, X_test, y_test):
    print(f"    Training {model_name}...")
    scaler = RobustScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    if model_name == 'LightGBM' and HAS_LGBM:
        model = lgb.LGBMClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=8,
            num_leaves=31,
            n_jobs=-1,
            random_state=42,
            verbosity=-1
        )
        model.fit(X_train_sc, y_train)
        y_pred_proba = model.predict_proba(X_test_sc)[:, 1]

    elif model_name == 'XGBoost' and HAS_XGB:
        model = xgb.XGBClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=8,
            tree_method='hist',
            n_jobs=-1,
            random_state=42,
            verbosity=0
        )
        model.fit(X_train_sc, y_train)
        y_pred_proba = model.predict_proba(X_test_sc)[:, 1]

    elif model_name == 'RandomForest':
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            n_jobs=-1,
            random_state=42
        )
        model.fit(X_train_sc, y_train)
        y_pred_proba = model.predict_proba(X_test_sc)[:, 1]

    else:
        return None

    metrics = evaluate(y_test, y_pred_proba)
    return metrics, model


def main():
    print("="*60)
    print("WALK-FORWARD TRAINING")
    print("="*60)

    X, y, feature_cols, index = load_data()
    n = len(X)

    splits = walk_forward_split(n, FOLDS, EMBARGO)
    print(f"\nGenerated {len(splits)} folds with {EMBARGO}-bar embargo")

    models = ['RandomForest']
    if HAS_LGBM:
        models.insert(0, 'LightGBM')
    if HAS_XGB:
        models.insert(1, 'XGBoost')

    results = []

    for fold_idx, (train_idx, test_idx) in enumerate(splits, 1):
        print(f"\n--- Fold {fold_idx}/{len(splits)} ---")
        print(f"  Train: {len(train_idx)} bars | Test: {len(test_idx)} bars")

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        for model_name in models:
            result = train_model(model_name, X_train, y_train, X_test, y_test)
            if result is None:
                continue
            metrics, model = result
            results.append({
                'model': model_name,
                'fold': fold_idx,
                **metrics
            })
            print(f"      {model_name}: AUC={metrics['auc']:.3f} | Acc={metrics['acc']:.3f} | Ret={metrics['net_ret_pct']:.2f}% | Sharpe={metrics['sharpe']:.2f}")

    # Save results
    results_df = pd.DataFrame(results)
    results_csv = OUTPUT_DIR / f"wf_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(results_csv, index=False)
    print(f"\nResults saved: {results_csv}")

    # Summary table
    print("\n" + "="*60)
    print("RESULTS SUMMARY")
    print("="*60)
    print("\n╔════════════╦═══════╦═══════╦═══════╦════════════╦════════╗")
    print("║ Model      ║ Fold  ║  AUC  ║  Acc  ║ Net Ret %  ║ Sharpe ║")
    print("╠════════════╬═══════╬═══════╬═══════╬════════════╬════════╣")

    for _, row in results_df.iterrows():
        print(f"║ {row['model']:<10} ║   {row['fold']}   ║ {row['auc']:5.3f} ║ {row['acc']:5.3f} ║  {row['net_ret_pct']:7.2f}   ║ {row['sharpe']:6.2f} ║")

    print("╠════════════╬═══════╬═══════╬═══════╬════════════╬════════╣")

    # Averages per model
    for model_name in results_df['model'].unique():
        subset = results_df[results_df['model'] == model_name]
        avg_auc = subset['auc'].mean()
        avg_acc = subset['acc'].mean()
        avg_ret = subset['net_ret_pct'].mean()
        avg_sharpe = subset['sharpe'].mean()
        print(f"║ {model_name:<10} ║  AVG  ║ {avg_auc:5.3f} ║ {avg_acc:5.3f} ║  {avg_ret:7.2f}   ║ {avg_sharpe:6.2f} ║")

    print("╚════════════╩═══════╩═══════╩═══════╩════════════╩════════╝")

    # Verdict
    best_model = results_df.groupby('model')['auc'].mean().idxmax()
    best_auc = results_df.groupby('model')['auc'].mean().max()
    best_sharpe = results_df.groupby('model')['sharpe'].mean().max()

    print(f"\nBest model: {best_model} | AUC={best_auc:.3f} | Sharpe={best_sharpe:.2f}")

    if best_auc > 0.57 and best_sharpe > 0.5:
        verdict = "EDGE EXISTS"
    elif best_auc > 0.53:
        verdict = "WEAK EDGE"
    else:
        verdict = "NO EDGE"

    print(f"Verdict: {verdict}")
    print("="*60)

    # Write final report
    report = OUTPUT_DIR / "FINAL_REPORT.md"
    with open(report, 'w') as f:
        f.write("# HYDRA XAUUSD M5 MASTER DATASET — TRAINING RESULTS\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Dataset\n\n")
        f.write(f"- **File:** {DATASET}\n")
        f.write(f"- **Rows:** {n}\n")
        f.write(f"- **Features:** {len(feature_cols)}\n")
        f.write(f"- **Label:** {LABEL}\n")
        f.write(f"- **Date range:** {index.min()} to {index.max()}\n\n")
        f.write(f"## Walk-Forward Results\n\n")
        f.write("```\n")
        f.write("╔════════════╦═══════╦═══════╦═══════╦════════════╦════════╗\n")
        f.write("║ Model      ║ Fold  ║  AUC  ║  Acc  ║ Net Ret %  ║ Sharpe ║\n")
        f.write("╠════════════╬═══════╬═══════╬═══════╬════════════╬════════╣\n")
        for _, row in results_df.iterrows():
            f.write(f"║ {row['model']:<10} ║   {row['fold']}   ║ {row['auc']:5.3f} ║ {row['acc']:5.3f} ║  {row['net_ret_pct']:7.2f}   ║ {row['sharpe']:6.2f} ║\n")
        f.write("╠════════════╬═══════╬═══════╬═══════╬════════════╬════════╣\n")
        for model_name in results_df['model'].unique():
            subset = results_df[results_df['model'] == model_name]
            avg_auc = subset['auc'].mean()
            avg_acc = subset['acc'].mean()
            avg_ret = subset['net_ret_pct'].mean()
            avg_sharpe = subset['sharpe'].mean()
            f.write(f"║ {model_name:<10} ║  AVG  ║ {avg_auc:5.3f} ║ {avg_acc:5.3f} ║  {avg_ret:7.2f}   ║ {avg_sharpe:6.2f} ║\n")
        f.write("╚════════════╩═══════╩═══════╩═══════╩════════════╩════════╝\n")
        f.write("```\n\n")
        f.write(f"## Verdict\n\n")
        f.write(f"**{verdict}**\n\n")
        f.write(f"- Best model: {best_model}\n")
        f.write(f"- Best AUC: {best_auc:.3f}\n")
        f.write(f"- Best Sharpe: {best_sharpe:.2f}\n")

    print(f"\nFinal report: {report}")


if __name__ == "__main__":
    main()
