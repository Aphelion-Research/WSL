#!/usr/bin/env python3
"""
Walk-forward validation for HYDRA M5 dataset.

Chronological folds with embargo/purge for realistic research evaluation.
"""
import sys
import json
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, precision_score, recall_score

try:
    import lightgbm as lgb
    LGBM_AVAILABLE = True
except ImportError:
    LGBM_AVAILABLE = False
    print("⚠️  LightGBM not available")


def load_dataset(path: str) -> Tuple[pd.DataFrame, List[str], str]:
    """Load dataset, validate, and identify features/labels."""
    print(f"Loading {path}...")
    df = pd.read_parquet(path)

    # Validate shape
    if df.shape[1] != 3001:
        raise ValueError(f"Shape violation: expected 3001 cols, got {df.shape[1]}")

    # Get features (exclude time, labels)
    feature_cols = [c for c in df.columns if not c.startswith(('time', 'Z4_'))]
    feature_cols = [c for c in feature_cols if df[c].notna().sum() > len(df) * 0.05]

    # Identify label (use first available)
    label_col = None
    for candidate in ['Z4_0000', 'Z4_0001', 'Z4_0002']:
        if candidate in df.columns and df[candidate].notna().sum() > 100:
            label_col = candidate
            break

    if label_col is None:
        raise ValueError("No valid label column found")

    print(f"✓ Shape: {df.shape}")
    print(f"✓ Features: {len(feature_cols)}")
    print(f"✓ Label: {label_col}")

    return df, feature_cols, label_col


def create_chronological_folds(df: pd.DataFrame, n_folds: int = 5,
                                embargo_bars: int = 60, min_test_rows: int = 500) -> List[Tuple[np.ndarray, np.ndarray, str]]:
    """
    Create chronological train/test folds with embargo.

    Returns: List[(train_idx, test_idx, fold_status)]
    fold_status: VALID | INVALID_TOO_SMALL | INVALID_PAST_END
    """
    print(f"\nCreating {n_folds} chronological folds (embargo={embargo_bars} bars, min_test={min_test_rows})...")

    n = len(df)
    fold_size = n // (n_folds + 1)

    folds = []

    for i in range(n_folds):
        # Train: all data up to fold boundary
        train_end = fold_size * (i + 1)
        train_idx = np.arange(0, train_end)

        # Embargo
        embargo_start = train_end
        embargo_end = min(embargo_start + embargo_bars, n)

        # Test
        test_start = embargo_end
        test_end = min(test_start + fold_size, n)

        # Validate fold
        test_size = test_end - test_start

        if test_end > n:
            status = "INVALID_PAST_END"
        elif test_size < min_test_rows:
            status = "INVALID_TOO_SMALL"
        else:
            status = "VALID"

        test_idx = np.arange(test_start, min(test_end, n))

        folds.append((train_idx, test_idx, status))

        print(f"  Fold {i+1}: train={len(train_idx)}, test={len(test_idx)}, status={status}")

    return folds


def validate_fold_data(y_train: pd.Series, y_test: pd.Series, forward_returns_test: pd.Series) -> str:
    """
    Validate fold data before training.

    Returns fold status:
    - VALID
    - INVALID_EMPTY
    - INVALID_ONE_CLASS
    - INVALID_NAN_LABELS
    - INVALID_CONSTANT_RETURNS
    """
    if len(y_test) == 0:
        return "INVALID_EMPTY"

    # Check for NaN labels
    if y_test.isna().any():
        return "INVALID_NAN_LABELS"

    # Check class diversity (need both 0 and 1)
    n_classes = y_test.nunique()
    if n_classes < 2:
        return "INVALID_ONE_CLASS"

    # Check if returns are constant (std = 0)
    if forward_returns_test.std() < 1e-10:
        return "INVALID_CONSTANT_RETURNS"

    return "VALID"


