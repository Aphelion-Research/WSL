"""Regime detection via HMM and calendar-based regimes.

DEPRECATED: This module contains LEAKY HMM code.
Use data_pipeline.features.regime_safe instead.
"""
import warnings
import numpy as np
import pandas as pd
from datetime import datetime

# Import safe API
from data_pipeline.features.regime_safe import (
    fit_regime_hmm_model,
    transform_regime_hmm,
    fit_transform_split,
    detect_tactical_regime_hmm as _detect_tactical_regime_hmm_safe,
)


def detect_tactical_regime_hmm(df: pd.DataFrame, n_states: int = 4) -> pd.DataFrame:
    """DEPRECATED: Detect tactical regime via Hidden Markov Model.

    WARNING: This function fits HMM on the FULL dataset (train+OOS together).
    This LEAKS future information into past regime labels.

    Use fit_transform_split(train_df, oos_df) from regime_safe.py instead.

    States: trending_up, trending_down, ranging, crisis
    """
    warnings.warn(
        "detect_tactical_regime_hmm() fits HMM on full data (LEAKS FUTURE). "
        "Use fit_transform_split(train, oos) from data_pipeline.features.regime_safe instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    return _detect_tactical_regime_hmm_safe(df, n_states=n_states)


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


def compute_all_regime_features(df: pd.DataFrame, *, allow_leaky_hmm: bool = False) -> pd.DataFrame:
    """Compute all regime features (~40 features).

    FAIL-CLOSED BY DEFAULT: This function REFUSES to run leaky HMM unless explicitly allowed.

    Args:
        df: Full dataset DataFrame
        allow_leaky_hmm: If False (default), raises RuntimeError.
                        If True, allows leaky full-data HMM fit (DEPRECATED).

    Returns:
        DataFrame with regime features

    Raises:
        RuntimeError: If allow_leaky_hmm=False (default)

    RECOMMENDED SAFE USAGE:
        from data_pipeline.features.regime_safe import fit_transform_split
        train_regimes, oos_regimes = fit_transform_split(train_df, oos_df)
    """
    if not allow_leaky_hmm:
        raise RuntimeError(
            "compute_all_regime_features() fits HMM on FULL DATA (train+OOS together), "
            "which LEAKS future information into past regime labels. This is UNSAFE for backtest/research.\n\n"
            "For point-in-time safe regime features, use:\n"
            "    from data_pipeline.features.regime_safe import fit_transform_split\n"
            "    train_regimes, oos_regimes = fit_transform_split(train_df, oos_df)\n\n"
            "If you truly need legacy behavior (e.g., offline feature engineering with no backtest), "
            "pass allow_leaky_hmm=True."
        )

    warnings.warn(
        "compute_all_regime_features(allow_leaky_hmm=True) uses leaky HMM (fits on full data). "
        "For backtest/research, use fit_transform_split(train, oos) from regime_safe.py instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Tactical regime via HMM (LEAKY)
    tactical = detect_tactical_regime_hmm(df)

    # Micro regime (time-based, safe)
    micro = detect_micro_regime(df.index)

    # Duration and transition
    tactical["regime_duration"] = compute_regime_duration(tactical["regime_tactical"])
    tactical["regime_transition"] = compute_regime_transition(tactical["regime_tactical"])

    # Historical returns by regime
    hist_returns = compute_historical_return_by_regime(df, tactical["regime_tactical"])

    # Combine
    all_features = pd.concat([tactical, micro, hist_returns], axis=1)

    return all_features
