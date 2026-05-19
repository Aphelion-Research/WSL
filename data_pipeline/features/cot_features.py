"""COT (Commitments of Traders) positioning features."""
import numpy as np
import pandas as pd
from typing import List


def compute_cot_percentiles(cot_df: pd.DataFrame, windows: List[int] = [252, 504, 756]) -> pd.DataFrame:
    """Compute percentile ranks of COT positions.

    Args:
        cot_df: COT data with net_commercial and speculator_sentiment
        windows: Rolling windows for percentile calculation (1y, 2y, 3y)

    Returns:
        DataFrame with percentile features
    """
    features = pd.DataFrame(index=cot_df.index)

    for w in windows:
        # Net commercial percentile
        features[f"net_comm_pct_{w}"] = cot_df["net_commercial"].rolling(w).apply(
            lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100
        )

        # Speculator sentiment percentile
        features[f"spec_sent_pct_{w}"] = cot_df["speculator_sentiment"].rolling(w).apply(
            lambda x: (x.iloc[-1] <= x).sum() / len(x) * 100
        )

    return features


def compute_cot_momentum(cot_df: pd.DataFrame, windows: List[int] = [4, 8, 12]) -> pd.DataFrame:
    """Compute COT positioning momentum (change over N weeks)."""
    features = pd.DataFrame(index=cot_df.index)

    for w in windows:
        features[f"net_comm_mom_{w}w"] = cot_df["net_commercial"].diff(w)
        features[f"spec_sent_mom_{w}w"] = cot_df["speculator_sentiment"].diff(w)
        features[f"oi_mom_{w}w"] = cot_df["open_interest"].pct_change(w)

    return features


def compute_hedger_ratio(cot_df: pd.DataFrame) -> pd.DataFrame:
    """Compute commercial hedger ratio."""
    features = pd.DataFrame(index=cot_df.index)

    features["hedger_ratio"] = (
        (cot_df["commercial_long"] + cot_df["commercial_short"]) /
        (cot_df["open_interest"] + 1e-10)
    )

    return features


def compute_spec_concentration(cot_df: pd.DataFrame) -> pd.DataFrame:
    """Compute large speculator concentration."""
    features = pd.DataFrame(index=cot_df.index)

    features["spec_concentration"] = (
        (cot_df["noncommercial_long"] + cot_df["noncommercial_short"]) /
        (cot_df["open_interest"] + 1e-10)
    )

    return features


def compute_oi_features(cot_df: pd.DataFrame, windows: List[int] = [52, 104]) -> pd.DataFrame:
    """Compute open interest features."""
    features = pd.DataFrame(index=cot_df.index)

    features["oi_change"] = cot_df["open_interest"].diff()

    for w in windows:
        features[f"oi_vs_avg_{w}w"] = (
            cot_df["open_interest"] / (cot_df["open_interest"].rolling(w).mean() + 1e-10) - 1
        )

    return features


def compute_all_cot_features(cot_df: pd.DataFrame) -> pd.DataFrame:
    """Compute all COT features (~30 features)."""
    all_features = [
        compute_cot_percentiles(cot_df),
        compute_cot_momentum(cot_df),
        compute_hedger_ratio(cot_df),
        compute_spec_concentration(cot_df),
        compute_oi_features(cot_df),
    ]

    return pd.concat(all_features, axis=1)