def compute_cost_aware_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray,
                                forward_returns: pd.Series, spread_pips: float = 2.0) -> Dict:
    """
    Compute cost-aware performance metrics.

    Args:
        y_true: actual labels (0/1)
        y_pred: predicted labels (0/1)
        y_proba: prediction probabilities
        forward_returns: actual forward returns (pct)
        spread_pips: round-trip cost in pips (default 2.0)
    """
    # Basic classification metrics
    acc = accuracy_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    # AUC (safe for one-class case)
    try:
        if len(np.unique(y_true)) >= 2:
            auc = roc_auc_score(y_true, y_proba)
        else:
            auc = None  # Can't compute AUC with one class
    except:
        auc = None

    prec = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)

    # Predicted positive rate
    pred_pos_rate = y_pred.mean() if len(y_pred) > 0 else None

    # Returns when long/short
    long_mask = y_pred == 1
    short_mask = y_pred == 0

    ret_when_long = forward_returns[long_mask].mean() if long_mask.sum() > 0 else None
    ret_when_short = -forward_returns[short_mask].mean() if short_mask.sum() > 0 else None

    # Average return per prediction
    strategy_returns = np.where(y_pred == 1, forward_returns, -forward_returns)

    # Check for valid returns
    if len(strategy_returns) == 0 or np.all(np.isnan(strategy_returns)):
        return {
            'accuracy': acc,
            'f1': f1,
            'auc': auc,
            'precision': prec,
            'recall': recall,
            'pred_pos_rate': pred_pos_rate,
            'ret_when_long_pct': ret_when_long * 100 if ret_when_long is not None else None,
            'ret_when_short_pct': ret_when_short * 100 if ret_when_short is not None else None,
            'avg_return_raw_pct': None,
            'avg_return_net_pct': None,
            'cum_return_raw_pct': None,
            'cum_return_net_pct': None,
            'max_drawdown_pct': None,
            'sharpe_proxy': None,
            'error': 'INVALID_RETURNS'
        }

    avg_return_raw = np.nanmean(strategy_returns)

    # Cost-adjusted return
    cost_per_trade = spread_pips * 0.005 / 100
    avg_return_net = avg_return_raw - cost_per_trade

    # Cumulative returns
    cum_return_raw = np.nansum(strategy_returns)
    cum_return_net = cum_return_raw - (cost_per_trade * len(strategy_returns))

    # Max drawdown
    cum_rets = np.nancumsum(strategy_returns)
    if len(cum_rets) > 0:
        running_max = np.maximum.accumulate(cum_rets)
        drawdown = cum_rets - running_max
        max_dd = np.nanmin(drawdown)
    else:
        max_dd = None

    # Sharpe proxy (safe for zero std)
    ret_std = np.nanstd(strategy_returns)
    if ret_std > 1e-10:
        sharpe = avg_return_net / ret_std
    else:
        sharpe = None

    return {
        'accuracy': acc,
        'f1': f1,
        'auc': auc,
        'precision': prec,
        'recall': recall,
        'pred_pos_rate': pred_pos_rate,
        'ret_when_long_pct': ret_when_long * 100 if ret_when_long is not None else None,
        'ret_when_short_pct': ret_when_short * 100 if ret_when_short is not None else None,
        'avg_return_raw_pct': avg_return_raw * 100 if not np.isnan(avg_return_raw) else None,
        'avg_return_net_pct': avg_return_net * 100 if not np.isnan(avg_return_net) else None,
        'cum_return_raw_pct': cum_return_raw * 100 if not np.isnan(cum_return_raw) else None,
        'cum_return_net_pct': cum_return_net * 100 if not np.isnan(cum_return_net) else None,
        'max_drawdown_pct': max_dd * 100 if max_dd is not None and not np.isnan(max_dd) else None,
        'sharpe_proxy': sharpe if sharpe is not None and not np.isnan(sharpe) else None,
    }


