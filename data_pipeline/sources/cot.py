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
                print(f"Fetching COT {year}...")
                response = requests.get(url, timeout=60)
                response.raise_for_status()

                # Extract Excel from zip
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    # Find the Excel file (usually .xls)
                    excel_files = [f for f in zf.namelist() if f.endswith('.xls') or f.endswith('.xlsx')]
                    if not excel_files:
                        self.mark_error(f"No Excel file in {year} zip")
                        continue

                    excel_file = excel_files[0]
                    print(f"  Parsing {excel_file}...")

                    with zf.open(excel_file) as f:
                        # Try xlrd for .xls files
                        try:
                            if excel_file.endswith('.xls'):
                                df = pd.read_excel(f, engine='xlrd')
                            else:
                                df = pd.read_excel(f, engine='openpyxl')
                        except Exception as e:
                            # Fallback: read bytes and try again
                            f.seek(0)
                            df = pd.read_excel(io.BytesIO(f.read()), engine='xlrd' if excel_file.endswith('.xls') else 'openpyxl')

                    # Find gold rows — column names vary between years
                    # Try multiple search strategies
                    df_gold = pd.DataFrame()

                    # Strategy 1: Search by CFTC_Contract_Market_Code
                    if 'CFTC_Contract_Market_Code' in df.columns:
                        mask = df['CFTC_Contract_Market_Code'].astype(str).str.contains(self.gold_code, na=False)
                        df_gold = df[mask].copy()

                    # Strategy 2: Search by Market_and_Exchange_Names
                    if df_gold.empty:
                        name_cols = [c for c in df.columns if 'market' in c.lower() and 'exchange' in c.lower()]
                        for name_col in name_cols:
                            mask = df[name_col].astype(str).str.contains('GOLD|088691', case=False, na=False)
                            if mask.any():
                                df_gold = df[mask].copy()
                                break

                    # Strategy 3: Search any column for 088691
                    if df_gold.empty:
                        for col in df.columns:
                            if df[col].dtype == 'object' or 'int' in str(df[col].dtype):
                                mask = df[col].astype(str).str.contains('088691', na=False)
                                if mask.any():
                                    df_gold = df[mask].copy()
                                    break

                    if df_gold.empty:
                        self.mark_error(f"No gold data (088691) in {year} COT report")
                        continue

                    print(f"  Found {len(df_gold)} gold rows")

                    # Flexible column mapping — try multiple name variants
                    col_map = {}
                    for col in df_gold.columns:
                        col_lower = col.lower().replace('_', '').replace(' ', '')
                        if 'reportdate' in col_lower and ('mm' in col_lower or 'yyyy' in col_lower):
                            col_map['report_date'] = col
                        elif col == 'Comm_Positions_Long_All':
                            col_map['commercial_long'] = col
                        elif col == 'Comm_Positions_Short_All':
                            col_map['commercial_short'] = col
                        elif col == 'NonComm_Positions_Long_All':
                            col_map['noncommercial_long'] = col
                        elif col == 'NonComm_Positions_Short_All':
                            col_map['noncommercial_short'] = col
                        elif col == 'Open_Interest_All':
                            col_map['open_interest'] = col

                    # Rename columns
                    df_gold = df_gold.rename(columns={v: k for k, v in col_map.items()})

                    # Keep only needed columns
                    required = ['report_date', 'commercial_long', 'commercial_short',
                                'noncommercial_long', 'noncommercial_short', 'open_interest']
                    available = [c for c in required if c in df_gold.columns]

                    if len(available) < 3:
                        self.mark_error(f"Missing COT columns in {year}: found {available}")
                        continue

                    df_gold = df_gold[available].copy()

                    # Compute derived metrics
                    if 'commercial_long' in df_gold.columns and 'commercial_short' in df_gold.columns:
                        df_gold['net_commercial'] = df_gold['commercial_long'] - df_gold['commercial_short']
                    if 'noncommercial_long' in df_gold.columns and 'noncommercial_short' in df_gold.columns:
                        df_gold['speculator_sentiment'] = (
                            df_gold['noncommercial_long'] /
                            (df_gold['noncommercial_long'] + df_gold['noncommercial_short'] + 1e-9)
                        )

                    # Convert report_date to datetime
                    if 'report_date' in df_gold.columns:
                        df_gold['report_date'] = pd.to_datetime(df_gold['report_date'], errors='coerce')
                        df_gold = df_gold.dropna(subset=['report_date'])

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
