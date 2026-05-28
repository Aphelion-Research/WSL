#!/usr/bin/env python3
"""Train on all 6 label horizons overnight."""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import roc_auc_score, accuracy_score
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_3k.parquet")
OUTPUT_DIR = Path("runs/multilabel")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LABELS = ['label_6b', 'label_12b', 'label_24b', 'label_72b', 'label_144b', 'label_288b']


def train_all_horizons():
    """Train LightGBM on all label horizons."""
    import lightgbm as lgb

    print("Loading dataset...")
    df = pd.read_parquet(DATASET)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    all_results = []

    for label in LABELS:
        if label not in df.columns:
            continue

        print(f"\n{'='*60}")
        print(f"TRAINING ON: {label}")
        print(f"{'='*60}")

        df_label = df[df[label].notna()].copy()
        y = df_label[label].astype(int).values
        X = df_label[feature_cols].values

        print(f"Dataset: {len(X)} rows")

        # 5-fold walk-forward
        n = len(X)
        fold_size = n // 5
        embargo = 60

        for fold in range(1, 6):
            test_start = (fold - 1) * fold_size
            test_end = test_start + fold_size if fold < 5 else n
            train_end = test_start - embargo

            if train_end < fold_size:
                continue

            train_idx = np.arange(0, train_end)
            test_idx = np.arange(test_start, test_end)

            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            scaler = RobustScaler()
            X_train_sc = scaler.fit_transform(X_train)
            X_test_sc = scaler.transform(X_test)

            model = lgb.LGBMClassifier(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=10,
                n_jobs=-1,
                verbosity=-1,
                random_state=42
            )
            model.fit(X_train_sc, y_train)
            y_pred = model.predict_proba(X_test_sc)[:, 1]

            auc = roc_auc_score(y_test, y_pred)
            acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))

            all_results.append({
                'label': label,
                'fold': fold,
                'auc': auc,
                'acc': acc,
                'train_size': len(train_idx),
                'test_size': len(test_idx)
            })

            print(f"  Fold {fold}: AUC={auc:.4f} Acc={acc:.4f}")

    # Save
    results_df = pd.DataFrame(all_results)
    output_file = OUTPUT_DIR / f"multilabel_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
    results_df.to_csv(output_file, index=False)

    print(f"\n{'='*60}")
    print("SUMMARY BY LABEL")
    print(f"{'='*60}")
    print(results_df.groupby('label').agg({'auc': 'mean', 'acc': 'mean'}).round(4))
    print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    train_all_horizons()
