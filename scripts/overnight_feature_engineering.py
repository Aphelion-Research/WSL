#!/usr/bin/env python3
"""Advanced feature engineering overnight."""
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from scipy.fft import fft
import warnings
warnings.filterwarnings('ignore')

INPUT = Path("data/hydra_xauusd_m5_3k.parquet")
OUTPUT = Path("data/hydra_xauusd_m5_advanced.parquet")


def add_fourier_features(X, n_freq=50):
    """Add Fourier transform features."""
    print(f"Adding top {n_freq} Fourier frequencies...")

    price_cols = [c for c in X.columns if 'close' in c][:5]
    fourier_df = pd.DataFrame(index=X.index)

    for col in price_cols:
        s = X[col].fillna(0).values
        fft_vals = fft(s)
        power = np.abs(fft_vals) ** 2

        # Top N frequencies by power
        top_freq_idx = np.argsort(power)[-n_freq:]

        for i, freq_idx in enumerate(top_freq_idx):
            fourier_df[f'{col}_fft_power_{i}'] = power[freq_idx]
            fourier_df[f'{col}_fft_phase_{i}'] = np.angle(fft_vals[freq_idx])

    print(f"  Added {len(fourier_df.columns)} Fourier features")
    return fourier_df


def add_wavelet_features(X):
    """Add wavelet decomposition features."""
    print("Adding wavelet decomposition...")

    from scipy.signal import cwt, ricker

    price_cols = [c for c in X.columns if 'close' in c][:3]
    wavelet_df = pd.DataFrame(index=X.index)

    widths = [5, 10, 20, 40, 80]

    for col in price_cols:
        s = X[col].fillna(method='ffill').fillna(0).values
        for width in widths:
            coef = cwt(s, ricker, [width])
            wavelet_df[f'{col}_wavelet_{width}'] = coef[0]

    print(f"  Added {len(wavelet_df.columns)} wavelet features")
    return wavelet_df


def add_entropy_features(X):
    """Add entropy-based features."""
    print("Adding entropy features...")

    ret_cols = [c for c in X.columns if 'ret' in c][:10]
    entropy_df = pd.DataFrame(index=X.index)

    for col in ret_cols:
        s = X[col]
        for w in [20, 50, 100]:
            # Shannon entropy
            def shannon_entropy(x):
                if len(x) < 5:
                    return 0
                hist, _ = np.histogram(x, bins=10)
                hist = hist / hist.sum()
                hist = hist[hist > 0]
                return -np.sum(hist * np.log2(hist))

            entropy_df[f'{col}_entropy_{w}'] = s.rolling(w).apply(shannon_entropy, raw=True)

    print(f"  Added {len(entropy_df.columns)} entropy features")
    return entropy_df


