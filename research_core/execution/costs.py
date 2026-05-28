"""Cost models for execution simulation."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class CostModel:
    """Transaction cost model.

    All costs are in price units (e.g., USD for XAU/USD).
    """

    spread_points: float = 0.0  # Bid-ask spread in points (e.g., 0.30)
    slippage_points: float = 0.0  # Additional slippage per side
    commission_per_lot: float = 0.0  # Commission per lot (e.g., $7)
    lot_size: float = 100.0  # Ounces per lot (100 oz for XAU/USD)

    @classmethod
    def xauusd_baseline(cls) -> "CostModel":
        """Baseline XAU/USD costs (conservative)."""
        return cls(
            spread_points=0.30,
            slippage_points=0.10,
            commission_per_lot=7.0,
            lot_size=100.0,
        )

    def scale(self, factor: float) -> "CostModel":
        """Return scaled cost model.

        Args:
            factor: Cost multiplier (e.g., 0.5 for half costs, 2.0 for double)
        """
        return CostModel(
            spread_points=self.spread_points * factor,
            slippage_points=self.slippage_points * factor,
            commission_per_lot=self.commission_per_lot * factor,
            lot_size=self.lot_size,
        )


def compute_total_cost(
    entry_price: float,
    exit_price: float,
    direction: int,  # 1 for long, -1 for short
    position_size_oz: float,
    cost_model: CostModel,
) -> float:
    """Compute total round-trip transaction cost.

    Args:
        entry_price: Entry price
        exit_price: Exit price
        direction: 1 for long, -1 for short
        position_size_oz: Position size in ounces
        cost_model: Cost model

    Returns:
        Total cost in USD (positive = cost, reduces PnL)
    """
    # Spread cost: pay half-spread on entry and exit
    spread_cost = cost_model.spread_points * 2

    # Slippage cost: additional slippage on entry and exit
    slippage_cost = cost_model.slippage_points * 2

    # Total price cost
    price_cost = spread_cost + slippage_cost

    # Cost in USD = cost in points * position size
    cost_usd = price_cost * position_size_oz

    # Commission cost
    lots = position_size_oz / cost_model.lot_size
    commission_cost = cost_model.commission_per_lot * lots * 2  # round-trip

    return cost_usd + commission_cost
