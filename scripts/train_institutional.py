"""
Train XGBoost on institutional-grade dataset.
Walk-forward validation: train on past, test on future.
Compare to old 1347-feature approach.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_auc_score, accuracy_score, log_loss
import xgboost as xgb
import json
from datetime import datetime

DATA = Path("data/institutional_xauusd.parquet")
OUTPUT_DIR = Path("output_institutional")
OUTPUT_DIR.mkdir(exist_ok=True)


def walk_forward_split(df, train_pct=0.6, val_pct=0.2):
    """Strict temporal split: train | val | OOS."""
    n = len(df)
    train_end = int(n * train_pct)
    val_end = int(n * (train_pct + val_pct))
    return df.iloc[:train_end], df.iloc[train_end:val_end], df.iloc[val_end:]


def train_single_horizon(df, label_col, feature_cols):
    """Train XGBoost for one label horizon."""
    valid = df.dropna(subset=[label_col])
    train, val, oos = walk_forward_split(valid)

    X_train = train[feature_cols].values
    y_train = train[label_col].values
    X_val = val[feature_cols].values
    y_val = val[label_col].values
    X_oos = oos[feature_cols].values
    y_oos = oos[label_col].values

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=feature_cols)
    dval = xgb.DMatrix(X_val, label=y_val, feature_names=feature_cols)
    doos = xgb.DMatrix(X_oos, label=y_oos, feature_names=feature_cols)

    params = {
        'objective': 'binary:logistic',
        'eval_metric': 'auc',
        'tree_method': 'hist',
        'max_depth': 4,
        'learning_rate': 0.01,
        'subsample': 0.7,
        'colsample_bytree': 0.7,
        'min_child_weight': 100,
        'reg_alpha': 1.0,
        'reg_lambda': 5.0,
        'seed': 42,
    }

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=500,
        evals=[(dtrain, 'train'), (dval, 'val')],
        early_stopping_rounds=30,
        verbose_eval=50,
    )

    # Evaluate
    val_proba = model.predict(dval)
    oos_proba = model.predict(doos)

    val_auc = roc_auc_score(y_val, val_proba)
    oos_auc = roc_auc_score(y_oos, oos_proba)
    oos_acc = accuracy_score(y_oos, (oos_proba > 0.5).astype(int))
    oos_logloss = log_loss(y_oos, oos_proba)

    # Feature importance
    importance = model.get_score(importance_type='total_gain')
    top_features = sorted(importance.items(), key=lambda x: -x[1])[:15]

    # Confidence gating
    gating = {}
    for threshold in [0.50, 0.52, 0.55, 0.58, 0.60]:
        mask = (oos_proba > threshold) | (oos_proba < (1 - threshold))
        if mask.sum() > 100:
            gated_acc = accuracy_score(y_oos[mask], (oos_proba[mask] > 0.5).astype(int))
            gated_auc = roc_auc_score(y_oos[mask], oos_proba[mask])
            gating[str(threshold)] = {
                'n_trades': int(mask.sum()),
                'trade_rate': float(mask.sum() / len(y_oos)),
                'accuracy': float(gated_acc),
                'auc_roc': float(gated_auc),
            }

    results = {
        'label': label_col,
        'train_samples': len(train),
        'val_samples': len(val),
        'oos_samples': len(oos),
        'train_date_range': f"{train.index.min()} to {train.index.max()}",
        'val_date_range': f"{val.index.min()} to {val.index.max()}",
        'oos_date_range': f"{oos.index.min()} to {oos.index.max()}",
        'best_iteration': model.best_iteration,
        'val_auc': float(val_auc),
        'oos_auc': float(oos_auc),
        'oos_accuracy': float(oos_acc),
        'oos_logloss': float(oos_logloss),
        'top_features': top_features,
        'confidence_gating': gating,
    }

    return results, model


def main():
    print("Loading institutional dataset...")
    df = pd.read_parquet(DATA)
    print(f"  {len(df)} rows × {len(df.columns)} columns")

    feature_cols = [c for c in df.columns
                    if not c.startswith('label_') and not c.startswith('ret_') or
                    (c.startswith('ret_') and not c.endswith('_fwd'))]
    # Remove forward return columns
    feature_cols = [c for c in feature_cols if '_fwd' not in c]
    # Only keep actual feature columns (not labels)
    label_cols = [c for c in df.columns if c.startswith('label_')]
    fwd_cols = [c for c in df.columns if c.endswith('_fwd')]
    feature_cols = [c for c in df.columns if c not in label_cols and c not in fwd_cols]

    print(f"  Features: {len(feature_cols)}")
    print(f"  Labels: {label_cols}")

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'dataset': str(DATA),
        'n_samples': len(df),
        'n_features': len(feature_cols),
        'feature_names': feature_cols,
        'horizons': {},
    }

    for label in label_cols:
        print(f"\n{'='*60}")
        print(f"Training: {label}")
        print(f"{'='*60}")

        results, model = train_single_horizon(df, label, feature_cols)
        all_results['horizons'][label] = results

        print(f"\n  Val AUC:  {results['val_auc']:.4f}")
        print(f"  OOS AUC:  {results['oos_auc']:.4f}")
        print(f"  OOS Acc:  {results['oos_accuracy']:.4f}")
        print(f"  Best iter: {results['best_iteration']}")
        print(f"\n  Top 5 features:")
        for fname, fval in results['top_features'][:5]:
            print(f"    {fname}: {fval:.1f}")
        print(f"\n  Confidence gating:")
        for thresh, g in results['confidence_gating'].items():
            print(f"    >{thresh}: {g['n_trades']} trades ({g['trade_rate']:.1%}), "
                  f"acc={g['accuracy']:.4f}, auc={g['auc_roc']:.4f}")

        model.save_model(str(OUTPUT_DIR / f"model_{label}.json"))

    # Save results
    results_file = OUTPUT_DIR / "results_institutional.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    # Print comparison summary
    print(f"\n\n{'='*60}")
    print("COMPARISON: Institutional vs Old Hydra")
    print(f"{'='*60}")
    print(f"{'Metric':<25} {'Old (1347 feat)':<20} {'New (48 feat)':<20}")
    print(f"{'-'*65}")

    old_aucs = {
        'scalp (1hr)': 0.541,
        'day (6hr)': 0.541,
        'swing (24hr)': 0.543,
        'meta': 0.523,
    }

    for label, res in all_results['horizons'].items():
        print(f"  {label:<23} {'—':<20} {res['oos_auc']:.4f}")
    print(f"\n  Old hydra_scalp (1hr): 0.5408")
    print(f"  Old hydra_day (6hr):   0.5413")
    print(f"  Old hydra_swing (24h): 0.5432")
    print(f"  Old meta ensemble:     0.5229")

    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
