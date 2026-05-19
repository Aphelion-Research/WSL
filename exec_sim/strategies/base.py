"""Base execution strategy."""
from abc import ABC, abstractmethod
from typing import List, Dict
import pandas as pd


class ExecutionStrategy(ABC):
    """Abstract base class for execution strategies."""

    def __init__(self, target_quantity: float, start_time: pd.Timestamp, end_time: pd.Timestamp):
        """Initialize strategy.

        Args:
            target_quantity: Total quantity to execute
            start_time: Start timestamp
            end_time: End timestamp
        """
        self.target_quantity = target_quantity
        self.start_time = start_time
        self.end_time = end_time
        self.filled_quantity = 0.0
        self.orders = []

    @abstractmethod
    def generate_slices(self, market_data: pd.DataFrame) -> List[Dict]:
        """Generate child order slices.

        Args:
            market_data: Historical market data

        Returns:
            List of order dicts with 'time', 'quantity', 'price'
        """
        pass

    @property
    def remaining_quantity(self) -> float:
        """Get remaining quantity."""
        return self.target_quantity - self.filled_quantity
