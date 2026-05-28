#!/usr/bin/env python3
"""Turbo 3K expansion: C++ kernels + 20-core parallel."""
import pandas as pd
import numpy as np
from pathlib import Path
from joblib import Parallel, delayed
from dominion.features.hydra_kernels import (
    rolling_mean, rolling_std, rolling_min, rolling_max,
    rolling_skew, rolling_kurt, rolling_zscore, ema, rsi, atr
)
import warnings
warnings.filterwarnings('ignore')

INPUT = Path("data/hydra_xauusd_m5_master.parquet")
OUTPUT = Path("data/hydra_xauusd_m5_3k.parquet")
N_JOBS = 8  # Reduced from 20 to avoid OOM on 789k rows


def load_base():
    """Load base feature matrix."""
    df = pd.read_parquet(INPUT)
    print(f"Base: {len(df):,} rows × {len(df.columns)} cols")

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    X = df[feature_cols]
    y = df[label_cols]

    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    X = X[numeric_cols]

    print(f"Numeric features: {len(numeric_cols)}")
    return X, y, df.index


def compute_lags_parallel(col_name, series, lags):
    """Compute lags for one column (parallel worker)."""
    features = {}
    for lag in lags:
        features[f'{col_name}_lag{lag}'] = series.shift(lag).values
    return col_name, features


def add_lag_features(X, n_lags=50):
    """Add lagged features using parallel processing."""
    print(f"\nAdding lags (parallel across {N_JOBS} cores)...")

    variances = X.var()
    top_features = variances.nlargest(15).index.tolist()  # Reduced from 20
    lags = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89]  # Reduced from 12 to 10 lags

    # Parallel lag computation
    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_lags_parallel)(col, X[col], lags)
        for col in top_features
    )

    # Merge results
    lagged = pd.DataFrame(index=X.index)
    for col_name, features in results:
        for feat_name, values in features.items():
            lagged[feat_name] = values

    print(f"  Added {len(lagged.columns)} lag features")
    return lagged


def compute_rolling_parallel(col_name, series, windows):
    """Compute rolling stats for one column using C++ kernels."""
    features = {}
    arr = series.values

    for w in windows:
        # Use C++ kernels (5x faster than pandas)
        features[f'{col_name}_rm{w}'] = rolling_mean(arr, w)
        features[f'{col_name}_rs{w}'] = rolling_std(arr, w)
        features[f'{col_name}_rmin{w}'] = rolling_min(arr, w)
        features[f'{col_name}_rmax{w}'] = rolling_max(arr, w)

        # Advanced stats
        if w >= 20:  # Need enough data for skew/kurt
            features[f'{col_name}_rskew{w}'] = rolling_skew(arr, w)
            features[f'{col_name}_rkurt{w}'] = rolling_kurt(arr, w)

    return col_name, features


def add_rolling_sweeps(X):
    """Add rolling stats using C++ + parallel."""
    print(f"\nAdding rolling stats (C++ + {N_JOBS} cores parallel)...")

    key_cols = [c for c in X.columns if any(x in c for x in
                ['close', 'ret', 'vol', 'spread', 'volume'])][:20]  # Reduced from 30

    windows = [5, 10, 20, 30, 50, 60, 100, 120, 200, 288, 500]  # Reduced from 19 to 11 windows

    # Parallel rolling computation
    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_rolling_parallel)(col, X[col], windows)
        for col in key_cols
    )

    # Merge results
    rolling = pd.DataFrame(index=X.index)
    for col_name, features in results:
        for feat_name, values in features.items():
            rolling[feat_name] = values

    print(f"  Added {len(rolling.columns)} rolling features")
    return rolling


def compute_ratio_batch(col_pairs, X):
    """Compute ratios for a batch of column pairs."""
    ratios = {}
    for col_a, col_b in col_pairs:
        a = X[col_a].values
        b = X[col_b].values
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = a / b
            ratio[~np.isfinite(ratio)] = 0
            ratios[f'{col_a}_div_{col_b}'] = ratio
    return ratios