def compute_baselines(forward_returns: pd.Series) -> Dict:
    """Compute baseline strategy metrics."""
    # Always long
    always_long = forward_returns.mean() * 100

    # Always short
    always_short = -forward_returns.mean() * 100

    # Random 50/50
    random_dir = np.random.choice([-1, 1], size=len(forward_returns))
    random_ret = (forward_returns * random_dir).mean() * 100

    # Previous bar direction
    prev_ret = forward_returns.shift(1)
    prev_dir = (prev_ret > 0).astype(int) * 2 - 1  # -1 or 1
    prev_dir_ret = (forward_returns * prev_dir).mean() * 100

    # Simple momentum (positive if last 5 bars up)
    mom_signal = (forward_returns.rolling(5).sum() > 0).astype(int) * 2 - 1
    mom_ret = (forward_returns * mom_signal).mean() * 100

    # Mean reversion (negative of momentum)
    mr_ret = (forward_returns * -mom_signal).mean() * 100

    return {
        'always_long': always_long,
        'always_short': always_short,
        'random_50_50': random_ret,
        'prev_bar_direction': prev_dir_ret,
        'momentum_5bar': mom_ret,
        'mean_reversion_5bar': mr_ret,
    }


def train_fold(X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series,
               forward_returns_test: pd.Series, model_type: str, model_params: Dict, seed: int,
               fold_status: str) -> Tuple[Dict, str]:
    """
    Train single fold and return metrics + validation status.

    Returns: (metrics_dict, final_status)
    """

    # Check fold split status first
    if fold_status != "VALID":
        return {'error': f'Fold split invalid: {fold_status}'}, fold_status

    # Validate fold data
    data_status = validate_fold_data(y_train, y_test, forward_returns_test)
    if data_status != "VALID":
        return {'error': f'Fold data invalid: {data_status}'}, data_status

    # Scale features
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train.fillna(0))
    X_test_scaled = scaler.transform(X_test.fillna(0))

    # Train model
    if model_type == 'rf':
        model = RandomForestClassifier(n_estimators=100, random_state=seed, n_jobs=-1, **model_params)
    elif model_type == 'gbm':
        model = GradientBoostingClassifier(n_estimators=100, random_state=seed, **model_params)
    elif model_type == 'lgbm' and LGBM_AVAILABLE:
        model = lgb.LGBMClassifier(n_estimators=100, random_state=seed, n_jobs=-1, verbose=-1, **model_params)
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    start = time.time()
    model.fit(X_train_scaled, y_train)
    elapsed = time.time() - start

    # Predict
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Compute metrics
    metrics = compute_cost_aware_metrics(y_test.values, y_pred, y_proba, forward_returns_test)
    metrics['elapsed_seconds'] = elapsed
    metrics['model_type'] = model_type

    return metrics, "VALID"


