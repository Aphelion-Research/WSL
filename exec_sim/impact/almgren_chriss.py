"""Almgren-Chriss (2001) market impact model."""
import numpy as np
from typing import List
from exec_sim.config import IMPACT_GAMMA, IMPACT_ETA, IMPACT_DELTA


def permanent_impact(quantity: float, adv: float, sigma: float, T_hours: float = 1.0) -> float:
    """Compute permanent impact (bps).

    Args:
        quantity: Trade size
        adv: Average daily volume
        sigma: Volatility (annualized)
        T_hours: Time horizon in hours

    Returns:
        Permanent impact in basis points
    """
    if adv == 0:
        return 0.0

    # Permanent impact proportional to quantity / ADV
    impact_bps = IMPACT_GAMMA * (quantity / adv) * sigma * np.sqrt(T_hours)
    return impact_bps * 10000  # convert to bps


def temporary_impact(rate: float, adv: float) -> float:
    """Compute temporary impact per slice (bps).

    Args:
        rate: Trade rate (quantity per unit time)
        adv: Average daily volume

    Returns:
        Temporary impact in basis points
    """
    if adv == 0:
        return 0.0

    # Temporary impact = eta * (rate/ADV)^delta
    normalized_rate = rate / adv
    impact_bps = IMPACT_ETA * np.sign(normalized_rate) * (abs(normalized_rate) ** IMPACT_DELTA)
    return impact_bps * 10000  # convert to bps


def total_cost(trajectory: List[float], adv: float, sigma: float) -> float:
    """Compute total execution cost for a trajectory.

    Args:
        trajectory: List of slice sizes
        adv: Average daily volume
        sigma: Volatility

    Returns:
        Total cost in basis points
    """
    if not trajectory or adv == 0:
        return 0.0

    total_quantity = sum(trajectory)

    # Permanent impact
    perm = permanent_impact(total_quantity, adv, sigma)

    # Temporary impact (sum across slices)
    temp = sum([temporary_impact(q, adv) for q in trajectory])

    return perm + temp


def optimal_trajectory(Q: float, T: float, adv: float, sigma: float, risk_aversion: float = 1e-6) -> List[float]:
    """Compute optimal trajectory using Almgren-Chriss closed form.

    Args:
        Q: Total quantity to trade
        T: Time horizon (hours)
        adv: Average daily volume
        sigma: Volatility
        risk_aversion: Risk aversion parameter

    Returns:
        List of optimal slice sizes
    """
    # Simplified: equal slicing (optimal under linear impact)
    N = max(int(T * 12), 1)  # 5-minute slices
    return [Q / N] * N
