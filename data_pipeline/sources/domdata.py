"""MT5 data source via existing domdata CLI."""
import subprocess
import json
from typing import Optional
from datetime import datetime
import pandas as pd

from data_pipeline.sources.base import DataSource
from data_pipeline.config import DOMDATA_CLI


class DomdataSource(DataSource):
    """MT5 tick and rate data via domdata CLI."""

    def __init__(self):
        super().__init__("mt5")
        self.cli = DOMDATA_CLI

    def fetch(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch XAU/USD data via domdata CLI."""
        try:
            # Use domdata CLI wrapper (installed in PATH) instead of python script
            result = subprocess.run(
                ["domdata", "rates", "XAUUSD", "D1", "--count", "1000"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                raise RuntimeError(f"domdata failed: {result.stderr}")

            # Parse JSON output — domdata returns flat array, not nested
            data = json.loads(result.stdout)

            if not data:
                raise RuntimeError("No rates data from domdata")

            # Convert directly to DataFrame
            df = pd.DataFrame(data)

            # Rename/standardize columns
            df['timestamp'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={
                'tick_volume': 'volume'
            })

            # Keep only OHLCV + add metadata
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
            df = df.dropna(subset=['close'])
            df['source'] = 'mt5'
            df['fetch_time'] = datetime.now()
            df['quality_score'] = 1.0

            # Filter by date range
            if start_date:
                df = df[df["timestamp"] >= start_date]
            if end_date:
                df = df[df["timestamp"] <= end_date]

            df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="last")

            if self.validate(df):
                self.mark_success()
                return df
            else:
                raise ValueError("Validation failed")

        except FileNotFoundError:
            self.mark_error("domdata CLI not found - graceful degradation")
            return pd.DataFrame()  # Empty df, not fatal
        except subprocess.TimeoutExpired:
            self.mark_error("domdata timeout")
            return pd.DataFrame()
        except Exception as e:
            self.mark_error(f"domdata error: {e}")
            return pd.DataFrame()

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate MT5 data."""
        if df.empty:
            return True  # Empty is OK (offline mode)

        # No NaN in close price
        if df["close"].isna().any():
            self.mark_error("NaN in close prices")
            return False

        # Price range check (MT5 quotes gold in $/oz, wider range than GLD ETF)
        if (df["close"] < 500).any() or (df["close"] > 6000).any():
            self.mark_error("Price outside realistic range")
            return False

        return True
