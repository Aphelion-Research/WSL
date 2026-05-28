"""Fetch macro data from FRED CSV endpoints."""
import requests
import pandas as pd
import io
from pathlib import Path
import time

MACRO_DIR = Path("data/macro")
MACRO_DIR.mkdir(parents=True, exist_ok=True)

FRED_SERIES = {
    # Interest rates (daily)
    'DFF': 'Fed Funds Rate',
    'DGS1MO': '1-Month Treasury',
    'DGS3MO': '3-Month Treasury',
    'DGS6MO': '6-Month Treasury',
    'DGS1': '1-Year Treasury',
    'DGS2': '2-Year Treasury',
    'DGS5': '5-Year Treasury',
    'DGS10': '10-Year Treasury',
    'DGS20': '20-Year Treasury',
    'DGS30': '30-Year Treasury',
    'DFII5': '5-Year TIPS',
    'DFII10': '10-Year TIPS',
    'T5YIE': '5-Year Breakeven',
    'T10YIE': '10-Year Breakeven',
    'T5YIFR': '5-Year Forward Inflation',
    'T10Y2Y': '10Y-2Y Spread',
    'T10Y3M': '10Y-3M Spread',
    # Inflation (monthly)
    'CPIAUCSL': 'CPI All Urban',
    'CPILFESL': 'Core CPI',
    'PCEPI': 'PCE Price Index',
    'PCEPILFE': 'Core PCE',
    'MICH': 'Michigan Inflation Expectations',
    # Growth & Labor
    'GDPC1': 'Real GDP',
    'PAYEMS': 'Nonfarm Payrolls',
    'UNRATE': 'Unemployment Rate',
    'ICSA': 'Initial Claims',
    'RSAFS': 'Retail Sales',
    'INDPRO': 'Industrial Production',
    'TCU': 'Capacity Utilization',
    # Fed Balance Sheet
    'WALCL': 'Fed Total Assets',
}


def fetch_fred_csv(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2015-01-01&coed=2026-05-20"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 50:
            df = pd.read_csv(io.StringIO(r.text))
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
            df.columns = [series_id]
            df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
            df = df.dropna()
            return df
    except Exception:
        pass
    return None


def main():
    all_series = {}
    failed = []

    for series_id, name in FRED_SERIES.items():
        cache_file = MACRO_DIR / f"{series_id}.parquet"
        if cache_file.exists():
            df = pd.read_parquet(cache_file)
            all_series[series_id] = df
            print(f"  {series_id}: cached ({len(df)} rows)")
            continue

        df = fetch_fred_csv(series_id)
        if df is not None and len(df) > 10:
            df.to_parquet(cache_file)
            all_series[series_id] = df
            print(f"  {series_id}: {len(df)} rows")
        else:
            failed.append(series_id)
            print(f"  {series_id}: FAILED")
        time.sleep(0.3)

    if failed:
        print(f"\nFailed series: {failed}")

    # Combine all into daily frequency
    print("\nCombining into daily macro dataset...")
    date_range = pd.date_range('2015-01-01', '2026-05-20', freq='D')
    combined = pd.DataFrame(index=date_range)
    combined.index.name = 'date'

    for series_id, df in all_series.items():
        df.index = pd.to_datetime(df.index)
        combined = combined.join(df, how='left')

    # Forward fill (macro data is sparse)
    combined = combined.ffill()
    combined.to_parquet(MACRO_DIR / "macro_daily.parquet")
    real_cols = [c for c in combined.columns if combined[c].notna().sum() > 100]
    print(f"Macro daily: {len(combined)} rows, {len(real_cols)} real columns")
    print(f"Columns: {real_cols}")


if __name__ == "__main__":
    main()
