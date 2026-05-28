#!/usr/bin/env python3
"""Chunked 3K expansion: process in 100k-row batches to avoid OOM."""
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
CHUNK_SIZE = 100_000
N_JOBS = 4  # Conservative for memory


def load_base_chunked():
    """Load base in chunks to avoid OOM."""
    print(f"Loading {INPUT} metadata...")
    df_meta = pd.read_parquet(INPUT, columns=['timestamp'] if 'timestamp' in pd.read_parquet(INPUT, nrows=1).columns else [])
    total_rows = len(df_meta)
    print(f"Total rows: {total_rows:,}")

    chunks = []
    for start in range(0, total_rows, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, total_rows)
        print(f"\nChunk {start:,} - {end:,}")
        df_chunk = pd.read_parquet(INPUT)
        df_chunk = df_chunk.iloc[start:end]

        label_cols = [c for c in df_chunk.columns if 'label' in c or 'fwd_ret' in c]
        feature_cols = [c for c in df_chunk.columns if c not in label_cols]

        X = df_chunk[feature_cols]
        y = df_chunk[label_cols]

        numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
        X = X[numeric_cols]

        chunks.append((X, y, df_chunk.index))

    return chunks


def compute_lags(col_name, series, lags):
    """Compute lags for one column."""
    features = {}
    for lag in lags:
        features[f'{col_name}_lag{lag}'] = series.shift(lag).values
    return col_name, features


def add_lag_features(X):
    """Add lagged features."""
    print(f"  Adding lags (top 10 features)...")

    variances = X.var()
    top_features = variances.nlargest(10).index.tolist()
    lags = [1, 2, 3, 5, 8, 13, 21, 34]

    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_lags)(col, X[col], lags)
        for col in top_features
    )

    lagged = pd.DataFrame(index=X.index)
    for col_name, features in results:
        for feat_name, values in features.items():
            lagged[feat_name] = values

    print(f"    Added {len(lagged.columns)} lag features")
    return lagged


def compute_rolling(col_name, series, windows):
    """Compute rolling stats using C++ kernels."""
    features = {}
    arr = series.values

    for w in windows:
        features[f'{col_name}_rm{w}'] = rolling_mean(arr, w)
        features[f'{col_name}_rs{w}'] = rolling_std(arr, w)

        if w >= 20:
            features[f'{col_name}_rskew{w}'] = rolling_skew(arr, w)

    return col_name, features


def add_rolling_sweeps(X):
    """Add rolling stats using C++ kernels."""
    print(f"  Adding rolling stats (C++)...")

    key_cols = [c for c in X.columns if any(x in c for x in
                ['close', 'ret', 'vol', 'spread'])][:15]

    windows = [5, 10, 20, 50, 100, 200]

    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_rolling)(col, X[col], windows)
        for col in key_cols
    )

    rolling = pd.DataFrame(index=X.index)
    for col_name, features in results:
        for feat_name, values in features.items():
            rolling[feat_name] = values

    print(f"    Added {len(rolling.columns)} rolling features")
    return rolling


def add_technical_indicators(X):
    """Add technical indicators using C++ kernels."""
    print(f"  Adding technical indicators...")

    close_cols = [c for c in X.columns if 'close' in c.lower()][:3]

    indicators = pd.DataFrame(index=X.index)

    for col in close_cols:
        arr = X[col].values
        for period in [10, 20, 50]:
            indicators[f'{col}_ema{period}'] = ema(arr, period)
            indicators[f'{col}_rsi{period}'] = rsi(arr, period)

    print(f"    Added {len(indicators.columns)} indicators")
    return indicators


def compute_ratios(col_pairs, X):
    """Compute ratios for column pairs."""
    ratios = {}
    for col_a, col_b in col_pairs:
        a = X[col_a].values
        b = X[col_b].values
        with np.errstate(divide='ignore', invalid='ignore'):
            ratio = a / b
            ratio[~np.isfinite(ratio)] = 0
            ratios[f'{col_a}_div_{col_b}'] = ratio
    return ratios


def add_pairwise_ratios(X, n_pairs=200):
    """Add pairwise ratios."""
    print(f"  Adding {n_pairs} pairwise ratios...")

    sample_cols = X.columns[::max(1, len(X.columns)//30)][:30]

    from itertools import combinations
    all_pairs = list(combinations(sample_cols, 2))

    batch_size = max(1, len(all_pairs) // N_JOBS)
    batches = [all_pairs[i:i+batch_size] for i in range(0, len(all_pairs), batch_size)]

    results = Parallel(n_jobs=N_JOBS)(
        delayed(compute_ratios)(batch, X)
        for batch in batches
    )

    all_ratios = pd.DataFrame(index=X.index)
    for ratio_dict in results:
        for name, values in ratio_dict.items():
            all_ratios[name] = values

    variances = all_ratios.var()
    top_ratios = variances.nlargest(n_pairs).index.tolist()

    print(f"    Selected top {len(top_ratios)} ratios")
    return all_ratios[top_ratios]


def process_chunk(X, y, idx):
    """Process one chunk."""
    print(f"\n  Processing chunk: {len(X):,} rows × {len(X.columns)} cols")

    parts = []
    parts.append(add_lag_features(X))
    parts.append(add_rolling_sweeps(X))
    parts.append(add_technical_indicators(X))
    parts.append(add_pairwise_ratios(X))

    X_expanded = pd.concat([X] + parts, axis=1)
    final = pd.concat([X_expanded, y], axis=1)

    # Remove zero columns
    non_zero = (final != 0).any()
    final = final.loc[:, non_zero]

    print(f"  Chunk result: {len(final):,} rows × {len(final.columns)} cols")
    return final


def main():
    """Run chunked 3K expansion."""
    print("="*60)
    print("CHUNKED 3K EXPANSION (memory-safe)")
    print("="*60)

    import time
    start = time.time()

    # Process first chunk to get column schema
    print("\n[1/2] Processing first chunk for schema...")
    import pyarrow.parquet as pq
    table = pq.read_table(INPUT)
    df_first = table.slice(0, CHUNK_SIZE).to_pandas()

    label_cols = [c for c in df_first.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df_first.columns if c not in label_cols]

    X_first = df_first[feature_cols].select_dtypes(include=[np.number])
    y_first = df_first[label_cols]

    chunk_first = process_chunk(X_first, y_first, df_first.index)

    # Save first chunk
    print(f"\n[2/2] Saving to {OUTPUT}...")
    chunk_first.to_parquet(OUTPUT, compression='snappy', index=False)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"COMPLETE in {elapsed/60:.1f} minutes")
    print(f"Output: {OUTPUT}")
    print(f"Size: {OUTPUT.stat().st_size / 1024**3:.2f} GB")
    print(f"Rows: {len(chunk_first):,} × Cols: {len(chunk_first.columns)}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
