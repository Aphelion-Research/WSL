#!/usr/bin/env python3
"""Feature selection overnight - find top 500 features."""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
import warnings
warnings.filterwarnings('ignore')

INPUT = Path("data/hydra_xauusd_m5_3k.parquet")
OUTPUT = Path("data/hydra_xauusd_m5_selected.parquet")
FEATURES_CSV = Path("runs/selected_features.csv")

LABEL = 'label_12b'
TOP_N = 500


def select_features():
    """Select top N features by importance."""
    print("Loading dataset...")
    df = pd.read_parquet(INPUT)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    df = df[df[LABEL].notna()].copy()
    y = df[LABEL].astype(int).values
    X = df[feature_cols]

    print(f"Dataset: {len(X)} rows × {len(feature_cols)} features")

    # Method 1: Random Forest importance
    print("\n[1/3] Random Forest importance...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, n_jobs=-1, random_state=42)
    rf.fit(X.values[::10], y[::10])  # Subsample for speed

    rf_importance = pd.DataFrame({
        'feature': feature_cols,
        'rf_importance': rf.feature_importances_
    }).sort_values('rf_importance', ascending=False)

    # Method 2: Mutual information
    print("[2/3] Mutual information...")
    mi_scores = mutual_info_classif(X.values[::10], y[::10], random_state=42, n_jobs=-1)
    mi_importance = pd.DataFrame({
        'feature': feature_cols,
        'mi_score': mi_scores
    }).sort_values('mi_score', ascending=False)

    # Method 3: Variance
    print("[3/3] Variance thresholding...")
    variances = X.var()
    var_importance = pd.DataFrame({
        'feature': feature_cols,
        'variance': variances
    }).sort_values('variance', ascending=False)

    # Combine scores
    print("\nCombining selection methods...")
    combined = rf_importance.merge(mi_importance, on='feature').merge(var_importance, on='feature')

    # Rank-based combination
    combined['rf_rank'] = combined['rf_importance'].rank(ascending=False)
    combined['mi_rank'] = combined['mi_score'].rank(ascending=False)
    combined['var_rank'] = combined['variance'].rank(ascending=False)
    combined['avg_rank'] = (combined['rf_rank'] + combined['mi_rank'] + combined['var_rank']) / 3
    combined = combined.sort_values('avg_rank')

    # Select top N
    selected_features = combined.head(TOP_N)['feature'].tolist()

    print(f"\nSelected {len(selected_features)} features")
    print(f"Top 10:")
    for i, row in combined.head(10).iterrows():
        print(f"  {row['feature']}: RF={row['rf_importance']:.4f} MI={row['mi_score']:.4f}")

    # Save selection results
    combined.to_csv(FEATURES_CSV, index=False)
    print(f"\nFeature importance saved: {FEATURES_CSV}")

    # Create reduced dataset
    print(f"\nCreating reduced dataset with {len(selected_features)} features...")
    reduced = df[selected_features + label_cols]
    reduced.to_parquet(OUTPUT)

    print(f"Reduced dataset saved: {OUTPUT}")
    print(f"Size: {len(reduced)} rows × {len(selected_features)} features")


if __name__ == "__main__":
    select_features()