def main(dataset_path: str = "data/hydra_m5_dataset.parquet", n_folds: int = 5,
         embargo_bars: int = 60, output_dir: str = "runs"):
    """Run walk-forward validation."""

    print("="*80)
    print("WALK-FORWARD VALIDATION")
    print("="*80)
    print(f"Dataset: {dataset_path}")
    print(f"Folds: {n_folds}")
    print(f"Embargo: {embargo_bars} bars")
    print("="*80 + "\n")

    # Load data
    df, feature_cols, label_col = load_dataset(dataset_path)

    # Prepare features and labels
    X = df[feature_cols]
    y = (df[label_col] > 0).astype(int)
    forward_returns = df[label_col]  # Raw forward returns

    # Remove rows with null labels
    valid_mask = ~y.isna()
    X = X[valid_mask]
    y = y[valid_mask]
    forward_returns = forward_returns[valid_mask]

    print(f"\nValid samples: {len(X)} (label rate: {y.mean():.3f})\n")

    # Create folds
    folds = create_chronological_folds(df[valid_mask].reset_index(drop=True), n_folds, embargo_bars)

    # Compute baselines
    print("\nComputing baselines...")
    baselines = compute_baselines(forward_returns)
    print("Baselines (avg return %):")
    for name, val in baselines.items():
        print(f"  {name}: {val:.4f}%")

    # Models to test
    models = [
        {'name': 'rf', 'params': {'max_depth': 10, 'min_samples_split': 20}, 'seed': 42},
        {'name': 'gbm', 'params': {'max_depth': 5, 'learning_rate': 0.1, 'subsample': 0.8}, 'seed': 43},
    ]

    if LGBM_AVAILABLE:
        models.append({'name': 'lgbm', 'params': {'max_depth': 8, 'learning_rate': 0.05}, 'seed': 44})

    # Train all models on all folds
    all_results = []

    for model_cfg in models:
        print(f"\n{'='*80}")
        print(f"MODEL: {model_cfg['name'].upper()}")
        print(f"{'='*80}")

        fold_results = []
        valid_fold_count = 0

        for fold_idx, (train_idx, test_idx, fold_status) in enumerate(folds):
            print(f"\n  Fold {fold_idx + 1}/{len(folds)} ({fold_status})...")

            if fold_status != "VALID":
                print(f"    Skipped: {fold_status}")
                continue

            X_train = X.iloc[train_idx].reset_index(drop=True)
            y_train = y.iloc[train_idx].reset_index(drop=True)
            X_test = X.iloc[test_idx].reset_index(drop=True)
            y_test = y.iloc[test_idx].reset_index(drop=True)
            fwd_ret_test = forward_returns.iloc[test_idx].reset_index(drop=True)

            metrics, final_status = train_fold(X_train, y_train, X_test, y_test, fwd_ret_test,
                                             model_cfg['name'], model_cfg['params'], model_cfg['seed'],
                                             fold_status)

            metrics['fold'] = fold_idx + 1
            metrics['fold_status'] = final_status
            fold_results.append(metrics)

            if final_status == "VALID":
                valid_fold_count += 1
                auc_str = f"{metrics['auc']:.4f}" if metrics.get('auc') is not None else "None"
                ret_str = f"{metrics['avg_return_net_pct']:.4f}%" if metrics.get('avg_return_net_pct') is not None else "None"
                print(f"    AUC: {auc_str}, Net ret: {ret_str}")
            else:
                print(f"    Invalid: {metrics.get('error', 'unknown')}")

        if valid_fold_count == 0:
            print("\n  ⚠️  NO VALID FOLDS")
            continue

        # Average across VALID folds only
        valid_results = [r for r in fold_results if r.get('fold_status') == 'VALID']

        avg_metrics = {}
        for key in valid_results[0].keys():
            if key in ['fold', 'model_type', 'fold_status', 'error']:
                continue
            values = [r[key] for r in valid_results if r.get(key) is not None]
            avg_metrics[key] = np.mean(values) if values else None

        avg_metrics['model_type'] = model_cfg['name']
        avg_metrics['n_folds'] = len(folds)
        avg_metrics['n_valid_folds'] = valid_fold_count

        all_results.append({
            'model': model_cfg['name'],
            'fold_results': fold_results,
            'avg_metrics': avg_metrics
        })

        auc_avg = avg_metrics.get('auc')
        ret_avg = avg_metrics.get('avg_return_net_pct')
        auc_str = f"{auc_avg:.4f}" if auc_avg is not None else "None"
        ret_str = f"{ret_avg:.4f}%" if ret_avg is not None else "None"
        print(f"\n  Average ({valid_fold_count} valid folds): AUC={auc_str}, Net ret={ret_str}")

    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save detailed CSV
    rows = []
    for result in all_results:
        for fold_res in result['fold_results']:
            rows.append({**fold_res, 'model': result['model']})

    results_df = pd.DataFrame(rows)
    csv_path = Path(output_dir) / f"walk_forward_results_{timestamp}.csv"
    csv_path.parent.mkdir(exist_ok=True, parents=True)
    results_df.to_csv(csv_path, index=False)

    # Save summary JSON
    summary = {
        'timestamp': timestamp,
        'dataset': dataset_path,
        'n_folds': n_folds,
        'embargo_bars': embargo_bars,
        'total_samples': len(X),
        'baselines': baselines,
        'models': {r['model']: r['avg_metrics'] for r in all_results}
    }

    json_path = Path(output_dir) / f"walk_forward_summary_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"\nBaselines (avg return %):")
    for name, val in baselines.items():
        print(f"  {name:25s}: {val:7.4f}%")

    print(f"\nModels (avg across valid folds):")
    for result in all_results:
        avg = result['avg_metrics']
        n_valid = avg.get('n_valid_folds', 0)
        print(f"\n  {result['model'].upper()} ({n_valid} valid folds):")
        print(f"    AUC:        {avg.get('auc', None) or 'None'}")
        print(f"    Accuracy:   {avg.get('accuracy', None) or 'None'}")
        print(f"    F1:         {avg.get('f1', None) or 'None'}")
        print(f"    Net return: {avg.get('avg_return_net_pct', None) or 'None'}%")
        print(f"    Sharpe:     {avg.get('sharpe_proxy', None) or 'None'}")

    # Determine status (check for validation bugs first)
    has_nan_bug = any(
        any(
            r.get('fold_status') not in ['VALID', 'INVALID_TOO_SMALL', 'INVALID_PAST_END',
                                         'INVALID_EMPTY', 'INVALID_ONE_CLASS',
                                         'INVALID_NAN_LABELS', 'INVALID_CONSTANT_RETURNS']
            for r in result['fold_results']
        )
        for result in all_results
    )

    if has_nan_bug:
        status = "VALIDATION_BUG_REMAINING"
        best_model = "N/A"
        best_auc = None
        best_net_ret = None
    else:
        # Filter results with valid metrics
        valid_results = [r for r in all_results if r['avg_metrics'].get('auc') is not None]

        if not valid_results:
            status = "VALIDATION_BUG_REMAINING"
            best_model = "N/A"
            best_auc = None
            best_net_ret = None
        else:
            best_auc = max(r['avg_metrics']['auc'] for r in valid_results)
            best_net_ret = max(r['avg_metrics'].get('avg_return_net_pct', -999) for r in valid_results)
            best_model = max(valid_results, key=lambda r: r['avg_metrics']['auc'])['model']

            if best_auc > 0.53 and best_net_ret > 0.01:
                status = "RESEARCH_EXPERIMENT_PASS"
            elif best_auc > 0.52 and best_net_ret > 0.0:
                status = "RESEARCH_EXPERIMENT_WEAK"
            else:
                status = "RESEARCH_EXPERIMENT_FAIL"

    print(f"\n{'='*80}")
    print(f"STATUS: {status}")
    print(f"{'='*80}")
    print(f"Best model: {best_model.upper() if best_model != 'N/A' else 'N/A'}")
    print(f"Best AUC: {best_auc if best_auc is not None else 'N/A'}")
    print(f"Best net return: {best_net_ret if best_net_ret is not None else 'N/A'}%")
    print(f"\nResults: {csv_path}")
    print(f"Summary: {json_path}")

    return summary, status


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Walk-forward validation')
    parser.add_argument('--dataset', default='data/hydra_m5_dataset.parquet')
    parser.add_argument('--folds', type=int, default=5)
    parser.add_argument('--embargo', type=int, default=60, help='Embargo bars between train/test')
    parser.add_argument('--output', default='runs')

    args = parser.parse_args()

    # Validate dataset shape
    df_test = pd.read_parquet(args.dataset)
    if df_test.shape[1] != 3001:
        print(f"❌ SHAPE VIOLATION: {df_test.shape[1]} cols (expected 3001)")
        sys.exit(1)

    summary, status = main(args.dataset, args.folds, args.embargo, args.output)
