#!/usr/bin/env python3
"""Expand feature matrix to 3000+ columns via programmatic generation."""
import pandas as pd
import numpy as np
from pathlib import Path
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

INPUT = Path("data/hydra_xauusd_m5_master.parquet")
OUTPUT = Path("data/hydra_xauusd_m5_3k.parquet")


def load_base():
    """Load base feature matrix."""
    df = pd.read_parquet(INPUT)
    print(f"Base: {len(df)} rows × {len(df.columns)} cols")

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    X = df[feature_cols]
    y = df[label_cols]

    # Select numeric columns only
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    X = X[numeric_cols]

    print(f"Numeric features: {len(numeric_cols)}")
    return X, y, df.index


def add_lag_features(X, n_lags=50):
    """Add lagged features for top variables."""
    print(f"\nAdding {n_lags} lags for key features...")

    # Select high-variance features
    variances = X.var()
    top_features = variances.nlargest(20).index.tolist()

    lagged = pd.DataFrame(index=X.index)
    for col in top_features:
        for lag in [1,2,3,5,8,13,21,34,55,89,144,233]:
            lagged[f'{col}_lag{lag}'] = X[col].shift(lag)

    print(f"  Added {len(lagged.columns)} lag features")
    return lagged


def add_rolling_sweeps(X):
    """Add rolling stats at many windows."""
    print("\nAdding rolling stats sweeps...")

    # Select subset for rolling
    key_cols = [c for c in X.columns if any(x in c for x in
                ['close', 'ret', 'vol', 'spread', 'volume'])][:30]

    windows = [5,10,15,20,30,40,50,60,72,89,100,120,144,200,288,377,500,720,1000]

    rolling = pd.DataFrame(index=X.index)
    for col in key_cols:
        s = X[col]
        for w in windows:
            rolling[f'{col}_rm{w}'] = s.rolling(w).mean()
            rolling[f'{col}_rs{w}'] = s.rolling(w).std()
            rolling[f'{col}_rmin{w}'] = s.rolling(w).min()
            rolling[f'{col}_rmax{w}'] = s.rolling(w).max()

    print(f"  Added {len(rolling.columns)} rolling features")
    return rolling


