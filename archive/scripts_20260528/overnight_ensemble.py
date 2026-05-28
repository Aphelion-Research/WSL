#!/usr/bin/env python3
"""Build ensemble models overnight."""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import roc_auc_score, accuracy_score
import warnings
warnings.filterwarnings('ignore')

DATASET = Path("data/hydra_xauusd_m5_selected.parquet")
OUTPUT = Path("runs/ensemble_results.csv")

LABEL = 'label_12b'


def train_ensemble():
    """Voting, stacking, blending."""
    import lightgbm as lgb
    import xgboost as xgb
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier, StackingClassifier
    from sklearn.linear_model import LogisticRegression

    print("Loading dataset...")
    df = pd.read_parquet(DATASET)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    df = df[df[LABEL].notna()].copy()
    y = df[LABEL].astype(int).values
    X = df[feature_cols].values

    print(f"Dataset: {len(X)} rows × {len(feature_cols)} features")

    # Single train/test split
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    scaler = RobustScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)

    results = []

    # Base models
    base_models = {
        'lgb': lgb.LGBMClassifier(n_estimators=300, n_jobs=-1, verbosity=-1, random_state=42),
        'xgb': xgb.XGBClassifier(n_estimators=300, n_jobs=-1, verbosity=0, random_state=42),
        'rf': RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=42),
    }

    # Train base models
    print("\nTraining base models...")
    predictions = {}
    for name, model in base_models.items():
        print(f"  {name}...")
        model.fit(X_train, y_train)
        y_pred = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, y_pred)
        acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
        predictions[name] = y_pred
        results.append({'method': name, 'auc': auc, 'acc': acc})
        print(f"    AUC: {auc:.4f}")

    # Voting ensemble
    print("\nVoting ensemble...")
    voting = VotingClassifier(
        estimators=[(n, m) for n, m in base_models.items()],
        voting='soft',
        n_jobs=-1
    )
    voting.fit(X_train, y_train)
    y_pred = voting.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred)
    acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
    results.append({'method': 'voting', 'auc': auc, 'acc': acc})
    print(f"  AUC: {auc:.4f}")

    # Stacking
    print("\nStacking ensemble...")
    stacking = StackingClassifier(
        estimators=[(n, m) for n, m in base_models.items()],
        final_estimator=LogisticRegression(max_iter=1000),
        n_jobs=-1
    )
    stacking.fit(X_train, y_train)
    y_pred = stacking.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred)
    acc = accuracy_score(y_test, (y_pred >= 0.5).astype(int))
    results.append({'method': 'stacking', 'auc': auc, 'acc': acc})
    print(f"  AUC: {auc:.4f}")

    # Simple averaging
    print("\nSimple averaging...")
    avg_pred = np.mean([predictions[n] for n in predictions], axis=0)
    auc = roc_auc_score(y_test, avg_pred)
    acc = accuracy_score(y_test, (avg_pred >= 0.5).astype(int))
    results.append({'method': 'averaging', 'auc': auc, 'acc': acc})
    print(f"  AUC: {auc:.4f}")

    # Weighted averaging (by individual AUC)
    print("\nWeighted averaging...")
    weights = []
    for name in predictions.keys():
        w = [r['auc'] for r in results if r['method'] == name][0]
        weights.append(w)
    weights = np.array(weights) / sum(weights)

    weighted_pred = np.average([predictions[n] for n in predictions], axis=0, weights=weights)
    auc = roc_auc_score(y_test, weighted_pred)
    acc = accuracy_score(y_test, (weighted_pred >= 0.5).astype(int))
    results.append({'method': 'weighted_avg', 'auc': auc, 'acc': acc})
    print(f"  AUC: {auc:.4f}")

    # Save
    results_df = pd.DataFrame(results).sort_values('auc', ascending=False)
    results_df.to_csv(OUTPUT, index=False)

    print(f"\n{'='*60}")
    print("ENSEMBLE RESULTS")
    print(f"{'='*60}")
    print(results_df.to_string(index=False))
    print(f"\nSaved: {OUTPUT}")


if __name__ == "__main__":
    train_ensemble()
