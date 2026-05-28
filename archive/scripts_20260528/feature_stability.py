#!/usr/bin/env python3
"""Feature stability monitoring - track IC decay over time.

Computes rolling IC for each feature to detect distribution shifts.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import spearmanr
import json
from datetime import datetime

# Config
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
ROLLING_WINDOW = 100  # Rolling IC window
IC_DECAY_THRESHOLD = -0.05  # Flag if IC drops by >0.05


def compute_rolling_ic(feature_values, target_values, window=100):
    """Compute rolling IC (Spearman correlation).

    Args:
        feature_values: Feature time series
        target_values: Target time series
        window: Rolling window size

    Returns:
        List of (index, IC, p-value) tuples
    """
    rolling_ics = []

    for i in range(window, len(feature_values)):
        window_feature = feature_values[i-window:i]
        window_target = target_values[i-window:i]

        # Remove NaNs
        valid = ~(pd.isna(window_feature) | pd.isna(window_target))
        if valid.sum() < 10:
            rolling_ics.append((i, np.nan, 1.0))
            continue

        ic, pval = spearmanr(window_feature[valid], window_target[valid])
        rolling_ics.append((i, ic, pval))

    return rolling_ics


def detect_ic_decay(rolling_ics, threshold=-0.05):
    """Detect if IC has decayed significantly.

    Args:
        rolling_ics: List of (index, IC, p-value)
        threshold: Decay threshold (negative number)

    Returns:
        (has_decay, decay_amount, decay_from_index)
    """
    if len(rolling_ics) < 2:
        return False, 0.0, None

    # Get first and last IC (ignoring NaNs)
    valid_ics = [(idx, ic) for idx, ic, _ in rolling_ics if not np.isnan(ic)]

    if len(valid_ics) < 2:
        return False, 0.0, None

    first_ic = valid_ics[0][1]
    last_ic = valid_ics[-1][1]

    decay = last_ic - first_ic

    has_decay = decay < threshold

    return has_decay, decay, valid_ics[0][0]


def main():
    """Analyze feature stability."""
    print("=" * 60)
    print("Feature Stability Monitoring")
    print("=" * 60)

    # Load train data
    print("\nLoading train set...")
    train = pd.read_parquet(DATA_DIR / "train_v1.parquet")

    print(f"Samples: {len(train)}")
    print(f"Rolling window: {ROLLING_WINDOW}")

    # Get feature columns
    exclude_cols = ['timestamp', 'close', 'high', 'low', 'open', 'volume',
                    'target_return_1', 'target_return_5', 'target_return_10']
    feature_cols = [col for col in train.columns if col not in exclude_cols]

    print(f"Features: {len(feature_cols)}")

    # Compute rolling IC for each feature
    print("\nComputing rolling IC (this may take 2-3 minutes)...")

    feature_stability = {}
    unstable_features = []

    for i, feature in enumerate(feature_cols):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{len(feature_cols)}")

        feature_values = train[feature].values
        target_values = train['target_return_1'].values

        # Compute rolling IC
        rolling_ics = compute_rolling_ic(feature_values, target_values, window=ROLLING_WINDOW)

        # Detect decay
        has_decay, decay_amount, decay_from_idx = detect_ic_decay(rolling_ics, threshold=IC_DECAY_THRESHOLD)

        # Store
        feature_stability[feature] = {
            "rolling_ics": [(idx, ic, pval) for idx, ic, pval in rolling_ics],
            "has_decay": has_decay,
            "decay_amount": decay_amount,
            "decay_from_index": decay_from_idx,
            "first_ic": rolling_ics[0][1] if rolling_ics and not np.isnan(rolling_ics[0][1]) else None,
            "last_ic": rolling_ics[-1][1] if rolling_ics and not np.isnan(rolling_ics[-1][1]) else None,
        }

        if has_decay:
            unstable_features.append({
                "feature": feature,
                "decay": decay_amount,
                "first_ic": feature_stability[feature]["first_ic"],
                "last_ic": feature_stability[feature]["last_ic"],
            })

    print(f"  Completed {len(feature_cols)} features")

    # Summary
    print("\n" + "=" * 60)
    print("STABILITY SUMMARY")
    print("=" * 60)

    print(f"\nTotal features analyzed: {len(feature_cols)}")
    print(f"Unstable features (IC decay > {IC_DECAY_THRESHOLD}): {len(unstable_features)}")

    if unstable_features:
        print(f"\nTop 10 most unstable features:")
        unstable_sorted = sorted(unstable_features, key=lambda x: x['decay'])[:10]

        for uf in unstable_sorted:
            print(f"  {uf['feature']}: IC {uf['first_ic']:.3f} → {uf['last_ic']:.3f} (decay: {uf['decay']:.3f})")

    # Stats
    all_decays = [fs['decay_amount'] for fs in feature_stability.values() if fs['decay_amount'] is not None]

    if all_decays:
        print(f"\nDecay statistics:")
        print(f"  Mean decay: {np.mean(all_decays):.4f}")
        print(f"  Median decay: {np.median(all_decays):.4f}")
        print(f"  Std decay: {np.std(all_decays):.4f}")
        print(f"  Min decay: {np.min(all_decays):.4f}")
        print(f"  Max decay: {np.max(all_decays):.4f}")

    # Save
    results = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "dataset": "dataset_v1",
        "rolling_window": ROLLING_WINDOW,
        "ic_decay_threshold": IC_DECAY_THRESHOLD,
        "total_features": len(feature_cols),
        "unstable_features_count": len(unstable_features),
        "unstable_features": unstable_features,
        "decay_statistics": {
            "mean": float(np.mean(all_decays)) if all_decays else None,
            "median": float(np.median(all_decays)) if all_decays else None,
            "std": float(np.std(all_decays)) if all_decays else None,
            "min": float(np.min(all_decays)) if all_decays else None,
            "max": float(np.max(all_decays)) if all_decays else None,
        }
    }

    results_path = REPO_ROOT / "reports" / "feature_stability_v1.json"
    results_path.write_text(json.dumps(results, indent=2))

    print(f"\n✓ Results saved: {results_path}")

    # Alert if many unstable
    if len(unstable_features) > len(feature_cols) * 0.2:
        print(f"\n⚠ WARNING: {len(unstable_features)/len(feature_cols):.1%} of features are unstable")
        print(f"  Consider retraining or removing unstable features")
    else:
        print(f"\n✓ Feature stability looks good ({len(unstable_features)/len(feature_cols):.1%} unstable)")

    return 0


if __name__ == "__main__":
    exit(main())
