"""40+ improvement strategies for the autonomous loop."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Strategy:
    name: str
    priority: int
    description: str
    apply: Callable[..., dict]


def threshold_tuning(ctx: dict) -> dict:
    """Grid search over long/short thresholds."""
    import numpy as np
    best_sharpe = ctx.get("sharpe", 0)
    best_params = {"long_threshold": 0.60, "short_threshold": 0.40}
    for lt in np.arange(0.55, 0.66, 0.02):
        for st in np.arange(0.35, 0.46, 0.02):
            ctx["ensemble_config_override"] = {"long_threshold": lt, "short_threshold": st}
    return {"action": "threshold_tuning", "params": best_params}


def refit_bma(ctx: dict) -> dict:
    return {"action": "refit_bma"}


def add_boosting_rounds(ctx: dict) -> dict:
    return {"action": "add_boosting_rounds", "n_rounds": 100}


def rerun_feature_selection(ctx: dict) -> dict:
    return {"action": "rerun_feature_selection"}


def toggle_pe_filter(ctx: dict) -> dict:
    delta = 0.02 if ctx.get("pe_direction", "up") == "up" else -0.02
    return {"action": "toggle_pe_filter", "delta": delta}


def refit_hmm(ctx: dict) -> dict:
    return {"action": "refit_hmm", "n_components": [3, 4, 5]}


def refit_moe_gate(ctx: dict) -> dict:
    return {"action": "refit_moe_gate"}


def esn_sweep(ctx: dict) -> dict:
    return {"action": "esn_sweep", "radii": [0.4, 0.5, 0.6]}


def retrain_adversary(ctx: dict) -> dict:
    return {"action": "retrain_adversary"}


def increase_kelly(ctx: dict) -> dict:
    return {"action": "increase_kelly", "new_frac": 0.30}


def add_lagged_interactions(ctx: dict) -> dict:
    return {"action": "add_lagged_interactions", "lags": [1, 5, 20]}


def refit_gat(ctx: dict) -> dict:
    return {"action": "refit_gat", "extra_epochs": 1}


def swap_lr_cv(ctx: dict) -> dict:
    return {"action": "swap_lr_cv"}


def refit_scaler(ctx: dict) -> dict:
    return {"action": "refit_scaler", "quantile_range": (10, 90)}


def enable_neural(ctx: dict) -> dict:
    return {"action": "enable_neural"}


def increase_seq_len(ctx: dict) -> dict:
    return {"action": "increase_seq_len", "new_len": 90}


def add_channel_features(ctx: dict) -> dict:
    return {"action": "add_channel_features", "indicators": ["bollinger_pctb", "keltner_pos", "donchian_pos"]}


def add_vwap_deviation(ctx: dict) -> dict:
    return {"action": "add_vwap_deviation"}


def refit_causal_dag(ctx: dict) -> dict:
    return {"action": "refit_causal_dag", "alphas": [0.01, 0.05]}


def bump_ragd_k(ctx: dict) -> dict:
    return {"action": "bump_ragd_k", "new_k": 20}


def add_transfer_entropy(ctx: dict) -> dict:
    return {"action": "add_transfer_entropy", "source": "DXY"}


def asymmetric_thresholds(ctx: dict) -> dict:
    return {"action": "asymmetric_thresholds"}


def per_regime_kelly(ctx: dict) -> dict:
    return {"action": "per_regime_kelly"}


def expand_moe_window(ctx: dict) -> dict:
    return {"action": "expand_moe_window", "mult": 2}


def add_time_features(ctx: dict) -> dict:
    return {"action": "add_time_features"}


def vol_weighted_training(ctx: dict) -> dict:
    return {"action": "vol_weighted_training"}


def drop_outlier_spread(ctx: dict) -> dict:
    return {"action": "drop_outlier_spread", "mad_mult": 3}


def noise_injection(ctx: dict) -> dict:
    return {"action": "noise_injection", "sigma": 0.01}


def bag_meta_learner(ctx: dict) -> dict:
    return {"action": "bag_meta_learner", "n_bags": 10}


def lgbm_stacker(ctx: dict) -> dict:
    return {"action": "lgbm_stacker", "depth": 3, "rounds": 200}


def combinatorial_cv(ctx: dict) -> dict:
    return {"action": "combinatorial_cv", "groups": 8, "choose": 2}


def tighten_embargo(ctx: dict) -> dict:
    return {"action": "tighten_embargo", "new_embargo": 20}


def monotonic_constraints(ctx: dict) -> dict:
    return {"action": "monotonic_constraints", "features": ["rsi", "atr", "cot_net"]}


def causal_only_features(ctx: dict) -> dict:
    return {"action": "causal_only_features"}


def adversarial_weighting(ctx: dict) -> dict:
    return {"action": "adversarial_weighting"}


def vol_targeting(ctx: dict) -> dict:
    return {"action": "vol_targeting"}


def trailing_stop_step(ctx: dict) -> dict:
    return {"action": "trailing_stop_step", "trigger_atr": 1.5, "lock_atr": 0.5}


def time_filter(ctx: dict) -> dict:
    return {"action": "time_filter"}


def correlation_gate(ctx: dict) -> dict:
    return {"action": "correlation_gate"}


def add_extra_trees(ctx: dict) -> dict:
    return {"action": "add_extra_trees", "n_extra": 2}


STRATEGY_LADDER: list[Strategy] = [
    Strategy("threshold_tuning", 1, "Grid search long/short thresholds", threshold_tuning),
    Strategy("refit_bma", 2, "Re-fit BMA weights from val Sharpes", refit_bma),
    Strategy("add_boosting_rounds", 3, "Add 100 more rounds to GBMs", add_boosting_rounds),
    Strategy("rerun_feature_selection", 4, "Re-pick top-200 MI ∩ IC>=0.015", rerun_feature_selection),
    Strategy("toggle_pe_filter", 5, "Adjust PE gate strictness ±0.02", toggle_pe_filter),
    Strategy("refit_hmm", 6, "Re-fit HMM with n∈{3,4,5}", refit_hmm),
    Strategy("refit_moe_gate", 7, "Re-fit MoE gating weights", refit_moe_gate),
    Strategy("esn_sweep", 8, "ESN spectral-radius sweep", esn_sweep),
    Strategy("retrain_adversary", 9, "Re-train HYDRA-ADVERSARY", retrain_adversary),
    Strategy("increase_kelly", 10, "Bump kelly_frac 0.25→0.30", increase_kelly),
    Strategy("add_lagged_interactions", 11, "Top-5 features × lags", add_lagged_interactions),
    Strategy("refit_gat", 12, "GAT extra epoch", refit_gat),
    Strategy("swap_lr_cv", 13, "Replace LR with LogisticRegressionCV", swap_lr_cv),
    Strategy("refit_scaler", 14, "Scaler quantile (10,90)", refit_scaler),
    Strategy("enable_neural", 15, "Enable LSTM/TCN if PyTorch present", enable_neural),
    Strategy("increase_seq_len", 16, "seq_len 60→90", increase_seq_len),
    Strategy("add_channel_features", 17, "Bollinger/Keltner/Donchian", add_channel_features),
    Strategy("add_vwap_deviation", 18, "Intraday VWAP deviation", add_vwap_deviation),
    Strategy("refit_causal_dag", 19, "Causal DAG α∈{0.01,0.05}", refit_causal_dag),
    Strategy("bump_ragd_k", 20, "RAGD k: 10→20", bump_ragd_k),
    Strategy("add_transfer_entropy", 21, "DXY→XAU transfer entropy", add_transfer_entropy),
    Strategy("asymmetric_thresholds", 22, "Per-regime thresholds", asymmetric_thresholds),
    Strategy("per_regime_kelly", 23, "Lower Kelly in crisis", per_regime_kelly),
    Strategy("expand_moe_window", 24, "2× MoE training window", expand_moe_window),
    Strategy("add_time_features", 25, "Hour/DOW dummies", add_time_features),
    Strategy("vol_weighted_training", 26, "sample_weight=1/vol", vol_weighted_training),
    Strategy("drop_outlier_spread", 27, "Drop bars with spread>3×MAD", drop_outlier_spread),
    Strategy("noise_injection", 28, "Gaussian noise σ=0.01", noise_injection),
    Strategy("bag_meta_learner", 29, "10 bootstrap LRs", bag_meta_learner),
    Strategy("lgbm_stacker", 30, "LightGBM meta-learner", lgbm_stacker),
    Strategy("combinatorial_cv", 31, "CPCV (8 groups, choose 2)", combinatorial_cv),
    Strategy("tighten_embargo", 32, "Embargo 10→20 bars", tighten_embargo),
    Strategy("monotonic_constraints", 33, "RSI/ATR/COT monotonic", monotonic_constraints),
    Strategy("causal_only_features", 34, "Restrict to causal upstream", causal_only_features),
    Strategy("adversarial_weighting", 35, "Down-weight ADVERSARY-flagged", adversarial_weighting),
    Strategy("vol_targeting", 36, "Vol-targeting overlay", vol_targeting),
    Strategy("trailing_stop_step", 37, "Trail at +1.5ATR lock 0.5", trailing_stop_step),
    Strategy("time_filter", 38, "Disable scalp in overlap", time_filter),
    Strategy("correlation_gate", 39, "XAU-DXY correlation flip", correlation_gate),
    Strategy("add_extra_trees", 40, "2× ExtraTrees different seeds", add_extra_trees),
]


def get_strategy(index: int) -> Strategy:
    """Get strategy by 0-based index, wrapping around."""
    return STRATEGY_LADDER[index % len(STRATEGY_LADDER)]
