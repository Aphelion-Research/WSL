"""TWAP execution strategy."""
import pandas as pd
from typing import List, Dict
from exec_sim.strategies.base import ExecutionStrategy
from exec_sim.config import DEFAULT_SLICE_INTERVAL_MIN


class TWAPStrategy(ExecutionStrategy):
    """Time-Weighted Average Price strategy.

    Splits order into equal slices over time.
    """

    def __init__(self, target_quantity: float, start_time: pd.Timestamp, end_time: pd.Timestamp,
                 slice_interval_min: int = DEFAULT_SLICE_INTERVAL_MIN):
        """Initialize TWAP strategy.

        Args:
            target_quantity: Total quantity
            start_time: Start timestamp
            end_time: End timestamp
            slice_interval_min: Minutes between slices
        """
        super().__init__(target_quantity, start_time, end_time)
        self.slice_interval_min = slice_interval_min

    def generate_slices(self, market_data: pd.DataFrame) -> List[Dict]:
        """Generate TWAP slices.

        Args:
            market_data: Market data (unused for TWAP)

        Returns:
            List of equal-sized order slices
        """
        # Compute number of slices
        duration_min = (self.end_time - self.start_time).total_seconds() / 60
        n_slices = max(int(duration_min / self.slice_interval_min), 1)
        slice_qty = self.target_quantity / n_slices

        # Generate slice times
        slices = []
        for i in range(n_slices):
            slice_time = self.start_time + pd.Timedelta(minutes=i * self.slice_interval_min)
            slices.append({
                'time': slice_time,
                'quantity': slice_qty,
                'price': None
            })

        return slices
