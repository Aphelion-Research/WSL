"""Cross-asset correlation and lead-lag features."""
import numpy as np
import pandas as pd
from typing import Dict, List
from statsmodels.tsa.stattools import grangercausalitytests

from data_pipeline.config import FEATURE_WINDOWS


def compute_rolling_correlation(
    gold: pd.Series,
    other: pd.Series,
    windows: List[int] = None
) -> pd.DataFrame:
    """Compute rolling correlation between gold and another asset."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=gold.index)
    name = other.name if hasattr(other, 'name') else 'other'

    for w in windows:
        features[f"corr_{name}_{w}"] = gold.rolling(w).corr(other)

    return features


def compute_rolling_beta(
    gold: pd.Series,
    other: pd.Series,
    windows: List[int] = None
) -> pd.DataFrame:
    """Compute rolling beta of gold vs other asset."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame(index=gold.index)
    name = other.name if hasattr(other, 'name') else 'other'

    for w in windows:
        cov = gold.rolling(w).cov(other)
        var = other.rolling(w).var()
        features[f"beta_{name}_{w}"] = cov / (var + 1e-10)

    return features


def compute_lead_lag(
    gold: pd.Series,
    other: pd.Series,
    lags: List[int] = [-5, -3, -1, 0, 1, 3, 5],
    window: int = 252
) -> pd.DataFrame:
    """Compute lead-lag correlation at different lags."""
    features = pd.DataFrame(index=gold.index)
    name = other.name if hasattr(other, 'name') else 'other'

    for lag in lags:
        if lag < 0:
            # Gold lags other (other leads gold)
            shifted = other.shift(-lag)
            col_name = f"leadlag_{name}_m{abs(lag)}"
        elif lag > 0:
            # Gold leads other
            shifted = other.shift(lag)
            col_name = f"leadlag_{name}_p{lag}"
        else:
            shifted = other
            col_name = f"leadlag_{name}_0"

        features[col_name] = gold.rolling(window).corr(shifted)

    return features


def compute_granger(
    gold: pd.Series,
    other: pd.Series,
    maxlag: int = 5,
    window: int = 252
) -> pd.DataFrame:
    """Compute rolling Granger causality p-value."""
    features = pd.DataFrame(index=gold.index)
    name = other.name if hasattr(other, 'name') else 'other'

    p_values = []
    for i in range(len(gold)):
        if i < window:
            p_values.append(np.nan)
        else:
            gold_window = gold.iloc[i - window:i].values
            other_window = other.iloc[i - window:i].values

            # Create dataframe for Granger test
            data = pd.DataFrame({'gold': gold_window, 'other': other_window})

            try:
                result = grangercausalitytests(data[['gold', 'other']], maxlag=maxlag, verbose=False)
                # Get minimum p-value across lags
                min_p = min([result[lag][0]['ssr_ftest'][1] for lag in range(1, maxlag + 1)])
                p_values.append(min_p)
            except:
                p_values.append(np.nan)

    features[f"granger_{name}_{window}"] = p_values
    return features


def compute_partial_correlation(
    gold: pd.Series,
    other: pd.Series,
    control: pd.Series,
    window: int = 252
) -> pd.DataFrame:
    """Compute partial correlation controlling for control variable."""
    features = pd.DataFrame(index=gold.index)
    name = other.name if hasattr(other, 'name') else 'other'
    control_name = control.name if hasattr(control, 'name') else 'control'

    partial_corr = []
    for i in range(len(gold)):
        if i < window:
            partial_corr.append(np.nan)
        else:
            g = gold.iloc[i - window:i].values
            o = other.iloc[i - window:i].values
            c = control.iloc[i - window:i].values

            # Partial correlation formula
            r_go = np.corrcoef(g, o)[0, 1]
            r_gc = np.corrcoef(g, c)[0, 1]
            r_oc = np.corrcoef(o, c)[0, 1]

            if not np.isnan(r_go) and not np.isnan(r_gc) and not np.isnan(r_oc):
                pcorr = (r_go - r_gc * r_oc) / (np.sqrt((1 - r_gc ** 2) * (1 - r_oc ** 2)) + 1e-10)
            else:
                pcorr = np.nan

            partial_corr.append(pcorr)

    features[f"partial_corr_{name}_ctrl{control_name}_{window}"] = partial_corr
    return features


def compute_all_crossasset_features(
    gold_df: pd.DataFrame,
    macro_df: pd.DataFrame
) -> pd.DataFrame:
    """Compute all cross-asset features (~100 features).

    Args:
        gold_df: Gold price dataframe
        macro_df: Macro data with series_id column

    Returns:
        DataFrame with cross-asset features
    """
    all_features = []

    gold_returns = gold_df["close"].pct_change()

    # Pivot macro data
    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    # Merge with gold
    merged = gold_df[["close"]].join(macro_pivot, how='left')
    merged = merged.fillna(method='ffill').fillna(method='bfill')

    # Compute features for each macro series
    for series_id in macro_pivot.columns:
        if series_id not in merged.columns:
            continue

        series = merged[series_id]
        series.name = series_id

        # Correlation
        all_features.append(compute_rolling_correlation(gold_returns, series))

        # Beta
        all_features.append(compute_rolling_beta(gold_returns, series))

        # Lead-lag
        all_features.append(compute_lead_lag(gold_returns, series))

        # Granger causality (computationally expensive, use sparingly)
        if series_id in ["DGS10", "DTWEXBGS", "VIXCLS"]:
            all_features.append(compute_granger(gold_returns, series))

        # Partial correlation controlling for DXY
        if "DTWEXBGS" in merged.columns and series_id != "DTWEXBGS":
            dxy = merged["DTWEXBGS"]
            dxy.name = "DXY"
            all_features.append(compute_partial_correlation(gold_returns, series, dxy))

    return pd.concat(all_features, axis=1)
