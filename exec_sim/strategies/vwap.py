"""VWAP execution strategy."""
import pandas as pd
from typing import List, Dict
from exec_sim.strategies.base import ExecutionStrategy


class VWAPStrategy(ExecutionStrategy):
    """Volume-Weighted Average Price strategy.

    Slices orders proportionally to historical volume profile.
    """

    def generate_slices(self, market_data: pd.DataFrame) -> List[Dict]:
        """Generate VWAP slices.

        Args:
            market_data: DataFrame with 'timestamp', 'volume' columns

        Returns:
            List of order slices
        """
        # Filter to execution window
        window = market_data[
            (market_data['timestamp'] >= self.start_time) &
            (market_data['timestamp'] <= self.end_time)
        ].copy()

        if window.empty:
            # Fallback: single order
            return [{
                'time': self.start_time,
                'quantity': self.target_quantity,
                'price': None  # market order
            }]

        # Compute volume profile
        if 'volume' in window.columns:
            window['volume_frac'] = window['volume'] / window['volume'].sum()
        else:
            # Equal weighting if no volume data
            window['volume_frac'] = 1.0 / len(window)

        # Generate slices
        slices = []
        for _, row in window.iterrows():
            slice_qty = self.target_quantity * row['volume_frac']
            if slice_qty > 0:
                slices.append({
                    'time': row['timestamp'],
                    'quantity': slice_qty,
                    'price': None
                })

        return slices
