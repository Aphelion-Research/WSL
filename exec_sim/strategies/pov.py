"""POV (Participation of Volume) execution strategy."""
import pandas as pd
from typing import List, Dict
from exec_sim.strategies.base import ExecutionStrategy
from exec_sim.config import DEFAULT_POV_TARGET


class POVStrategy(ExecutionStrategy):
    """Participation of Volume strategy.

    Trades a target percentage of market volume.
    """

    def __init__(self, target_quantity: float, start_time: pd.Timestamp, end_time: pd.Timestamp,
                 pov_rate: float = DEFAULT_POV_TARGET):
        """Initialize POV strategy.

        Args:
            target_quantity: Total quantity
            start_time: Start timestamp
            end_time: End timestamp
            pov_rate: Target participation rate (0.10 = 10%)
        """
        super().__init__(target_quantity, start_time, end_time)
        self.pov_rate = pov_rate

    def generate_slices(self, market_data: pd.DataFrame) -> List[Dict]:
        """Generate POV slices.

        Args:
            market_data: DataFrame with 'timestamp', 'volume'

        Returns:
            List of order slices
        """
        # Filter to execution window
        window = market_data[
            (market_data['timestamp'] >= self.start_time) &
            (market_data['timestamp'] <= self.end_time)
        ].copy()

        if window.empty or 'volume' not in window.columns:
            # Fallback: single market order
            return [{
                'time': self.start_time,
                'quantity': self.target_quantity,
                'price': None
            }]

        # Generate slices proportional to market volume
        slices = []
        cumulative_filled = 0.0

        for _, row in window.iterrows():
            market_vol = row['volume']
            slice_qty = market_vol * self.pov_rate

            # Cap at remaining quantity
            slice_qty = min(slice_qty, self.target_quantity - cumulative_filled)

            if slice_qty > 0:
                slices.append({
                    'time': row['timestamp'],
                    'quantity': slice_qty,
                    'price': None
                })
                cumulative_filled += slice_qty

            if cumulative_filled >= self.target_quantity:
                break

        return slices
