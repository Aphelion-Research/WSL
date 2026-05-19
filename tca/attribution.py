"""Cost attribution logic."""
from typing import Dict


def compute_attribution(
    decision_price: float,
    arrival_price: float,
    avg_fill_price: float,
    quantity_target: float,
    quantity_filled: float,
    pre_trade_mid: float,
    close_price: float,
    side: str
) -> Dict[str, float]:
    """Decompose execution cost into components.

    Args:
        decision_price: Price at decision time
        arrival_price: Price at first fill
        avg_fill_price: Average fill price
        quantity_target: Target quantity
        quantity_filled: Actual filled quantity
        pre_trade_mid: Mid price 5 bars before decision
        close_price: Close price at end of window
        side: 'buy' or 'sell'

    Returns:
        Dict with cost components in bps
    """
    side_mult = 1.0 if side == 'buy' else -1.0

    # Decision cost: (decision_price - pre_trade_mid) / pre_trade_mid
    decision_cost_bps = side_mult * (decision_price - pre_trade_mid) / pre_trade_mid * 10000

    # Timing cost: (arrival_price - decision_price) / decision_price
    timing_cost_bps = side_mult * (arrival_price - decision_price) / decision_price * 10000

    # Impact cost: (avg_fill_price - arrival_price) / arrival_price
    impact_cost_bps = side_mult * (avg_fill_price - arrival_price) / arrival_price * 10000

    # Opportunity cost: unfilled quantity × price drift
    unfilled_qty = quantity_target - quantity_filled
    if quantity_target > 0:
        unfilled_pct = unfilled_qty / quantity_target
    else:
        unfilled_pct = 0.0

    price_drift = side_mult * (close_price - arrival_price) / arrival_price
    opportunity_cost_bps = unfilled_pct * price_drift * 10000

    # Total cost
    total_cost_bps = decision_cost_bps + timing_cost_bps + impact_cost_bps + opportunity_cost_bps

    return {
        'decision_cost_bps': decision_cost_bps,
        'timing_cost_bps': timing_cost_bps,
        'impact_cost_bps': impact_cost_bps,
        'opportunity_cost_bps': opportunity_cost_bps,
        'total_cost_bps': total_cost_bps
    }
