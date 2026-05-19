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

                    # Fetch daily data using history() — more reliable than download()
                    df = yfobj.history(period=YAHOO_DAILY_PERIOD, interval="1d", auto_adjust=True)

                    if df.empty:
                        if attempt == self.max_retries - 1:
                            self.mark_error(f"Empty data for {ticker}")
                        else:
                            time.sleep(self.retry_delay * (2 ** attempt))
                        continue

                    # Reset index — converts DatetimeIndex to 'Date' or 'Datetime' column
                    df = df.reset_index()

                    # Find date column (could be 'Date' or 'Datetime' depending on interval)
                    date_col = None
                    if 'Datetime' in df.columns:
                        date_col = 'Datetime'
                    elif 'Date' in df.columns:
                        date_col = 'Date'
                    else:
                        raise ValueError(f"No date column found in {ticker} data: {df.columns.tolist()}")

                    # Rename to timestamp
                    df = df.rename(columns={date_col: 'timestamp'})

                    # Lowercase all column names
                    df.columns = [c.lower() for c in df.columns]

                    # Strip timezone if present
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    if hasattr(df['timestamp'].iloc[0], 'tzinfo') and df['timestamp'].iloc[0].tzinfo:
                        df['timestamp'] = df['timestamp'].dt.tz_localize(None)

                    # Keep only OHLCV + add metadata
                    required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    df = df[[c for c in required_cols if c in df.columns]].copy()

                    # Validate basic sanity
                    df = df.dropna(subset=['close'])
                    df = df[df['close'] > 0]

                    if df.empty:
                        if attempt == self.max_retries - 1:
                            self.mark_error(f"No valid data after cleaning {ticker}")
                        continue

                    df['source'] = ticker.lower().replace('=f', '_futures').replace('^', '')
                    df['fetch_time'] = datetime.now()
                    df['quality_score'] = 1.0

                    all_data.append(df)
                    break  # success

                except Exception as e:
                    if attempt == self.max_retries - 1:
                        self.mark_error(f"Failed to fetch {ticker}: {e}")
                    else:
                        time.sleep(self.retry_delay * (2 ** attempt))  # exponential backoff

        if not all_data:
            raise RuntimeError("All Yahoo tickers failed")

        # Combine all data
        df = pd.concat(all_data, ignore_index=True)

        # Ensure start/end are naive datetime
        if start_date and hasattr(start_date, 'tzinfo') and start_date.tzinfo:
            start_date = start_date.replace(tzinfo=None)
        if end_date and hasattr(end_date, 'tzinfo') and end_date.tzinfo:
            end_date = end_date.replace(tzinfo=None)

        # Filter by date range
        if start_date:
            df = df[df["timestamp"] >= start_date]
        if end_date:
            df = df[df["timestamp"] <= end_date]

        # Sort and deduplicate by source+timestamp
        df = df.sort_values("timestamp").drop_duplicates(["source", "timestamp"], keep="last")

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

        # Volume check — allow zero (illiquid days), but not negative
        if 'volume' in df.columns:
            if (df["volume"] < 0).any():
                self.mark_error("Negative volume")
                return False

        # Price range check (gold: 500-5000 $/oz for GC=F, 50-500 $/share for GLD)
        # Accept anything in this wider range
        if (df["close"] < 50).any() or (df["close"] > 6000).any():
            self.mark_error("Price outside realistic range")
            return False

        return True
