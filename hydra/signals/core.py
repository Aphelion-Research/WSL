"""Three-brain fusion → final decision."""
from __future__ import annotations

import numpy as np

from hydra.config import ENSEMBLE


BRAIN_WEIGHTS = np.array([0.20, 0.35, 0.45])


def fuse_brains(
    s_scalp: np.ndarray,
    s_day: np.ndarray,
    s_swing: np.ndarray,
    weights: np.ndarray = BRAIN_WEIGHTS,
) -> np.ndarray:
    """Weighted sum of brain signals. Higher-TF dominant."""
    return weights[0] * s_scalp + weights[1] * s_day + weights[2] * s_swing


def agreement_multiplier(
    s_scalp: np.ndarray,
    s_day: np.ndarray,
    s_swing: np.ndarray,
) -> np.ndarray:
    """Compute sizing multiplier based on brain agreement."""
    n = len(s_scalp)
    mult = np.ones(n, dtype=np.float64)

    signs = np.stack([np.sign(s_scalp), np.sign(s_day), np.sign(s_swing)])
    combined_sign = np.sign(fuse_brains(s_scalp, s_day, s_swing))

    for i in range(n):
        agreeing = np.sum(signs[:, i] == combined_sign[i])
        if agreeing == 3:
            mult[i] = 2.0
        elif agreeing == 2:
            mult[i] = 1.0
        else:
            mult[i] = 0.5

    return mult


def conflict_resolution(
    s_scalp: np.ndarray,
    s_day: np.ndarray,
    s_swing: np.ndarray,
) -> np.ndarray:
    """If scalp and swing disagree on sign, flatten. Day breaks ties only if both neutral."""
    n = len(s_scalp)
    final = fuse_brains(s_scalp, s_day, s_swing)

    for i in range(n):
        scalp_sign = np.sign(s_scalp[i])
        swing_sign = np.sign(s_swing[i])
        if scalp_sign != 0 and swing_sign != 0 and scalp_sign != swing_sign:
            final[i] = 0.0

    return final


def five_gate_check(
    p_ensemble: float,
    p_causal: float,
    p_esn: float,
    p_moe: float,
    adversary_allows: bool,
    direction: int,
) -> bool:
    """All five gates must align for a signal to fire."""
    if direction == 1:
        return (
            p_ensemble > ENSEMBLE.long_threshold
            and p_causal > 0.55
            and p_esn > 0.55
            and p_moe > 0.55
            and adversary_allows
        )
    elif direction == -1:
        return (
            p_ensemble < ENSEMBLE.short_threshold
            and p_causal < 0.45
            and p_esn < 0.45
            and p_moe < 0.45
            and adversary_allows
        )
    return False
