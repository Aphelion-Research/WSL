"""Yahoo Finance data source via yfinance."""
import time
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from data_pipeline.sources.base import DataSource
from data_pipeline.config import YAHOO_TICKERS, YAHOO_DAILY_PERIOD, YAHOO_HOURLY_PERIOD


class YahooSource(DataSource):
    """Yahoo Finance gold price source (GC=F futures + GLD ETF)."""

    def __init__(self):
        super().__init__("yahoo")
        self.tickers = YAHOO_TICKERS
        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def fetch(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch gold OHLCV from Yahoo Finance."""
        try:
            import yfinance as yf
        except ImportError:
            raise RuntimeError("yfinance not installed: pip install yfinance")

        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 5)

        all_data = []

        for ticker in self.tickers:
            for attempt in range(self.max_retries):
                try:
                    yfobj = yf.Ticker(ticker)

                    # Fetch daily data
                    df_daily = yfobj.history(period=YAHOO_DAILY_PERIOD, interval="1d")
                    if not df_daily.empty:
                        df_daily = df_daily.reset_index()
                        df_daily["ticker"] = ticker
                        df_daily["interval"] = "1d"
                        all_data.append(df_daily)

                    # Fetch hourly data (last 60 days)
                    df_hourly = yfobj.history(period=YAHOO_HOURLY_PERIOD, interval="1h")
                    if not df_hourly.empty:
                        df_hourly = df_hourly.reset_index()
                        df_hourly["ticker"] = ticker
                        df_hourly["interval"] = "1h"
                        all_data.append(df_hourly)

                    break  # success
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        self.mark_error(f"Failed to fetch {ticker}: {e}")
                    else:
                        time.sleep(self.retry_delay * (2 ** attempt))  # exponential backoff

        if not all_data:
            raise RuntimeError("No data fetched from any Yahoo ticker")

        # Combine all data
        df = pd.concat(all_data, ignore_index=True)

        # Standardize columns
        df = df.rename(columns={
            "Date": "timestamp",
            "Datetime": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        })

        # Keep only required columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]

        # Filter by date range
        df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]

        # Sort and deduplicate
        df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")

        if self.validate(df):
            self.mark_success()
            return df
        else:
            raise ValueError("Validation failed")

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate Yahoo data quality."""
        if df.empty:
            self.mark_error("Empty dataframe")
            return False

        # No NaN in close price
        if df["close"].isna().any():
            self.mark_error("NaN in close prices")
            return False

        # Volume must be positive
        if (df["volume"] <= 0).any():
            self.mark_error("Non-positive volume")
            return False

        # Price range check (500-5000 USD/oz is realistic for gold)
        if (df["close"] < 500).any() or (df["close"] > 5000).any():
            self.mark_error("Price outside realistic range")
            return False

        return True