def add_pairwise_ratios(X, n_pairs=500):
    """Add top N pairwise ratios by variance."""
    print(f"\nAdding {n_pairs} pairwise ratios...")

    # Select diverse features
    sample_cols = X.columns[::max(1, len(X.columns)//50)][:50]

    ratios = []
    for c1, c2 in combinations(sample_cols, 2):
        ratio = X[c1] / (X[c2].abs() + 1e-10)
        ratio = ratio.clip(-100, 100)
        variance = ratio.var()
        ratios.append((f'{c1}_div_{c2}', ratio, variance))

    # Keep top N by variance
    ratios.sort(key=lambda x: x[2], reverse=True)

    ratio_df = pd.DataFrame(index=X.index)
    for name, series, _ in ratios[:n_pairs]:
        ratio_df[name] = series

    print(f"  Added {len(ratio_df.columns)} ratio features")
    return ratio_df


def add_percentile_ranks(X):
    """Add rolling percentile ranks."""
    print("\nAdding percentile rank features...")

    key_cols = [c for c in X.columns if 'close' in c or 'ret' in c or 'vol' in c][:20]

    pct = pd.DataFrame(index=X.index)
    for col in key_cols:
        s = X[col]
        for w in [20, 50, 100, 252, 500]:
            pct[f'{col}_pct{w}'] = s.rolling(w).rank(pct=True)

    print(f"  Added {len(pct.columns)} percentile features")
    return pct


def add_cross_correlations(X):
    """Add rolling cross-correlations."""
    print("\nAdding cross-correlation features...")

    # Select price-like and vol-like features
    price_like = [c for c in X.columns if 'close' in c or 'ema' in c][:10]
    vol_like = [c for c in X.columns if 'vol' in c or 'atr' in c][:10]

    corr_df = pd.DataFrame(index=X.index)

    for c1 in price_like:
        for c2 in vol_like:
            if c1 != c2:
                for w in [20, 50, 100]:
                    corr = X[c1].rolling(w).corr(X[c2])
                    corr_df[f'corr_{c1}_{c2}_{w}'] = corr.fillna(0)

    print(f"  Added {len(corr_df.columns)} correlation features")
    return corr_df


def add_momentum_features(X):
    """Add momentum at many horizons."""
    print("\nAdding momentum features...")

    close_cols = [c for c in X.columns if 'close' in c][:5]

    mom = pd.DataFrame(index=X.index)
    horizons = [3,5,8,13,21,34,55,89,144,233,377,500,720]

    for col in close_cols:
        s = X[col]
        for h in horizons:
            mom[f'{col}_mom{h}'] = s / (s.shift(h) + 1e-10) - 1

    print(f"  Added {len(mom.columns)} momentum features")
    return mom


def add_statistical_moments(X):
    """Add skew/kurt at many windows."""
    print("\nAdding statistical moments...")

    ret_cols = [c for c in X.columns if 'ret' in c][:15]

    stats = pd.DataFrame(index=X.index)
    for col in ret_cols:
        s = X[col]
        for w in [10, 20, 50, 100, 200]:
            stats[f'{col}_skew{w}'] = s.rolling(w).skew()
            stats[f'{col}_kurt{w}'] = s.rolling(w).kurt()

    print(f"  Added {len(stats.columns)} statistical features")
    return stats


def add_technical_sweeps(X):
    """Add technical indicators with parameter sweeps."""
    print("\nAdding technical indicator sweeps...")

    close_cols = [c for c in X.columns if 'close' in c][:3]

    tech = pd.DataFrame(index=X.index)

    # RSI sweep
    for col in close_cols:
        s = X[col]
        for period in [3,5,7,9,11,14,17,20,25,30,40,50,70,100]:
            delta = s.diff()
            gain = delta.clip(lower=0).rolling(period).mean()
            loss = (-delta.clip(upper=0)).rolling(period).mean()
            rs = gain / (loss + 1e-10)
            rsi = rs / (1 + rs) - 0.5
            tech[f'{col}_rsi{period}'] = rsi

    print(f"  Added {len(tech.columns)} technical features")
    return tech


def add_volatility_regime(X):
    """Add volatility regime features."""
    print("\nAdding volatility regime features...")

    vol_cols = [c for c in X.columns if 'vol' in c or 'atr' in c][:10]

    regime = pd.DataFrame(index=X.index)
    for col in vol_cols:
        s = X[col]
        for w in [20, 50, 100, 252]:
            pct = s.rolling(w).rank(pct=True)
            regime[f'{col}_regime{w}'] = pd.cut(pct, bins=[0,0.25,0.5,0.75,1.0],
                                                labels=[0,1,2,3]).astype(float)

    print(f"  Added {len(regime.columns)} regime features")
    return regime


def add_price_patterns(X):
    """Add price pattern features."""
    print("\nAdding price pattern features...")

    close_cols = [c for c in X.columns if 'close' in c][:5]

    patterns = pd.DataFrame(index=X.index)
    for col in close_cols:
        s = X[col]

        # Higher highs, lower lows
        for w in [5, 10, 20, 50]:
            hh = (s > s.rolling(w).max().shift(1)).astype(float)
            ll = (s < s.rolling(w).min().shift(1)).astype(float)
            patterns[f'{col}_hh{w}'] = hh
            patterns[f'{col}_ll{w}'] = ll

        # Distance to moving averages
        for w in [10,20,50,100,200]:
            ma = s.rolling(w).mean()
            patterns[f'{col}_dist_ma{w}'] = (s - ma) / (ma + 1e-10)

    print(f"  Added {len(patterns.columns)} pattern features")
    return patterns


def add_interaction_terms(X, n_terms=300):
    """Add multiplicative interaction terms."""
    print(f"\nAdding {n_terms} interaction terms...")

    # Sample diverse features
    sample = X.columns[::max(1, len(X.columns)//40)][:40]

    interactions = []
    for c1, c2 in combinations(sample, 2):
        prod = X[c1] * X[c2]
        prod = prod.clip(-1e6, 1e6)
        variance = prod.var()
        interactions.append((f'{c1}_x_{c2}', prod, variance))

    interactions.sort(key=lambda x: x[2], reverse=True)

    interact_df = pd.DataFrame(index=X.index)
    for name, series, _ in interactions[:n_terms]:
        interact_df[name] = series

    print(f"  Added {len(interact_df.columns)} interaction features")
    return interact_df


def main():
    print("="*60)
    print("EXPANDING TO 3000+ FEATURES")
    print("="*60)

    X, y, index = load_base()

    # Generate expansions
    expansions = []

    expansions.append(add_lag_features(X, n_lags=50))
    expansions.append(add_rolling_sweeps(X))
    expansions.append(add_pairwise_ratios(X, n_pairs=500))
    expansions.append(add_percentile_ranks(X))
    expansions.append(add_cross_correlations(X))
    expansions.append(add_momentum_features(X))
    expansions.append(add_statistical_moments(X))
    expansions.append(add_technical_sweeps(X))
    expansions.append(add_volatility_regime(X))
    expansions.append(add_price_patterns(X))
    expansions.append(add_interaction_terms(X, n_terms=300))

    # Combine
    print("\nCombining all features...")
    all_features = pd.concat([X] + expansions, axis=1)

    # Fill NaN
    all_features = all_features.fillna(0)
    all_features = all_features.replace([np.inf, -np.inf], 0)

    # Convert to float32
    for col in all_features.columns:
        try:
            all_features[col] = all_features[col].astype('float32')
        except:
            pass

    # Combine with labels
    master = pd.concat([all_features, y], axis=1)
    master.index = index

    # Save
    master.to_parquet(OUTPUT)

    real_features = [c for c in all_features.columns if not all_features[c].eq(0).all()]

    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    print(f"Output:          {OUTPUT}")
    print(f"Total rows:      {len(master)}")
    print(f"Total columns:   {len(master.columns)}")
    print(f"Real features:   {len(real_features)}")
    print(f"Label columns:   {len(y.columns)}")
    print(f"Target 3000:     {'YES' if len(real_features) >= 3000 else f'NO ({len(real_features)}/3000)'}")
    print("="*60)


if __name__ == "__main__":
    main()
