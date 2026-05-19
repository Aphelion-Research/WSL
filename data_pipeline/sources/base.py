"""Abstract base class for data sources."""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from datetime import datetime


class DataSource(ABC):
    """Base class for all data sources."""

    def __init__(self, name: str):
        self.name = name
        self.last_fetch: Optional[datetime] = None
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.trust_score = 0.5  # Initial trust score for Kalman fusion

    @abstractmethod
    def fetch(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch data from source.

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        pass

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> bool:
        """Validate fetched data meets quality requirements."""
        pass

    def health(self) -> dict:
        """Return health status of this source."""
        return {
            "source": self.name,
            "last_fetch": self.last_fetch,
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    def mark_success(self) -> None:
        """Record successful fetch."""
        self.last_fetch = datetime.now()
        self.error_count = 0
        self.last_error = None

    def mark_error(self, error: str) -> None:
        """Record fetch error."""
        self.error_count += 1
        self.last_error = error
