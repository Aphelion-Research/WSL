"""Regime detection via HMM and calendar-based regimes.

POINT-IN-TIME SAFE API:
- fit_regime_hmm_model(train_df) -> FittedRegimeHMM
- transform_regime_hmm(fitted, df) -> regime features
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
from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass
class FittedRegimeHMM:
    """Fitted HMM regime model with frozen state mapping and normalization.

    Attributes:
        model: Fitted GaussianHMM
        n_states: Number of hidden states
        state_map: Mapping from state_id to regime_name (learned on train)
        state_probs_map: Mapping from regime_name to state_id (for probabilities)
        feature_means: Train-computed feature means (for normalization)
        feature_stds: Train-computed feature stds (for normalization)
    """
    model: Any  # hmmlearn.hmm.GaussianHMM
    n_states: int
    state_map: dict[int, str]
    state_probs_map: dict[str, int]
    feature_means: np.ndarray
    feature_stds: np.ndarray


def _prepare_hmm_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Prepare HMM input features: returns, volatility, volume (raw, unnormalized)."""
    returns = df["close"].pct_change()
    volatility = returns.rolling(20).std()
    volume = df["volume"]

    # Stack raw features (do NOT normalize here)
    X = np.column_stack([
        returns.values,
        volatility.values,
        volume.values,
    ])

    # Valid mask (no NaNs)
    valid_mask = ~np.isnan(X).any(axis=1)

    return X, valid_mask


def _normalize_features(X: np.ndarray, means: np.ndarray, stds: np.ndarray) -> np.ndarray:
    """Normalize features using provided means and stds."""
    return (X - means) / (stds + 1e-10)


def fit_regime_hmm_model(train_df: pd.DataFrame, n_states: int = 4) -> FittedRegimeHMM:
    """Fit HMM regime model on training data only.

    Args:
        train_df: Training DataFrame with ['close', 'volume']
        n_states: Number of hidden states

    Returns:
        FittedRegimeHMM with frozen state mapping

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

    # Compute train normalization stats
    feature_means = X_valid.mean(axis=0)
    feature_stds = X_valid.std(axis=0)

    # Normalize train features
    X_valid_norm = _normalize_features(X_valid, feature_means, feature_stds)

    # Fit HMM on normalized training data only
    model = hmmlearn_hmm.GaussianHMM(
        n_components=n_states,
        covariance_type="full",
        n_iter=100,
        random_state=42,
    )
    model.fit(X_valid_norm)

    # Predict train states to learn state-to-regime mapping
    train_states = np.full(len(X), -1)
    train_states[valid_mask] = model.predict(X_valid_norm)

    # Map states to regime names based on mean train returns
    train_returns = train_df["close"].pct_change()
    state_means = []
    for i in range(n_states):
        state_returns = train_returns.values[train_states == i]
        if len(state_returns) > 0:
            state_means.append((i, np.mean(state_returns)))
        else:
            state_means.append((i, 0))

    state_means.sort(key=lambda x: x[1], reverse=True)

    # Map: highest mean = trending_up, lowest = trending_down, middle = ranging/crisis
    regime_names = ["trending_up", "trending_down", "ranging", "crisis"]
    state_map = {}
    state_probs_map = {}

    for idx, (state, _) in enumerate(state_means):
        if idx < len(regime_names):
            regime_name = regime_names[idx]
        else:
            regime_name = "unknown"
        state_map[state] = regime_name

    # Build reverse map for probabilities
    state_probs_map["trending_up"] = state_means[0][0] if len(state_means) > 0 else 0
    state_probs_map["trending_down"] = state_means[-1][0] if len(state_means) > 0 else 0
    state_probs_map["ranging"] = state_means[1][0] if len(state_means) > 1 else 0
    state_probs_map["crisis"] = state_means[2][0] if len(state_means) > 2 else 0

    return FittedRegimeHMM(
        model=model,
        n_states=n_states,
        state_map=state_map,
        state_probs_map=state_probs_map,
        feature_means=feature_means,
        feature_stds=feature_stds,
    )


def transform_regime_hmm(
    fitted: FittedRegimeHMM,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """Transform data using fitted HMM model (point-in-time safe, prefix-stable).

    Args:
        fitted: FittedRegimeHMM from fit_regime_hmm_model()
        df: DataFrame to transform with ['close', 'volume']

    Returns:
        DataFrame with regime features:
        - regime_tactical: regime label (trending_up, trending_down, ranging, crisis)
        - regime_prob_trend_up, regime_prob_trend_down, regime_prob_ranging, regime_prob_crisis
    """
    features = pd.DataFrame(index=df.index)

    X, valid_mask = _prepare_hmm_features(df)

    if valid_mask.sum() == 0:
        # No valid data, return unknown
        features["regime_tactical"] = "unknown"
        features["regime_prob_trend_up"] = 0.25
        features["regime_prob_trend_down"] = 0.25
        features["regime_prob_ranging"] = 0.25
        features["regime_prob_crisis"] = 0.25
        return features

    # Normalize using TRAIN stats only (prefix-stable)
    X_norm = _normalize_features(X, fitted.feature_means, fitted.feature_stds)

    # POINTWISE prediction (prefix-stable, no full-sequence Viterbi)
    # For each valid row, predict independently
    states = np.full(len(X), -1, dtype=int)
    probs = np.full((len(X), fitted.n_states), 1.0 / fitted.n_states, dtype=float)

    valid_indices = np.where(valid_mask)[0]
    for i in valid_indices:
        row = X_norm[i:i+1]  # shape (1, n_features), normalized
        # Pointwise prediction (no dependency on future rows)
        row_probs = fitted.model.predict_proba(row)[0]
        probs[i] = row_probs
        states[i] = np.argmax(row_probs)

    # Apply frozen state_map (learned on train)
    regime_labels = [fitted.state_map.get(s, "unknown") for s in states]
    features["regime_tactical"] = regime_labels

    # Probability columns (use frozen state_probs_map)
    features["regime_prob_trend_up"] = probs[:, fitted.state_probs_map["trending_up"]]
    features["regime_prob_trend_down"] = probs[:, fitted.state_probs_map["trending_down"]]
    features["regime_prob_ranging"] = probs[:, fitted.state_probs_map["ranging"]]
    features["regime_prob_crisis"] = probs[:, fitted.state_probs_map["crisis"]]

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

    # Fit on training data (returns FittedRegimeHMM)
    fitted = fit_regime_hmm_model(train_df, n_states=n_states)

    # Transform both (no train_returns needed, state_map frozen)
    train_features = transform_regime_hmm(fitted, train_df)
    oos_features = transform_regime_hmm(fitted, oos_df)

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

    # Fit on full data (LEAKY) - returns FittedRegimeHMM
    fitted = fit_regime_hmm_model(df, n_states=n_states)
    return transform_regime_hmm(fitted, df)


# ─────────────────────────────────────────────────────────────────────────────
# Time-based regimes (no leakage, calendar-only)
# ─────────────────────────────────────────────────────────────────────────────

def detect_micro_regime(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Detect micro (time-of-day) regime.

    Regimes: london, ny, asian, overlap, dead_zone

    Args:
        timestamps: DatetimeIndex or compatible index

    Returns:
        DataFrame with regime_micro column
    """
    features = pd.DataFrame(index=timestamps)

    regimes = []
    for ts in timestamps:
        # Handle non-datetime indexes defensively
        if isinstance(ts, pd.Timestamp):
            hour = ts.hour
        elif hasattr(ts, "hour"):
            hour = ts.hour
        else:
            # Cannot determine time-of-day, default to unknown
            regimes.append("unknown")
            continue

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
