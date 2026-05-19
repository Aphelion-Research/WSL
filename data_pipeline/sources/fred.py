"""FRED (Federal Reserve Economic Data) source."""
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd

from data_pipeline.sources.base import DataSource
from data_pipeline.config import FRED_API_KEY, FRED_SERIES, FRED_YEARS


class FREDSource(DataSource):
    """FRED macro data source."""

    def __init__(self):
        super().__init__("fred")
        if not FRED_API_KEY:
            raise RuntimeError("FRED_API_KEY not set in environment")
        self.api_key = FRED_API_KEY
        self.series = FRED_SERIES

    def fetch(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch all FRED series using raw REST API."""
        import requests

        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * FRED_YEARS)

        all_data = []

        for series_id, series_name in self.series.items():
            try:
                # FRED REST API
                params = {
                    'series_id': series_id,
                    'api_key': self.api_key,
                    'file_type': 'json',
                    'observation_start': start_date.strftime('%Y-%m-%d'),
                    'observation_end': end_date.strftime('%Y-%m-%d'),
                    'limit': 10000,
                    'sort_order': 'asc'
                }

                url = 'https://api.stlouisfed.org/fred/series/observations'
                response = requests.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if 'observations' not in data:
                    self.mark_error(f"FRED API error for {series_id}: {data}")
                    continue

                observations = data['observations']
                records = []
                for obs in observations:
                    # Skip missing values (FRED uses '.' for missing data)
                    if obs['value'] == '.':
                        continue
                    try:
                        records.append({
                            'series_id': series_id,
                            'series_name': series_name,
                            'timestamp': pd.to_datetime(obs['date']),
                            'value': float(obs['value'])
                        })
                    except (ValueError, KeyError):
                        continue

                if not records:
                    self.mark_error(f"No valid data for series {series_id}")
                    continue

                df = pd.DataFrame(records)
                all_data.append(df)

            except Exception as e:
                self.mark_error(f"Failed to fetch {series_id}: {e}")

        if not all_data:
            raise RuntimeError("No FRED data fetched")

        df = pd.concat(all_data, ignore_index=True)

        if self.validate(df):
            self.mark_success()
            return df
        else:
            raise ValueError("Validation failed")

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate FRED data."""
        if df.empty:
            self.mark_error("Empty dataframe")
            return False

        # No NaN values
        if df["value"].isna().any():
            self.mark_error("NaN in values")
            return False

        return True
