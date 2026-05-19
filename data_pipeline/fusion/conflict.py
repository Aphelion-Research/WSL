"""Conflict resolution and anomaly detection for multi-source fusion."""
import numpy as np
from typing import Dict, Tuple, Optional


def resolve_conflict(
    observations: Dict[str, float],
    fused_price: float,
    confidence: float,
    trust_scores: Dict[str, float],
) -> Tuple[float, bool, Optional[str]]:
    """Resolve conflicts between sources.

    Args:
        observations: Dict mapping source -> price
        fused_price: Current fused price estimate
        confidence: Current confidence estimate
        trust_scores: Current trust scores for each source

    Returns:
        (final_price, quarantine_flag, quarantined_source)
    """
    if len(observations) < 2:
        return fused_price, False, None

    # Compute standard deviation
    prices = list(observations.values())
    std = np.std(prices)

    # Check agreement within 0.05%
    if std / fused_price < 0.0005:
        # All sources agree -> use volume-weighted mean (approximated by fused price)
        return fused_price, False, None

    # Check for outliers
    quarantine_source = None
    quarantine_flag = False

    for source, price in observations.items():
        deviation = abs(price - fused_price)
        sigma = np.sqrt(1.0 / max(confidence, 0.01))

        if deviation > 3.0 * sigma:
            # Source diverges >3σ -> quarantine
            quarantine_source = source
            quarantine_flag = True
            break
        elif deviation > 1.0 * sigma:
            # Source diverges >1σ -> downweight implicitly via trust system
            pass

    # Byzantine fault tolerance: require 3+ sources agreeing
    if len(observations) >= 3:
        # Find majority (median-based)
        median_price = np.median(prices)
        agreeing_sources = [s for s, p in observations.items() if abs(p - median_price) < sigma]

        if len(agreeing_sources) >= 3:
            # Majority agrees -> use their weighted mean
            agreeing_prices = [observations[s] * trust_scores.get(s, 0.5) for s in agreeing_sources]
            agreeing_weights = [trust_scores.get(s, 0.5) for s in agreeing_sources]
            final_price = sum(agreeing_prices) / sum(agreeing_weights)
            return final_price, quarantine_flag, quarantine_source

    return fused_price, quarantine_flag, quarantine_source


def detect_anomaly(
    price: float,
    historical_mean: float,
    historical_std: float,
    z_threshold: float = 3.0,
) -> Tuple[bool, float]:
    """Detect price anomaly via z-score.

    Args:
        price: Current price
        historical_mean: Rolling mean
        historical_std: Rolling std
        z_threshold: Z-score threshold for anomaly

    Returns:
        (is_anomaly, z_score)
    """
    if historical_std > 0:
        z_score = abs(price - historical_mean) / historical_std
    else:
        z_score = 0.0

    return z_score > z_threshold, z_score
