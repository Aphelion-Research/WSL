"""Macro regime features from FRED data."""
import numpy as np
import pandas as pd
from typing import List
from datetime import datetime, timedelta

from data_pipeline.config import FEATURE_WINDOWS, FOMC_DATES_2026


def compute_real_yield_features(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute real yield features from TIPS."""
    features = pd.DataFrame()

    # Pivot macro data
    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    if "DFII10" not in macro_pivot.columns:
        return features

    real_yield = macro_pivot["DFII10"]

    features["real_yield_level"] = real_yield

    for w in [1, 5, 20]:
        features[f"real_yield_chg_{w}d"] = real_yield.diff(w)

    return features


def compute_yield_curve_features(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute yield curve features."""
    features = pd.DataFrame()

    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    # Slope (10Y - 2Y)
    if "T10Y2Y" in macro_pivot.columns:
        features["yield_curve_slope"] = macro_pivot["T10Y2Y"]
        features["yield_curve_slope_chg_20d"] = macro_pivot["T10Y2Y"].diff(20)

    # Alternative slope calculation
    if "DGS10" in macro_pivot.columns and "DGS2" in macro_pivot.columns:
        slope = macro_pivot["DGS10"] - macro_pivot["DGS2"]
        features["yield_slope_alt"] = slope

    return features


def compute_breakeven_features(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute breakeven inflation features."""
    features = pd.DataFrame()

    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    if "T10YIEM" not in macro_pivot.columns:
        return features

    breakeven = macro_pivot["T10YIEM"]

    features["breakeven_level"] = breakeven

    for w in [1, 5, 20]:
        features[f"breakeven_chg_{w}d"] = breakeven.diff(w)

    return features


def compute_dxy_momentum(macro_df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    """Compute dollar index momentum features."""
    if windows is None:
        windows = FEATURE_WINDOWS

    features = pd.DataFrame()

    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    if "DTWEXBGS" not in macro_pivot.columns:
        return features

    dxy = macro_pivot["DTWEXBGS"]

    for w in windows:
        features[f"dxy_mom_{w}"] = dxy.pct_change(w)
        features[f"dxy_zscore_{w}"] = (dxy - dxy.rolling(w).mean()) / (dxy.rolling(w).std() + 1e-10)

    return features


def compute_fed_features(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute Fed-related features."""
    features = pd.DataFrame()

    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    if "FEDFUNDS" not in macro_pivot.columns:
        return features

    fed_rate = macro_pivot["FEDFUNDS"]

    features["fed_rate"] = fed_rate
    features["fed_rate_chg_1m"] = fed_rate.diff(20)
    features["fed_rate_chg_3m"] = fed_rate.diff(60)

    return features


def compute_cpi_features(macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute CPI inflation features."""
    features = pd.DataFrame()

    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    if "CPIAUCSL" not in macro_pivot.columns:
        return features

    cpi = macro_pivot["CPIAUCSL"]

    # YoY change
    features["cpi_yoy"] = cpi.pct_change(252)

    # MoM change
    features["cpi_mom"] = cpi.pct_change(21)

    # Surprise vs previous month
    features["cpi_surprise"] = cpi.pct_change(21) - cpi.pct_change(21).shift(21)

    return features


def compute_fed_proximity(timestamps: pd.DatetimeIndex) -> pd.DataFrame:
    """Compute days until next Fed meeting."""
    features = pd.DataFrame(index=timestamps)

    fomc_dates = FOMC_DATES_2026

    days_to_fomc = []
    for ts in timestamps:
        # Find next FOMC date
        future_dates = [d for d in fomc_dates if d > ts]
        if future_dates:
            days_to_fomc.append((future_dates[0] - ts).days)
        else:
            days_to_fomc.append(np.nan)

    features["days_to_fomc"] = days_to_fomc

    return features


def compute_real_gold_price(gold_df: pd.DataFrame, macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute real gold price (gold / CPI)."""
    features = pd.DataFrame(index=gold_df.index)

    macro_pivot = macro_df.pivot(index='timestamp', columns='series_id', values='value')

    if "CPIAUCSL" not in macro_pivot.columns:
        return features

    # Merge gold and CPI
    merged = gold_df[["close"]].join(macro_pivot[["CPIAUCSL"]], how='left')
    merged = merged.ffill()

    # Real gold = nominal / (CPI / 100)
    features["real_gold"] = merged["close"] / (merged["CPIAUCSL"] / 100)

    return features


def compute_all_macro_features(gold_df: pd.DataFrame, macro_df: pd.DataFrame) -> pd.DataFrame:
    """Compute all macro features (~60 features)."""
    all_features = [
        compute_real_yield_features(macro_df),
        compute_yield_curve_features(macro_df),
        compute_breakeven_features(macro_df),
        compute_dxy_momentum(macro_df),
        compute_fed_features(macro_df),
        compute_cpi_features(macro_df),
        compute_fed_proximity(gold_df.index),
        compute_real_gold_price(gold_df, macro_df),
    ]

    # Reindex all to gold_df index
    result = pd.DataFrame(index=gold_df.index)
    for feat_df in all_features:
        if not feat_df.empty:
            result = result.join(feat_df, how='left')

    return result
