"""Train BOI M15 MTF model.

Usage:
    python scripts/train_boi_m15_mtf.py [--config CONFIG_PATH] [--quick]

Flags:
    --quick: Train on small sample for testing
"""
import sys
import yaml
import json
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from boi.data import load_all_timeframes, split_by_date
from boi.features import build_all_features
from boi.labels import create_triple_barrier_labels, CostModel
from research_core.data_contracts import validate_features


def compute_class_weights(labels: pd.Series) -> dict:
    """Compute class weights for imbalanced dataset."""
    counts = labels.value_counts()
    total = len(labels)
    weights = {cls: total / (len(counts) * count) for cls, count in counts.items()}
    return weights


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/models/boi_m15_mtf.yaml')
    parser.add_argument('--quick', action='store_true', help='Train on small sample')
    args = parser.parse_args()

    # Load config
    print("=" * 60)
    print("BOI M15 MTF Training")
    print("=" * 60)
    print(f"Config: {args.config}")
    print()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    # Load data
    data = load_all_timeframes(config)
    m15 = data['m15']
    m5 = data.get('m5')
    h1 = data.get('h1')
    h4 = data.get('h4')
    d1 = data.get('d1')

    # Build features
    print("\nBuilding features...")
    features = build_all_features(m15, m5, h1, h4, d1)
    print(f"  Total features: {features.shape[1]}")
    print(f"  Feature columns: {list(features.columns)[:10]}...")

    # Validate features
    print("\nValidating features...")
    try:
        validate_features(features, allow_label=False, check_bfill=False)
        print("  ✓ Feature validation passed")
    except Exception as e:
        print(f"  ✗ Feature validation failed: {e}")
        return

    # Compute ATR for labels
    print("\nComputing ATR for labels...")
    tr = pd.concat([
        m15['high'] - m15['low'],
        (m15['high'] - m15['close'].shift(1)).abs(),
        (m15['low'] - m15['close'].shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(config['label']['atr_period']).mean()

    # Create labels
    print("\nCreating labels...")
    label_config = config['label']
    cost_model = CostModel(**label_config['cost_model'])

    labels, label_metadata = create_triple_barrier_labels(
        m15,
        atr,
        horizon_bars=label_config['default_horizon'],
        stop_atr_mult=label_config['stop_atr_mult'],
        target_atr_mult=label_config['target_atr_mult'],
        entry_lag=label_config['entry_lag'],
        cost_model=cost_model,
        ambiguity_handling=label_config['ambiguity_handling'],
    )

    print(f"  Label distribution:")
    for cls, name in enumerate(['short', 'skip', 'long']):
        count = (labels == cls).sum()
        pct = count / len(labels) * 100
        print(f"    {name} ({cls}): {count:,} ({pct:.1f}%)")

    # Split data
    print("\nSplitting data...")
    splits = config['splits']
    train_features, val_features, oos_features = split_by_date(
        features,
        splits['train_start'], splits['train_end'],
        splits['val_start'], splits['val_end'],
        splits['oos_start'], splits['oos_end'],
    )
    train_labels = labels.reindex(train_features.index)
    val_labels = labels.reindex(val_features.index)
    oos_labels = labels.reindex(oos_features.index)

    print(f"  Train: {len(train_features):,} bars")
    print(f"  Val: {len(val_features):,} bars")
    print(f"  OOS: {len(oos_features):,} bars")

    # Quick mode: subsample
    if args.quick:
        print("\n⚠️  QUICK MODE: Training on 10k sample")
        sample_size = min(10000, len(train_features))
        idx = np.random.choice(len(train_features), sample_size, replace=False)
        train_features = train_features.iloc[idx]
        train_labels = train_labels.iloc[idx]

    # Drop NaN
    train_mask = train_features.notna().all(axis=1) & train_labels.notna()
    val_mask = val_features.notna().all(axis=1) & val_labels.notna()

    X_train = train_features[train_mask]
    y_train = train_labels[train_mask]
    X_val = val_features[val_mask]
    y_val = val_labels[val_mask]

    print(f"  After NaN drop:")
    print(f"    Train: {len(X_train):,} samples")
    print(f"    Val: {len(X_val):,} samples")

    # Compute class weights
    class_weights = compute_class_weights(y_train)
    print(f"\n  Class weights: {class_weights}")

    # Sample weights
    sample_weights = y_train.map(class_weights).values

    # Train model
    print("\nTraining XGBoost model...")
    model_params = config['model']['params'].copy()
    model_params['num_class'] = 3

    dtrain = xgb.DMatrix(X_train, label=y_train, weight=sample_weights)
    dval = xgb.DMatrix(X_val, label=y_val)

    evals = [(dtrain, 'train'), (dval, 'val')]
    early_stopping = config['model'].get('early_stopping_rounds', 30)

    model = xgb.train(
        model_params,
        dtrain,
        num_boost_round=config['model']['params']['n_estimators'],
        evals=evals,
        early_stopping_rounds=early_stopping,
        verbose_eval=20,
    )

    print(f"  Best iteration: {model.best_iteration}")
    print(f"  Best score: {model.best_score:.4f}")

    # Evaluate
    print("\nEvaluating...")
    train_pred = model.predict(dtrain)
    val_pred = model.predict(dval)

    train_pred_class = train_pred.argmax(axis=1)
    val_pred_class = val_pred.argmax(axis=1)

    train_acc = (train_pred_class == y_train.values).mean()
    val_acc = (val_pred_class == y_val.values).mean()

    print(f"  Train accuracy: {train_acc:.3f}")
    print(f"  Val accuracy: {val_acc:.3f}")

    # Feature importance
    importance = model.get_score(importance_type='gain')
    importance_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:15]
    print(f"\n  Top 15 features:")
    for feat, gain in importance_sorted:
        print(f"    {feat}: {gain:.1f}")

    # Save model
    output_dir = Path(config['output']['base_dir'])
    output_dir.mkdir(exist_ok=True, parents=True)

    model_path = output_dir / config['output']['model_file']
    model.save_model(str(model_path))
    print(f"\n✓ Model saved to {model_path}")

    # Save metadata
    metadata = {
        'model_name': config['model_name'],
        'version': config['version'],
        'instrument': config['instrument'],
        'decision_timeframe': config['decision_timeframe'],
        'feature_count': len(X_train.columns),
        'training_period': f"{splits['train_start']} to {splits['train_end']}",
        'validation_period': f"{splits['val_start']} to {splits['val_end']}",
        'test_period': f"{splits['oos_start']} to {splits['oos_end']}",
        'label_config': label_config,
        'execution_config': config['execution'],
        'train_samples': len(X_train),
        'val_samples': len(X_val),
        'label_distribution': {
            'short': int((y_train == 0).sum()),
            'skip': int((y_train == 1).sum()),
            'long': int((y_train == 2).sum()),
        },
        'train_accuracy': float(train_acc),
        'val_accuracy': float(val_acc),
        'best_iteration': int(model.best_iteration),
        'best_score': float(model.best_score),
        'class_weights': {int(k): float(v) for k, v in class_weights.items()},
        'contaminated': False,
        'selected_by': 'train_script',
        'trained_at': datetime.now().isoformat(),
        'quick_mode': args.quick,
    }

    metadata_path = output_dir / config['output']['metadata_file']
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ Metadata saved to {metadata_path}")

    # Save feature list
    features_list = {
        'feature_names': list(X_train.columns),
        'feature_count': len(X_train.columns),
        'feature_importance': {feat: float(gain) for feat, gain in importance_sorted},
    }
    features_path = output_dir / config['output']['features_file']
    with open(features_path, 'w') as f:
        json.dump(features_list, f, indent=2)
    print(f"✓ Features saved to {features_path}")

    print("\n" + "=" * 60)
    print("Training complete")
    print("=" * 60)
    print(f"Next: Run validation with scripts/validate_boi_m15_mtf.py")


if __name__ == "__main__":
    main()
