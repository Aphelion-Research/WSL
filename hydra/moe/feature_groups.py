"""Feature group definitions for HYDRA-MoE router and expert specialization."""

import numpy as np


ROUTER_FEATURES = [
    "vix_regime", "vol_regime", "trend_regime",
    "regime_crisis_prob", "regime_trend_up_prob",
    "atr_pct_14b", "realized_vol_144b", "parkinson_144b",
    "vol_zscore_60b", "vol_of_vol",
    "trend_efficiency_50b", "trend_efficiency_100b",
    "autocorr_1_lag60b", "hurst_100b",
    "adx_14", "di_plus_14", "di_minus_14",
    "sin_hour", "cos_hour", "is_london", "is_ny", "is_asia",
    "is_monday", "is_friday",
    "vix_z20d", "dxy_z20d", "corr_dxy_20d",
    "risk_on_composite", "dollar_composite",
    "spread_zscore", "spread_ratio",
    "amihud_288b", "kyle_lambda_144b",
]

EXPERT_FEATURE_PREFERENCES = {
    "trend_up": [
        "momentum", "ema_cross", "macd", "trend_efficiency",
        "cot_mm_long", "cot_mm_net", "gld_inflow",
        "log_ret_20b", "log_ret_50b",
    ],
    "trend_down": [
        "ema_cross", "adx", "breakdown", "dxy_ret",
        "real_yield_10y", "yield_2s10s", "tlt_ret",
        "log_ret_20b", "bear_streak",
    ],
    "mean_revert": [
        "zscore", "rsi", "bb_position", "drawdown", "drawup",
        "stoch", "williams_r", "cci", "autocorr",
    ],
    "crisis_vol": [
        "vix", "vpin", "amihud", "kyle_lambda",
        "spread", "vol_zscore", "parkinson", "garman_klass",
        "gvz", "realized_vol",
    ],
}

EXPERT_NAMES = ["trend_up", "trend_down", "mean_revert", "crisis_vol"]


def get_router_feature_indices(feature_cols: list[str]) -> np.ndarray:
    """Return column indices matching router feature names (fuzzy substring match).

    Args:
        feature_cols: Full list of feature column names.

    Returns:
        Array of integer indices into feature_cols for router-relevant features.
    """
    indices = []
    feature_cols_lower = [c.lower() for c in feature_cols]

    for router_feat in ROUTER_FEATURES:
        rf_lower = router_feat.lower()
        for i, col_lower in enumerate(feature_cols_lower):
            if rf_lower in col_lower or col_lower in rf_lower:
                if i not in indices:
                    indices.append(i)

    if not indices:
        # Fallback: use first 60 features as router features
        indices = list(range(min(60, len(feature_cols))))

    return np.array(sorted(indices), dtype=np.int64)


def get_expert_feature_boost(feature_cols: list[str], expert_name: str) -> np.ndarray:
    """Return boost weights for MI scoring — matched features get 1.5x.

    Args:
        feature_cols: Full list of feature column names.
        expert_name: One of EXPERT_NAMES.

    Returns:
        Float array of shape (n_features,) with 1.0 base and 1.5 for preferred features.
    """
    boost = np.ones(len(feature_cols), dtype=np.float32)
    prefs = EXPERT_FEATURE_PREFERENCES.get(expert_name, [])

    for i, col in enumerate(feature_cols):
        col_lower = col.lower()
        for pref in prefs:
            if pref.lower() in col_lower:
                boost[i] = 1.5
                break

    return boost
