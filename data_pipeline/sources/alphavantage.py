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
        """Fetch gold OHLCV from Alpha Vantage with aggressive caching."""
        import json
        from pathlib import Path

        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 5)

        cache_dir = Path('/tmp')
        cache_file = cache_dir / 'av_gld_cache.json'

        # Use cache if less than 23 hours old
        data = None
        if cache_file.exists():
            age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
            if age_hours < 23:
                print(f"Using AV cache ({age_hours:.1f}h old)")
                with open(cache_file) as f:
                    data = json.load(f)

        all_data = []

        for symbol in self.symbols:
            try:
                # Fetch if no cache
                if data is None:
                    params = {
                        "function": "TIME_SERIES_DAILY",
                        "symbol": symbol,
                        "outputsize": "full",
                        "apikey": self.api_key,
                    }

                    response = requests.get(self.base_url, params=params, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    # Check for rate limit
                    if 'Information' in data or 'Note' in data:
                        msg = data.get('Information', data.get('Note', 'Unknown'))
                        print(f"AV rate limited: {msg}")
                        self.mark_error(f"AV rate limited: {msg}")
                        # Return empty df gracefully — other sources will carry the load
                        return pd.DataFrame()

                    # Cache the response
                    with open(cache_file, 'w') as f:
                        json.dump(data, f)

                # Parse time series
                ts_key = [k for k in data.keys() if 'Time Series' in k]
                if not ts_key:
                    self.mark_error(f"No time series in AV response for {symbol}: {list(data.keys())}")
                    continue

                ts = data[ts_key[0]]
                rows = []
                for date_str, values in ts.items():
                    try:
                        rows.append({
                            "timestamp": pd.to_datetime(date_str),
                            "open": float(values.get("1. open", values.get("open", 0))),
                            "high": float(values.get("2. high", values.get("high", 0))),
                            "low": float(values.get("3. low", values.get("low", 0))),
                            "close": float(values.get("4. close", values.get("close", 0))),
                            "volume": float(values.get("5. volume", values.get("volume", 0))),
                        })
                    except (ValueError, KeyError):
                        continue

                df = pd.DataFrame(rows).sort_values('timestamp')
                df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]
                df['source'] = 'alphavantage'
                df['fetch_time'] = datetime.now()
                df['quality_score'] = 0.9
                all_data.append(df)

                # Rate limit delay
                time.sleep(ALPHAVANTAGE_RATE_LIMIT_DELAY)

            except Exception as e:
                self.mark_error(f"Failed to fetch {symbol}: {e}")

        if not all_data:
            # Graceful degradation — return empty rather than crash
            print("WARNING: No Alpha Vantage data, pipeline will use other sources")
            return pd.DataFrame()

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
