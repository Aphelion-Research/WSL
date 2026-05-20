"""Tradeability filters: permutation entropy, COT, toxicity, spread."""
from __future__ import annotations

import numpy as np

from hydra.config import ENSEMBLE, BACKTEST


def permutation_entropy_gate(
    close: np.ndarray,
    window: int = 100,
    order: int = 3,
    max_pe: float = ENSEMBLE.pe_max,
) -> np.ndarray:
    """Returns boolean mask: True where trading is allowed."""
    n = len(close)
    allowed = np.ones(n, dtype=bool)

    for i in range(window, n):
        segment = close[i - window:i]
        pe = _perm_entropy(segment, order=order)
        if pe > max_pe:
            allowed[i] = False

    return allowed


def _perm_entropy(x: np.ndarray, order: int = 3) -> float:
    """Normalised permutation entropy."""
    import math
    n = len(x)
    if n < order + 1:
        return 1.0

    from itertools import permutations
    n_perms = math.factorial(order)
    counts = {}

    for i in range(n - order):
        segment = x[i:i + order]
        perm = tuple(np.argsort(segment))
        counts[perm] = counts.get(perm, 0) + 1

    total = sum(counts.values())
    entropy = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            entropy -= p * math.log(p)

    max_entropy = math.log(n_perms)
    if max_entropy == 0:
        return 0.0
    return entropy / max_entropy


def cot_filter(
    comm_long: np.ndarray,
    comm_short: np.ndarray,
    oi_total: np.ndarray,
    threshold: float = 0.35,
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (allow_long, allow_short) boolean masks."""
    n = len(comm_long)
    allow_long = np.ones(n, dtype=bool)
    allow_short = np.ones(n, dtype=bool)

    comm_net_short = comm_short / np.where(oi_total > 0, oi_total, 1.0)
    comm_net_long = comm_long / np.where(oi_total > 0, oi_total, 1.0)

    allow_long[comm_net_short > threshold] = False
    allow_short[comm_net_long > threshold] = False

    return allow_long, allow_short


def toxicity_gate(toxicity_scores: np.ndarray, max_tox: float = 0.7) -> np.ndarray:
    """Returns boolean mask: True where toxicity is acceptable."""
    return toxicity_scores <= max_tox


def spread_gate(
    realised_spread: np.ndarray,
    max_mult: float = 2.0,
    nominal_spread: float = BACKTEST.spread_pips,
) -> np.ndarray:
    """Block when realised spread exceeds threshold."""
    return realised_spread <= max_mult * nominal_spread