def add_fractal_dimension(X):
    """Add fractal dimension (Hurst exponent) at multiple scales."""
    print("Adding fractal dimension features...")

    price_cols = [c for c in X.columns if 'close' in c][:5]
    fractal_df = pd.DataFrame(index=X.index)

    def hurst_exponent(ts):
        if len(ts) < 10:
            return 0.5
        lags = range(2, min(20, len(ts)//2))
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0

    for col in price_cols:
        s = X[col]
        for w in [50, 100, 200]:
            fractal_df[f'{col}_hurst_{w}'] = s.rolling(w).apply(hurst_exponent, raw=True)

    print(f"  Added {len(fractal_df.columns)} fractal features")
    return fractal_df


def add_microstructure_proxies(X):
    """Add microstructure proxies."""
    print("Adding microstructure proxy features...")

    micro_df = pd.DataFrame(index=X.index)

    # Kyle's lambda (price impact)
    if 'close' in X.columns and 'volume' in X.columns:
        close = X['close']
        volume = X['volume']

        for w in [20, 50, 100]:
            ret = np.log(close / close.shift(1))
            kyle_lambda = (ret.abs() / (volume + 1)).rolling(w).mean()
            micro_df[f'kyle_lambda_{w}'] = kyle_lambda

    # Roll spread estimator
    if 'close' in X.columns:
        close = X['close']
        for w in [20, 50]:
            price_changes = close.diff()
            cov = price_changes.rolling(w).cov(price_changes.shift(1))
            roll_spread = 2 * np.sqrt(-cov).clip(lower=0)
            micro_df[f'roll_spread_{w}'] = roll_spread

    print(f"  Added {len(micro_df.columns)} microstructure features")
    return micro_df


def add_market_regime_hmm(X):
    """Add HMM-based regime features.

    WARNING: This function fits HMM on FULL data (train+OOS together).
    For backtest/research, use fit_transform_split() from regime_safe.py instead.

    This function is for OFFLINE feature engineering only (not point-in-time safe).
    """
    print("Adding HMM regime features...")
    print("  WARNING: Fitting HMM on full data (NOT point-in-time safe)")

    try:
        from hmmlearn import hmm

        regime_df = pd.DataFrame(index=X.index)

        # Use volatility for regime detection
        vol_cols = [c for c in X.columns if 'vol' in c or 'atr' in c][:3]

        for col in vol_cols:
            s = X[col].fillna(0).values.reshape(-1, 1)

            # Fit 3-state HMM on subsampled data (LEAKY but fast for offline features)
            model = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=100, random_state=42)

            # Fit on first 80% of data only (train proxy)
            train_len = int(len(s) * 0.8)
            s_train = s[:train_len][::10]  # Subsample for speed

            if len(s_train) < 100:
                print(f"  Skipping {col}: insufficient data")
                continue

            model.fit(s_train)

            # Transform full data (train + OOS)
            states = model.predict(s)
            regime_df[f'{col}_hmm_state'] = states

            # State probabilities
            probs = model.predict_proba(s)
            for i in range(3):
                regime_df[f'{col}_hmm_prob_{i}'] = probs[:, i]

        print(f"  Added {len(regime_df.columns)} HMM features")
        return regime_df
    except ImportError:
        print("  HMM library not available, skipping")
        return pd.DataFrame(index=X.index)


def add_info_theory_features(X):
    """Add information theory features."""
    print("Adding information theory features...")

    info_df = pd.DataFrame(index=X.index)

    ret_cols = [c for c in X.columns if 'ret' in c][:5]

    for c1 in ret_cols[:3]:
        for c2 in ret_cols[3:5]:
            if c1 != c2:
                s1 = X[c1].fillna(0)
                s2 = X[c2].fillna(0)

                # Mutual information (rolling)
                def mutual_info(window):
                    if len(window) < 10:
                        return 0
                    x = window[:len(window)//2]
                    y = window[len(window)//2:]
                    return np.corrcoef(x, y)[0, 1] ** 2

                combined = pd.concat([s1, s2], axis=1).sum(axis=1)
                info_df[f'mi_{c1}_{c2}'] = combined.rolling(40).apply(mutual_info, raw=True)

    print(f"  Added {len(info_df.columns)} info theory features")
    return info_df


def main():
    print("="*60)
    print("ADVANCED FEATURE ENGINEERING")
    print("="*60)

    if not INPUT.exists():
        print(f"ERROR: {INPUT} not found. Run overnight_build.sh first.")
        return

    print(f"Loading {INPUT}...")
    df = pd.read_parquet(INPUT)

    label_cols = [c for c in df.columns if 'label' in c or 'fwd_ret' in c]
    feature_cols = [c for c in df.columns if c not in label_cols]

    X = df[feature_cols]
    y = df[label_cols]

    print(f"Base: {len(X)} rows × {len(feature_cols)} features")

    # Add advanced features
    advanced = []

    advanced.append(add_fourier_features(X, n_freq=30))
    # advanced.append(add_wavelet_features(X))  # Slow, skip for now
    advanced.append(add_entropy_features(X))
    advanced.append(add_fractal_dimension(X))
    advanced.append(add_microstructure_proxies(X))
    advanced.append(add_market_regime_hmm(X))
    advanced.append(add_info_theory_features(X))

    # Combine
    print("\nCombining advanced features...")
    all_features = pd.concat([X] + advanced, axis=1)
    all_features = all_features.fillna(0).replace([np.inf, -np.inf], 0)

    for col in all_features.columns:
        try:
            all_features[col] = all_features[col].astype('float32')
        except:
            pass

    master = pd.concat([all_features, y], axis=1)
    master.index = df.index

    master.to_parquet(OUTPUT)

    real = [c for c in all_features.columns if not all_features[c].eq(0).all()]

    print("\n" + "="*60)
    print("ADVANCED FEATURES COMPLETE")
    print("="*60)
    print(f"Output:        {OUTPUT}")
    print(f"Total rows:    {len(master)}")
    print(f"Total features: {len(real)}")
    print(f"Labels:        {len(label_cols)}")
    print("="*60)


if __name__ == "__main__":
    main()
