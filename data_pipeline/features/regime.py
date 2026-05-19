"""Regime detection via HMM and calendar-based regimes."""
import numpy as np
import pandas as pd
from datetime import datetime


def detect_tactical_regime_hmm(df: pd.DataFrame, n_states: int = 4) -> pd.DataFrame:
    """Detect tactical regime via Hidden Markov Model.

    States: trending_up, trending_down, ranging, crisis
    """
    try:
        from hmmlearn import hmm as hmmlearn_hmm
    except ImportError:
        # Graceful degradation if hmmlearn not available
        features = pd.DataFrame(index=df.index)
        features["regime_tactical"] = "unknown"
        features["regime_prob_trend_up"] = 0.25
        features["regime_prob_trend_down"] = 0.25
        features["regime_prob_ranging"] = 0.25
        features["regime_prob_crisis"] = 0.25
        return features

    features = pd.DataFrame(index=df.index)

    # Prepare HMM features: returns, volatility, volume
    returns = df["close"].pct_change()
    volatility = returns.rolling(20).std()
    volume = df["volume"]

    # Normalize features
    X = np.column_stack([
        (returns - returns.mean()) / (returns.std() + 1e-10),
        (volatility - volatility.mean()) / (volatility.std() + 1e-10),
        (volume - volume.mean()) / (volume.std() + 1e-10),
    ])

    # Remove NaNs
    valid_mask = ~np.isnan(X).any(axis=1)
    X_valid = X[valid_mask]

    if len(X_valid) < 100:
        # Not enough data
        features["regime_tactical"] = "unknown"
        features["regime_prob_trend_up"] = 0.25
        features["regime_prob_trend_down"] = 0.25
        features["regime_prob_ranging"] = 0.25
        features["regime_prob_crisis"] = 0.25
        return features

    # Fit HMM
    model = hmmlearn_hmm.GaussianHMM(n_components=n_states, covariance_type="full", n_iter=100)
    model.fit(X_valid)

    # Predict states
    states = np.full(len(X), -1)
    states[valid_mask] = model.predict(X_valid)

    # Predict probabilities
    probs = np.full((len(X), n_states), 0.25)
    probs[valid_mask] = model.predict_proba(X_valid)

    # Map states to regime names based on mean returns
    state_means = []
    for i in range(n_states):
        state_returns = returns.values[states == i]
        if len(state_returns) > 0:
            state_means.append((i, np.mean(state_returns)))
        else:
            state_means.append((i, 0))

    state_means.sort(key=lambda x: x[1], reverse=True)

    # Map: highest mean = trending_up, lowest = trending_down, middle = ranging/crisis
    state_map = {}
    regime_names = ["trending_up", "trending_down", "ranging", "crisis"]
    for idx, (state, _) in enumerate(state_means):
        if idx < len(regime_names):
            state_map[state] = regime_names[idx]
        else:
            state_map[state] = "unknown"

    # Apply mapping
    regime_labels = [state_map.get(s, "unknown") for s in states]
    features["regime_tactical"] = regime_labels

    # Probability columns
    features["regime_prob_trend_up"] = probs[:, state_means[0][0]] if len(state_means) > 0 else 0.25
    features["regime_prob_trend_down"] = probs[:, state_means[-1][0]] if len(state_means) > 0 else 0.25
    features["regime_prob_ranging"] = probs[:, state_means[1][0] if len(state_means) > 1 else 0] if len(state_means) > 1 else 0.25
    features["regime_prob_crisis"] = probs[:, state_means[2][0] if len(state_means) > 2 else 0] if len(state_means) > 2 else 0.25

    return features


def detect_micro_regime(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Detect micro (time-of-day) regime.

    Regimes: london, ny, asian, overlap, dead_zone
    """
    features = pd.DataFrame(index=timestamps)

    regimes = []
    for ts in timestamps:
        hour = ts.hour

        if 8 <= hour < 13:
            regimes.append("london")
        elif 13 <= hour < 17:
            regimes.append("overlap")
        elif 17 <= hour < 22:
            regimes.append("ny")
        elif 22 <= hour < 23:
            regimes.append("dead_zone")
        else:
            regimes.append("asian")

    features["regime_micro"] = regimes

    return features


def compute_regime_duration(regime_series: pd.Series) -> pd.Series:
    """Compute bars in current regime."""
    duration = []
    current_regime = None
    current_duration = 0

    for regime in regime_series:
        if regime == current_regime:
            current_duration += 1
        else:
            current_regime = regime
            current_duration = 1
        duration.append(current_duration)

    return pd.Series(duration, index=regime_series.index)


def compute_regime_transition(regime_series: pd.Series) -> pd.Series:
    """Detect regime transitions (binary flag)."""
    return (regime_series != regime_series.shift(1)).astype(int)


def compute_historical_return_by_regime(df: pd.DataFrame, regime_series: pd.Series, window: int = 252) -> pd.DataFrame:
    """Compute historical return by regime (rolling)."""
    features = pd.DataFrame(index=df.index)
    returns = df["close"].pct_change()

    for regime in regime_series.unique():
        regime_returns = []
        for i in range(len(returns)):
            if i < window:
                regime_returns.append(np.nan)
            else:
                window_regimes = regime_series.iloc[i - window:i]
                window_returns = returns.iloc[i - window:i]
                regime_mask = window_regimes == regime
                if regime_mask.sum() > 0:
                    avg_ret = window_returns[regime_mask].mean()
                else:
                    avg_ret = np.nan
                regime_returns.append(avg_ret)

        features[f"regime_hist_ret_{regime}"] = regime_returns

    return features


def compute_all_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all regime features (~40 features)."""
    # Tactical regime via HMM
    tactical = detect_tactical_regime_hmm(df)

    # Micro regime (time-based)
    micro = detect_micro_regime(df.index)

    # Duration and transition
    tactical["regime_duration"] = compute_regime_duration(tactical["regime_tactical"])
    tactical["regime_transition"] = compute_regime_transition(tactical["regime_tactical"])

    # Historical returns by regime
    hist_returns = compute_historical_return_by_regime(df, tactical["regime_tactical"])

    # Combine
    all_features = pd.concat([tactical, micro, hist_returns], axis=1)

    return all_features
