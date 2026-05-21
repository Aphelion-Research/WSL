#!/usr/bin/env python3
"""Train multiple model architectures overnight."""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import roc_auc_score, accuracy_score
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_3k.parquet")
OUTPUT_DIR = Path("runs/overnight_models")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LABEL = 'label_12b'
FOLDS = 5
EMBARGO = 60


def train_all_models():
    """Train LightGBM, XGBoost, CatBoost, RandomForest, ExtraTrees."""
    print("Loading dataset...")
    df = pd.read_parquet(DATASET)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    df = df[df[LABEL].notna()].copy()
    y = df[LABEL].astype(int).values
    X = df[feature_cols].values

    print(f"Dataset: {len(X)} rows × {len(feature_cols)} features")

    # Walk-forward splits
    n = len(X)
    fold_size = n // FOLDS

    results = []

    for fold in range(1, FOLDS + 1):
        test_start = (fold - 1) * fold_size
        test_end = test_start + fold_size if fold < FOLDS else n
        train_end = test_start - EMBARGO

        if train_end < fold_size:
            continue

        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)

        X_train, X_test = X[train_idx], X[test_idx]
        y_train, y_test = y[train_idx], y[test_idx]

        print(f"\n{'='*60}")
        print(f"FOLD {fold}/{FOLDS}")
        print(f"{'='*60}")
        print(f"Train: {len(train_idx):,} | Test: {len(test_idx):,}")

        scaler = RobustScaler()
        X_train_sc = scaler.fit_transform(X_train)
        X_test_sc = scaler.transform(X_test)

        # LightGBM
        try:
            import lightgbm as lgb
            print("\n[LightGBM]")
            model = lgb.LGBMClassifier(
                n_estimators=500,
                learning_rate=0.03,
                max_depth=12,
                num_leaves=64,
                n_jobs=-1,
                verbosity=-1,
                random_state=42
            )
            model.fit(X_train_sc, y_train)
            y_pred = model.predict_proba(X_test_sc)[:, 1]
            auc = roc_auc_score(y_test, y_pred)
            acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
            print(f"  AUC: {auc:.4f} | Acc: {acc:.4f}")
            results.append({'fold': fold, 'model': 'LightGBM', 'auc': auc, 'acc': acc})
        except Exception as e:
            print(f"  Failed: {e}")

        # XGBoost
        try:
            import xgboost as xgb
            print("\n[XGBoost]")
            model = xgb.XGBClassifier(
                n_estimators=500,
                learning_rate=0.03,
                max_depth=12,
                tree_method='hist',
                n_jobs=-1,
                verbosity=0,
                random_state=42
            )
            model.fit(X_train_sc, y_train)
            y_pred = model.predict_proba(X_test_sc)[:, 1]
            auc = roc_auc_score(y_test, y_pred)
            acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
            print(f"  AUC: {auc:.4f} | Acc: {acc:.4f}")
            results.append({'fold': fold, 'model': 'XGBoost', 'auc': auc, 'acc': acc})
        except Exception as e:
            print(f"  Failed: {e}")

        # CatBoost
        try:
            from catboost import CatBoostClassifier
            print("\n[CatBoost]")
            model = CatBoostClassifier(
                iterations=500,
                learning_rate=0.03,
                depth=12,
                verbose=0,
                random_state=42
            )
            model.fit(X_train_sc, y_train)
            y_pred = model.predict_proba(X_test_sc)[:, 1]
            auc = roc_auc_score(y_test, y_pred)
            acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
            print(f"  AUC: {auc:.4f} | Acc: {acc:.4f}")
            results.append({'fold': fold, 'model': 'CatBoost', 'auc': auc, 'acc': acc})
        except Exception as e:
            print(f"  Failed: {e}")

        # RandomForest
        try:
            from sklearn.ensemble import RandomForestClassifier
            print("\n[RandomForest]")
            model = RandomForestClassifier(
                n_estimators=300,
                max_depth=12,
                n_jobs=-1,
                random_state=42
            )
            model.fit(X_train_sc, y_train)
            y_pred = model.predict_proba(X_test_sc)[:, 1]
            auc = roc_auc_score(y_test, y_pred)
            acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
            print(f"  AUC: {auc:.4f} | Acc: {acc:.4f}")
            results.append({'fold': fold, 'model': 'RandomForest', 'auc': auc, 'acc': acc})
        except Exception as e:
            print(f"  Failed: {e}")

        # ExtraTrees
        try:
            from sklearn.ensemble import ExtraTreesClassifier
            print("\n[ExtraTrees]")
            model = ExtraTreesClassifier(
                n_estimators=300,
                max_depth=12,
                n_jobs=-1,
                random_state=42
            )
            model.fit(X_train_sc, y_train)
            y_pred = model.predict_proba(X_test_sc)[:, 1]
            auc = roc_auc_score(y_test, y_pred)
            acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
            print(f"  AUC: {auc:.4f} | Acc: {acc:.4f}")
            results.append({'fold': fold, 'model': 'ExtraTrees', 'auc': auc, 'acc': acc})
        except Exception as e:
            print(f"  Failed: {e}")

    # Save results
    results_df = pd.DataFrame(results)
    output_file = OUTPUT_DIR / f"all_models_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(output_file, index=False)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(results_df.groupby('model').agg({'auc': 'mean', 'acc': 'mean'}).round(4))
    print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    train_all_models()
