"""Alpha Vantage data source."""
import time
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import requests

from data_pipeline.sources.base import DataSource
from data_pipeline.config import ALPHAVANTAGE_API_KEY, ALPHAVANTAGE_RATE_LIMIT_DELAY, ALPHAVANTAGE_SYMBOLS


class AlphaVantageSource(DataSource):
    """Alpha Vantage gold price source."""

    def __init__(self):
        super().__init__("alphavantage")
        if not ALPHAVANTAGE_API_KEY:
            raise RuntimeError("ALPHAVANTAGE_API_KEY not set in environment")
        self.api_key = ALPHAVANTAGE_API_KEY
        self.symbols = ALPHAVANTAGE_SYMBOLS
        self.base_url = "https://www.alphavantage.co/query"

    def fetch(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch gold OHLCV from Alpha Vantage."""
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 5)

        all_data = []

        for symbol in self.symbols:
            try:
                # TIME_SERIES_DAILY for GLD
                params = {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": "full",
                    "apikey": self.api_key,
                }

                response = requests.get(self.base_url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if "Time Series (Daily)" not in data:
                    self.mark_error(f"No daily data for {symbol}: {data.get('Note', data.get('Error Message', 'Unknown error'))}")
                    continue

                ts = data["Time Series (Daily)"]
                rows = []
                for date_str, values in ts.items():
                    rows.append({
                        "timestamp": pd.to_datetime(date_str),
                        "open": float(values["1. open"]),
                        "high": float(values["2. high"]),
                        "low": float(values["3. low"]),
                        "close": float(values["4. close"]),
                        "volume": float(values["5. volume"]),
                    })

                df = pd.DataFrame(rows)
                df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]
                all_data.append(df)

                # Rate limit delay (free tier: 25 req/day)
                time.sleep(ALPHAVANTAGE_RATE_LIMIT_DELAY)

            except Exception as e:
                self.mark_error(f"Failed to fetch {symbol}: {e}")

        if not all_data:
            raise RuntimeError("No data fetched from Alpha Vantage")

        df = pd.concat(all_data, ignore_index=True)
        df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")

        if self.validate(df):
            self.mark_success()
            return df
        else:
            raise ValueError("Validation failed")

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate Alpha Vantage data."""
        if df.empty:
            self.mark_error("Empty dataframe")
            return False

        # No NaN in close price
        if df["close"].isna().any():
            self.mark_error("NaN in close prices")
            return False

        # Price range check
        if (df["close"] < 50).any() or (df["close"] > 500).any():
            self.mark_error("Price outside realistic range for GLD ETF")
            return False

        return True
