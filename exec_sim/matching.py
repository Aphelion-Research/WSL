"""Order matching engine with partial fills."""
from typing import Tuple, Dict, List


def walk_book(price: float, size: float, book: List[Tuple[float, float]], side: str) -> Tuple[float, float, float]:
    """Walk the book to fill an order.

    Args:
        price: Limit price
        size: Order size
        book: List of (price, size) tuples
        side: 'buy' or 'sell'

    Returns:
        (avg_fill_price, filled_quantity, remaining_quantity)
    """
    if not book or size <= 0:
        return 0.0, 0.0, size

    filled = 0.0
    total_cost = 0.0
    remaining = size

    for level_price, level_size in book:
        # Check if we can trade at this level
        can_trade = (side == 'buy' and level_price <= price) or \
                    (side == 'sell' and level_price >= price)

        if not can_trade:
            break

        # Trade what's available
        trade_size = min(remaining, level_size)
        filled += trade_size
        total_cost += trade_size * level_price
        remaining -= trade_size

        if remaining <= 0:
            break

    avg_fill_price = total_cost / filled if filled > 0 else price
    return avg_fill_price, filled, remaining


def compute_slippage_bps(fill_price: float, mid_price: float, side: str) -> float:
    """Compute slippage in basis points.

    Args:
        fill_price: Actual fill price
        mid_price: Mid price at submission
        side: 'buy' or 'sell'

    Returns:
        Slippage in basis points (always positive)
    """
    if mid_price == 0:
        return 0.0

    if side == 'buy':
        slippage = (fill_price - mid_price) / mid_price
    else:
        slippage = (mid_price - fill_price) / mid_price

    return slippage * 10000  # to bps
