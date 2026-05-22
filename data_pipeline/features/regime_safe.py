"""Regime detection via HMM and calendar-based regimes.

POINT-IN-TIME SAFE API:
- fit_regime_hmm_model(train_df) -> fitted model
- transform_regime_hmm(model, df) -> regime features
- fit_transform_split(train_df, oos_df) -> both DataFrames with regimes

OLD API (detect_tactical_regime_hmm) is DEPRECATED and LEAKS.

EXAMPLE USAGE:
    from data_pipeline.features.regime_safe import fit_transform_split

    # Split data
    train = df.iloc[:1000]
    oos = df.iloc[1000:]

    # Fit on train, transform both (point-in-time safe)
    train_regimes, oos_regimes = fit_transform_split(train, oos)

    # OOS regime labels use train-fitted model only (no future leakage)
    print(oos_regimes["regime_tactical"])
"""
import numpy as np
import pandas as pd
from typing import Optional, Tuple


def _prepare_hmm_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Prepare HMM input features: returns, volatility, volume."""
    returns = df["close"].pct_change()
    volatility = returns.rolling(20).std()
    volume = df["volume"]

    # Normalize
    X = np.column_stack([
        (returns - returns.mean()) / (returns.std() + 1e-10),
        (volatility - volatility.mean()) / (volatility.std() + 1e-10),
        (volume - volume.mean()) / (volume.std() + 1e-10),
    ])

    # Valid mask (no NaNs)
    valid_mask = ~np.isnan(X).any(axis=1)

    return X, valid_mask


def fit_regime_hmm_model(train_df: pd.DataFrame, n_states: int = 4):
    """Fit HMM regime model on training data only.

    Args:
        train_df: Training DataFrame with ['close', 'volume']
        n_states: Number of hidden states

    Returns:
        Fitted HMM model (hmmlearn.hmm.GaussianHMM)

    Raises:
        ImportError: If hmmlearn not available
        ValueError: If insufficient training data
    """
    try:
        from hmmlearn import hmm as hmmlearn_hmm
    except ImportError:
        raise ImportError("hmmlearn not installed. Install via: pip install hmmlearn")

    X, valid_mask = _prepare_hmm_features(train_df)
    X_valid = X[valid_mask]

    if len(X_valid) < 100:
        raise ValueError(f"Insufficient training data: {len(X_valid)} valid rows (need ≥100)")

    # Fit HMM on training data only
    model = hmmlearn_hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=100,
        random_state=42,
    )
    model.fit(X_valid)

    return model


def transform_regime_hmm(
    model,
    df: pd.DataFrame,
    train_returns: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Transform data using fitted HMM model (point-in-time safe).

    Args:
        model: Fitted HMM model from fit_regime_hmm_model()
        df: DataFrame to transform with ['close', 'volume']
        train_returns: Training returns for state-to-regime mapping (optional)

    Returns:
        DataFrame with regime features:
        - regime_tactical: regime label (trending_up, trending_down, ranging, crisis)
        - regime_prob_trend_up, regime_prob_trend_down, regime_prob_ranging, regime_prob_crisis
    """
    features = pd.DataFrame(index=df.index)

    X, valid_mask = _prepare_hmm_features(df)
    X_valid = X[valid_mask]

    if len(X_valid) == 0:
        # No valid data, return unknown
        features["regime_tactical"] = "unknown"
        features["regime_prob_trend_up"] = 0.25
        features["regime_prob_trend_down"] = 0.25
        features["regime_prob_ranging"] = 0.25
        features["regime_prob_crisis"] = 0.25
        return features

    # Predict states (transform only, no fitting)
    states = np.full(len(X), -1)
    states[valid_mask] = model.predict(X_valid)

    # Predict probabilities
    n_states = model.n_components
    probs = np.full((len(X), n_states), 1.0 / n_states)
    probs[valid_mask] = model.predict_proba(X_valid)

    # Map states to regime names based on mean returns
    returns = df["close"].pct_change() if train_returns is None else train_returns
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


def fit_transform_split(
    train_df: pd.DataFrame,
    oos_df: pd.DataFrame,
    n_states: int = 4,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Fit HMM on training data, transform both train and OOS (point-in-time safe).

    Args:
        train_df: Training DataFrame
        oos_df: Out-of-sample DataFrame
        n_states: Number of hidden states

    Returns:
        (train_features, oos_features): DataFrames with regime columns
    """
    try:
        from hmmlearn import hmm as hmmlearn_hmm
    except ImportError:
        # Graceful degradation
        def _fallback(df):
            features = pd.DataFrame(index=df.index)
            features["regime_tactical"] = "unknown"
            features["regime_prob_trend_up"] = 0.25
            features["regime_prob_trend_down"] = 0.25
            features["regime_prob_ranging"] = 0.25
            features["regime_prob_crisis"] = 0.25
            return features

        return _fallback(train_df), _fallback(oos_df)

    # Fit on training data
    model = fit_regime_hmm_model(train_df, n_states=n_states)

    # Get training returns for state mapping
    train_returns = train_df["close"].pct_change()

    # Transform both
    train_features = transform_regime_hmm(model, train_df, train_returns=train_returns)
    oos_features = transform_regime_hmm(model, oos_df, train_returns=train_returns)

    return train_features, oos_features


# ─────────────────────────────────────────────────────────────────────────────
# DEPRECATED: OLD LEAKY API (kept for backward compat, prints warning)
# ─────────────────────────────────────────────────────────────────────────────

def detect_tactical_regime_hmm(df: pd.DataFrame, n_states: int = 4) -> pd.DataFrame:
    """DEPRECATED: Fits HMM on full data (LEAKS FUTURE INTO PAST).

    Use fit_transform_split() instead for point-in-time safety.

    This function is kept for backward compatibility but prints a warning.
    """
    import warnings
    warnings.warn(
        "detect_tactical_regime_hmm() fits HMM on full data (LEAKS). "
        "Use fit_transform_split(train, oos) instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    try:
        from hmmlearn import hmm as hmmlearn_hmm
    except ImportError:
        features = pd.DataFrame(index=df.index)
        features["regime_tactical"] = "unknown"
        features["regime_prob_trend_up"] = 0.25
        features["regime_prob_trend_down"] = 0.25
        features["regime_prob_ranging"] = 0.25
        features["regime_prob_crisis"] = 0.25
        return features

    # Fit on full data (LEAKY)
    model = fit_regime_hmm_model(df, n_states=n_states)
    return transform_regime_hmm(model, df)


# ─────────────────────────────────────────────────────────────────────────────
# Time-based regimes (no leakage, calendar-only)
# ─────────────────────────────────────────────────────────────────────────────

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


def compute_historical_return_by_regime(
    df: pd.DataFrame,
    regime_series: pd.Series,
    window: int = 252,
) -> pd.DataFrame:
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
