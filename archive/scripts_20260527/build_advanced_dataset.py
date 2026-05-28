#!/usr/bin/env python3
"""
Build dataset with C++-inspired advanced features (Python implementations).
Fast implementations of key algorithms from design spec.
"""

import pandas as pd
import numpy as np
from scipy import stats, signal
from scipy.fft import fft, ifft
import warnings
warnings.filterwarnings('ignore')

print("Loading base dataset...")
df = pd.read_parquet('data/hydra_xauusd_m5_master_clean.parquet')
print(f"Loaded {len(df)} bars with {len(df.columns)} features")

# Subsample for speed
df = df.iloc[::2].reset_index(drop=True)
print(f"Subsampled to {len(df)} bars")

# Need price column - reconstruct from returns
if 'pct_ret_1b' in df.columns:
    df['close'] = (1 + df['pct_ret_1b']).cumprod() * 1800  # Approx starting price
    print("Reconstructed price series")
else:
    print("ERROR: No returns column found")
    exit(1)

print("\n=== Computing advanced features (may take 5-10min) ===\n")

# 1. HURST EXPONENT (R/S analysis)
print("1/12: Hurst exponent...")
def hurst_rs(series):
    n = len(series)
    if n < 20:
        return np.nan
    mean = series.mean()
    cumdev = (series - mean).cumsum()
    R = cumdev.max() - cumdev.min()
    S = series.std()
    return np.log(R / S) / np.log(n) if S > 1e-10 else np.nan

df['hurst_60'] = df['close'].rolling(60).apply(hurst_rs, raw=False)
df['hurst_252'] = df['close'].rolling(252).apply(hurst_rs, raw=False)

# 2. PERMUTATION ENTROPY
print("2/12: Permutation entropy...")
def perm_entropy(series, m=3):
    n = len(series)
    patterns = {}
    for i in range(n - m):
        pattern = tuple(np.argsort(series[i:i+m]))
        patterns[pattern] = patterns.get(pattern, 0) + 1
    probs = np.array(list(patterns.values())) / sum(patterns.values())
    return -np.sum(probs * np.log2(probs + 1e-12))

df['perm_ent_100'] = df['close'].rolling(100).apply(lambda x: perm_entropy(x.values), raw=False)

# 3. SAMPLE ENTROPY (simplified - rolling std/mean ratio)
print("3/12: Sample entropy proxy...")
df['sample_ent_100'] = df['close'].rolling(100).apply(lambda x: x.std() / (abs(x.mean()) + 1e-12), raw=False)

# 4. MULTIFRACTAL WIDTH (quantile ratio)
print("4/12: Multifractal width...")
df['ret_sq'] = df['close'].pct_change() ** 2
df['mf_width_252'] = df['ret_sq'].rolling(252).apply(
    lambda x: np.log(x.quantile(0.95) / (x.quantile(0.05) + 1e-12)), raw=False)

# 5. JUMP DETECTION (Lee-Mykland style)
print("5/12: Jump detection...")
df['bv'] = (df['close'].pct_change().abs() * df['close'].shift(1).pct_change().abs()).rolling(60).sum()
df['jump_stat'] = (df['ret_sq'] / (df['bv'].shift(1) + 1e-12)).rolling(20).mean()
df['jump_detected'] = (df['jump_stat'] > df['jump_stat'].rolling(252).quantile(0.95)).astype(float)

# 6. MICROSTRUCTURE NOISE (autocorrelation proxy)
print("6/12: Microstructure noise...")
df['noise_var'] = -df['close'].pct_change().rolling(60).apply(lambda x: x.autocorr(1), raw=False)
df['signal_to_noise'] = df['realized_vol_60b'] / (df['noise_var'].abs() + 1e-12)

# 7. TRANSFER ENTROPY (lagged correlation proxy)
print("7/12: Transfer entropy proxy...")
df['transfer_ent_60'] = df['close'].rolling(60).corr(df['close'].shift(5)).abs()

# 8. REALIZED VARIANCE COMPONENTS (multi-scale)
print("8/12: Realized variance...")
df['rv_1h'] = df['close'].pct_change().rolling(12).apply(lambda x: (x**2).sum(), raw=False)
df['rv_5h'] = df['close'].pct_change().rolling(60).apply(lambda x: (x**2).sum(), raw=False)
df['rv_ratio'] = df['rv_1h'] / (df['rv_5h'] + 1e-12)

# 9. FRACTAL DIMENSION (simplified)
print("9/12: Fractal dimension...")
df['fractal_dim'] = 2.0 - df['hurst_252']

# 10. COMPLEXITY (LZ-style)
print("10/12: LZ complexity...")
def lz_complexity(series):
    binary = (series > series.median()).astype(int)
    patterns = set()
    current = ""
    for bit in binary:
        current += str(bit)
        if current not in patterns:
            patterns.add(current)
            current = ""
    return len(patterns)

df['lz_complex_100'] = df['close'].rolling(100).apply(lambda x: lz_complexity(x.values), raw=False)

# 11. AUTOCORRELATION STRUCTURE
print("11/12: Autocorrelation features...")
df['autocorr_5'] = df['close'].rolling(60).apply(lambda x: x.autocorr(5), raw=False)
df['autocorr_10'] = df['close'].rolling(60).apply(lambda x: x.autocorr(10), raw=False)
df['autocorr_20'] = df['close'].rolling(60).apply(lambda x: x.autocorr(20), raw=False)

# 12. REGIME INDICATORS
print("12/12: Regime indicators...")
df['vol_regime_zscore'] = (df['realized_vol_60b'] - df['realized_vol_60b'].rolling(252).mean()) / (
    df['realized_vol_60b'].rolling(252).std() + 1e-12)
df['trend_strength'] = df['close'].rolling(60).apply(lambda x: abs(stats.linregress(range(len(x)), x)[0]), raw=False)

print("\n=== Feature computation complete ===\n")

# Drop intermediate columns
df = df.drop(columns=['ret_sq', 'bv', 'close'], errors='ignore')

# Clean NaNs
print(f"Rows before cleaning: {len(df)}")
df = df.dropna()
print(f"Rows after cleaning: {len(df)}")

# Save enriched dataset
output_path = 'data/hydra_xauusd_m5_advanced_cpp.parquet'
df.to_parquet(output_path, index=False)
print(f"\n✅ Saved to {output_path}")
print(f"Final shape: {df.shape}")
print(f"Total features: {len(df.columns)}")
