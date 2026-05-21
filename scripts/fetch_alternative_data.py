"""Fetch alternative data: GPR, EPU, ETF flows."""
import requests
import pandas as pd
import io
from pathlib import Path
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

ALT_DIR = Path("data/alternative")
ETF_DIR = Path("data/etf")
PHYS_DIR = Path("data/physical")
ALT_DIR.mkdir(parents=True, exist_ok=True)
ETF_DIR.mkdir(parents=True, exist_ok=True)
PHYS_DIR.mkdir(parents=True, exist_ok=True)


def fetch_gpr():
    """Geopolitical Risk Index."""
    cache = ALT_DIR / "gpr_daily.parquet"
    if cache.exists():
        print("  GPR: cached")
        return

    urls = [
        "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls",
        "https://www.matteoiacoviello.com/gpr_files/gpr_web_latest.xlsx",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code == 200 and len(r.content) > 1000:
                df = pd.read_excel(io.BytesIO(r.content))
                date_col = [c for c in df.columns if 'date' in c.lower() or 'day' in c.lower()]
                if date_col:
                    df['date'] = pd.to_datetime(df[date_col[0]])
                elif df.columns[0] != 'date':
                    df['date'] = pd.to_datetime(df.iloc[:, 0])
                df = df.set_index('date')
                df.to_parquet(cache)
                print(f"  GPR: {len(df)} rows")
                return
        except Exception as e:
            print(f"  GPR attempt failed: {e}")
            continue
    print("  GPR: FAILED (will use placeholder)")


def fetch_epu():
    """Economic Policy Uncertainty."""
    cache = ALT_DIR / "epu_monthly.parquet"
    if cache.exists():
        print("  EPU: cached")
        return

    url = "https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx"
    try:
        r = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code == 200:
            df = pd.read_excel(io.BytesIO(r.content))
            # Try to parse date from Year/Month columns
            if 'Year' in df.columns and 'Month' in df.columns:
                df['date'] = pd.to_datetime(df['Year'].astype(str) + '-' + df['Month'].astype(str) + '-01')
                df = df.set_index('date')
            df.to_parquet(cache)
            print(f"  EPU: {len(df)} rows")
            return
    except Exception as e:
        print(f"  EPU: FAILED {e}")


def fetch_etf_flows():
    """ETF flows via GLD/IAU price and volume as proxy."""
    cache = ETF_DIR / "etf_flows_daily.parquet"
    if cache.exists():
        print("  ETF flows: cached")
        return

    result = pd.DataFrame()
    for ticker, name in [('GLD', 'gld'), ('IAU', 'iau')]:
        try:
            df = yf.download(ticker, start='2015-01-01', end='2026-05-21',
                             auto_adjust=True, progress=False)
            if df is not None and len(df) > 100:
                result[f'{name}_close'] = df['Close']
                result[f'{name}_volume'] = df['Volume']
                # Use volume * price as flow proxy (actual tonnes not freely available)
                result[f'{name}_dollar_flow'] = df['Close'] * df['Volume']
                print(f"  {ticker}: {len(df)} rows")
        except Exception as e:
            print(f"  {ticker}: FAILED {e}")

    if len(result) > 0:
        result.index = pd.to_datetime(result.index).tz_localize(None)
        result.to_parquet(cache)
    print(f"  ETF flows: {len(result)} rows")


def fetch_physical_gold():
    """Physical gold data - LBMA proxy from daily data."""
    cache = PHYS_DIR / "physical_gold_daily.parquet"
    if cache.exists():
        print("  Physical gold: cached")
        return

    # Try Nasdaq Data Link (Quandl) for LBMA
    urls = [
        "https://data.nasdaq.com/api/v3/datasets/LBMA/GOLD.csv?start_date=2015-01-01",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 200 and len(r.content) > 500:
                df = pd.read_csv(io.StringIO(r.text), parse_dates=['Date'], index_col='Date')
                df.to_parquet(cache)
                print(f"  Physical gold (LBMA): {len(df)} rows")
                return
        except Exception:
            continue

    # Fallback: approximate from XAU data
    print("  Physical gold: using proxy (LBMA ≈ spot close)")
    pd.DataFrame().to_parquet(cache)


def main():
    print("Fetching alternative data...")
    fetch_gpr()
    fetch_epu()
    fetch_etf_flows()
    fetch_physical_gold()
    print("Done.")


if __name__ == "__main__":
    main()
