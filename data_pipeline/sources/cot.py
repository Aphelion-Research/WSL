"""CFTC Commitments of Traders data source."""
import io
import zipfile
from typing import Optional
from datetime import datetime
import pandas as pd
import requests

from data_pipeline.sources.base import DataSource
from data_pipeline.config import COT_URLS, COT_GOLD_CODE


class COTSource(DataSource):
    """CFTC COT reports for gold futures."""

    def __init__(self):
        super().__init__("cot")
        self.urls = COT_URLS
        self.gold_code = COT_GOLD_CODE

    def fetch(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch and parse COT reports for gold."""
        all_data = []

        for year, url in self.urls.items():
            try:
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                # Extract Excel from zip
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    # Find the Excel file
                    excel_files = [f for f in zf.namelist() if f.endswith('.xls') or f.endswith('.xlsx')]
                    if not excel_files:
                        self.mark_error(f"No Excel file in {year} zip")
                        continue

                    with zf.open(excel_files[0]) as excel_file:
                        df = pd.read_excel(excel_file)

                        # Filter for gold futures (COMEX code 088691)
                        df_gold = df[df['CFTC_Contract_Market_Code'].astype(str) == self.gold_code].copy()

                        if df_gold.empty:
                            self.mark_error(f"No gold data in {year} COT report")
                            continue

                        # Extract relevant columns
                        df_gold = df_gold.rename(columns={
                            'Report_Date_as_YYYY-MM-DD': 'report_date',
                            'Comm_Positions_Long_All': 'commercial_long',
                            'Comm_Positions_Short_All': 'commercial_short',
                            'NonComm_Positions_Long_All': 'noncommercial_long',
                            'NonComm_Positions_Short_All': 'noncommercial_short',
                            'Open_Interest_All': 'open_interest',
                        })

                        # Keep only needed columns
                        cols = ['report_date', 'commercial_long', 'commercial_short',
                                'noncommercial_long', 'noncommercial_short', 'open_interest']
                        df_gold = df_gold[cols]

                        # Compute derived metrics
                        df_gold['net_commercial'] = df_gold['commercial_long'] - df_gold['commercial_short']
                        df_gold['speculator_sentiment'] = (
                            df_gold['noncommercial_long'] /
                            (df_gold['noncommercial_long'] + df_gold['noncommercial_short'])
                        )

                        # Convert report_date to datetime
                        df_gold['report_date'] = pd.to_datetime(df_gold['report_date'])

                        all_data.append(df_gold)

            except Exception as e:
                self.mark_error(f"Failed to fetch COT {year}: {e}")

        if not all_data:
            raise RuntimeError("No COT data fetched")

        df = pd.concat(all_data, ignore_index=True)
        df = df.sort_values('report_date').drop_duplicates('report_date', keep='last')

        # Filter by date range
        if start_date:
            df = df[df['report_date'] >= start_date]
        if end_date:
            df = df[df['report_date'] <= end_date]

        if self.validate(df):
            self.mark_success()
            return df
        else:
            raise ValueError("Validation failed")

    def validate(self, df: pd.DataFrame) -> bool:
        """Validate COT data."""
        if df.empty:
            self.mark_error("Empty dataframe")
            return False

        # Check for required columns
        required = ['report_date', 'commercial_long', 'commercial_short',
                    'noncommercial_long', 'noncommercial_short', 'open_interest']
        if not all(col in df.columns for col in required):
            self.mark_error("Missing required columns")
            return False

        # No NaN in key columns
        if df[required].isna().any().any():
            self.mark_error("NaN in COT data")
            return False

        return True