def add_pairwise_ratios(X, n_pairs=300):
    """Add pairwise ratios using parallel batches."""
    print(f"\nAdding {n_pairs} pairwise ratios (parallel)...")

    sample_cols = X.columns[::max(1, len(X.columns)//40)][:40]  # Reduced from 50

    # Generate all pairs
    from itertools import combinations
    all_pairs = list(combinations(sample_cols, 2))

    # Split into batches for parallel processing
    batch_size = max(1, len(all_pairs) // N_JOBS)
    batches = [all_pairs[i:i+batch_size] for i in range(0, len(all_pairs), batch_size)]

    # Parallel ratio computation
    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_ratio_batch)(batch, X)
        for batch in batches
    )

    # Merge and select top by variance
    all_ratios = pd.DataFrame(index=X.index)
    for ratio_dict in results:
        for name, values in ratio_dict.items():
            all_ratios[name] = values

    # Select top N by variance
    variances = all_ratios.var()
    top_ratios = variances.nlargest(n_pairs).index.tolist()

    print(f"  Selected top {len(top_ratios)} ratios by variance")
    return all_ratios[top_ratios]


def add_technical_indicators(X):
    """Add technical indicators using C++ kernels."""
    print("\nAdding technical indicators (C++ kernels)...")

    close_cols = [c for c in X.columns if 'close' in c.lower()][:5]
    high_cols = [c for c in X.columns if 'high' in c.lower()][:5]
    low_cols = [c for c in X.columns if 'low' in c.lower()][:5]

    indicators = pd.DataFrame(index=X.index)

    # EMA at multiple periods
    for col in close_cols:
        arr = X[col].values
        for period in [10, 20, 50, 100, 200]:
            indicators[f'{col}_ema{period}'] = ema(arr, period)

    # RSI
    for col in close_cols:
        arr = X[col].values
        for period in [14, 21, 50]:
            indicators[f'{col}_rsi{period}'] = rsi(arr, period)

    # ATR
    for i, (h, l, c) in enumerate(zip(high_cols, low_cols, close_cols)):
        if i < min(len(high_cols), len(low_cols), len(close_cols)):
            high = X[h].values
            low = X[l].values
            close = X[c].values
            for period in [14, 21, 50]:
                indicators[f'atr{i}_{period}'] = atr(high, low, close, period)

    print(f"  Added {len(indicators.columns)} technical indicators")
    return indicators


def add_statistical_moments(X):
    """Add rolling statistical moments."""
    print("\nAdding statistical moments (C++ parallel)...")

    key_cols = [c for c in X.columns if 'ret' in c.lower() or 'vol' in c.lower()][:20]
    windows = [20, 50, 100, 200]

    def compute_moments(col, series, windows):
        features = {}
        arr = series.values
        for w in windows:
            features[f'{col}_skew{w}'] = rolling_skew(arr, w)
            features[f'{col}_kurt{w}'] = rolling_kurt(arr, w)
            features[f'{col}_zscore{w}'] = rolling_zscore(arr, w)
        return col, features

    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_moments)(col, X[col], windows)
        for col in key_cols
    )

    moments = pd.DataFrame(index=X.index)
    for col_name, features in results:
        for feat_name, values in features.items():
            moments[feat_name] = values

    print(f"  Added {len(moments.columns)} statistical moments")
    return moments


def main():
    """Run turbo 3K expansion."""
    print("="*60)
    print("TURBO 3K EXPANSION (C++ + 20-core parallel)")
    print("="*60)

    import time
    start = time.time()

    # Load
    X, y, idx = load_base()

    # Generate features in parallel
    parts = []

    parts.append(add_lag_features(X))
    parts.append(add_rolling_sweeps(X))
    parts.append(add_technical_indicators(X))
    parts.append(add_statistical_moments(X))
    parts.append(add_pairwise_ratios(X))

    # Merge all
    print("\nMerging all features...")
    X_expanded = pd.concat([X] + parts, axis=1)

    # Add labels back
    final = pd.concat([X_expanded, y], axis=1)

    # Remove all-zero columns
    non_zero = (final != 0).any()
    final = final.loc[:, non_zero]

    print(f"\nFinal: {len(final):,} rows × {len(final.columns)} cols")

    # Save
    print(f"\nSaving to {OUTPUT}...")
    final.to_parquet(OUTPUT, compression='snappy', index=False)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"COMPLETE in {elapsed/60:.1f} minutes")
    print(f"Output: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size / 1024**3:.2f} GB")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
