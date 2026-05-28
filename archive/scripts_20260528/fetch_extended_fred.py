#!/usr/bin/env python3
"""Fetch 100+ FRED series."""
import requests
import pandas as pd
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

OUTPUT_DIR = Path("data/macro_extended")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = OUTPUT_DIR / "fred_extended_daily.parquet"

# Expanded FRED series
SERIES = {
    # Interest rates (existing)
    'DFF': 'Fed Funds', 'DGS1MO': '1M TSY', 'DGS3MO': '3M TSY', 'DGS6MO': '6M TSY',
    'DGS1': '1Y TSY', 'DGS2': '2Y TSY', 'DGS5': '5Y TSY', 'DGS10': '10Y TSY',
    'DGS20': '20Y TSY', 'DGS30': '30Y TSY',
    'DFII5': '5Y TIPS', 'DFII10': '10Y TIPS', 'DFII20': '20Y TIPS', 'DFII30': '30Y TIPS',
    'T5YIE': '5Y BE', 'T10YIE': '10Y BE', 'T5YIFR': '5Y5Y Fwd', 'T10Y2Y': '10Y-2Y',
    'T10Y3M': '10Y-3M',

    # Credit spreads
    'BAMLC0A0CM': 'Corp OAS', 'BAMLH0A0HYM2': 'HY OAS', 'BAMLC0A4CBBB': 'BBB OAS',
    'BAMLC0A1CAAA': 'AAA OAS', 'BAMLH0A1HYBB': 'BB HY', 'BAMLH0A2HYC': 'CCC HY',
    'DAAA': 'AAA Corp', 'DBAA': 'BAA Corp', 'DCOILWTICO': 'WTI Spot',

    # Inflation
    'CPIAUCSL': 'CPI', 'CPILFESL': 'Core CPI', 'PCEPI': 'PCE', 'PCEPILFE': 'Core PCE',
    'MICH': 'Mich Exp', 'CORESTICKM159SFRBATL': 'Sticky CPI', 'EXPINF5YR': '5Y Exp Inf',
    'EXPINF10YR': '10Y Exp Inf',

    # Growth
    'GDPC1': 'Real GDP', 'A191RL1Q225SBEA': 'GDP Grth', 'INDPRO': 'Ind Prod',
    'TCU': 'Cap Util', 'RSAFS': 'Retail Sales', 'UMCSENT': 'Mich Sent',
    'HOUST': 'Housing Starts', 'PERMIT': 'Bld Permits', 'DSPIC96': 'Disp Income',
    'PSAVERT': 'Savings Rate', 'MORTGAGE30US': '30Y Mtg',

    # Labor
    'PAYEMS': 'Payrolls', 'UNRATE': 'Unemp Rate', 'ICSA': 'Init Claims', 'CCSA': 'Cont Claims',
    'CIVPART': 'Part Rate', 'EMRATIO': 'Emp/Pop', 'AHETPI': 'Hrly Earn',
    'U6RATE': 'U6 Rate', 'LNS14000006': 'U6',

    # Money & Credit
    'M2SL': 'M2', 'M1SL': 'M1', 'WALCL': 'Fed Assets', 'WRESBAL': 'Reserves',
    'TOTRESNS': 'Tot Reserves', 'DPCREDIT': 'Dom Credit', 'BUSLOANS': 'C&I Loans',
    'CONSUMER': 'Cons Credit', 'REVOLSL': 'Revolv Credit',

    # Housing
    'CSUSHPISA': 'Case-Shiller', 'MORTGAGE15US': '15Y Mtg', 'RRVRUSQ156N': 'Rental Vac',
    'ACTLISCOUUS': 'Home Sales', 'MSPUS': 'Median Price',

    # Manufacturing
    'NEWORDER': 'New Orders', 'DGORDER': 'Dur Gds Ord', 'ISM': 'ISM PMI', 'NAPM': 'NAPM',
    'BUSINV': 'Bus Inv', 'ISRATIO': 'Inv/Sales',

    # Trade
    'NETEXP': 'Net Exports', 'BOPGSTB': 'Trade Bal', 'IMPCH': 'Imports', 'EXPCH': 'Exports',

    # Commodities
    'DCOILBRENTEU': 'Brent', 'GASREGW': 'Gas Price', 'PPIACO': 'PPI', 'PPIFIS': 'PPI Final',
    'GOLDAMGBD228NLBM': 'Gold LBMA',

    # Financial conditions
    'NFCI': 'Chicago FCI', 'ANFCI': 'Adj NFCI', 'STLFSI': 'STL FCI',
    'GSFCI': 'GS FCI',

    # International
    'VIXCLS': 'VIX Close', 'TEDRATE': 'TED Spread', 'DEXCHUS': 'USD/CNY', 'DEXJPUS': 'JPY/USD',
}


def fetch_fred_csv(series_id):
    cache = OUTPUT_DIR / f"{series_id}.parquet"
    if cache.exists():
        try:
            df = pd.read_parquet(cache)
            if len(df) > 10:
                return (series_id, len(df), 'cached')
        except:
            pass

    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2015-01-01&coed=2026-05-20"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200 and len(r.content) > 50:
            df = pd.read_csv(io.StringIO(r.text))
            date_col = df.columns[0]
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.set_index(date_col)
            df.columns = [series_id]
            df[series_id] = pd.to_numeric(df[series_id], errors='coerce')
            df = df.dropna()
            if len(df) > 10:
                df.to_parquet(cache)
                return (series_id, len(df), 'fetched')
    except:
        pass
    return (series_id, 0, 'failed')


def main():
    print(f"Fetching {len(SERIES)} FRED series...")

    results = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(fetch_fred_csv, sid): sid for sid in SERIES.keys()}
        completed = 0
        for future in as_completed(futures):
            sid, rows, status = future.result()
            results.append((sid, rows, status))
            completed += 1
            if completed % 20 == 0:
                success = sum(1 for _, _, s in results if s != 'failed')
                print(f"  {completed}/{len(SERIES)} | Success: {success}")

    # Combine
    print("\nCombining...")
    date_range = pd.date_range('2015-01-01', '2026-05-20', freq='D')
    combined = pd.DataFrame(index=date_range)
    combined.index.name = 'date'

    success_count = 0
    for sid, rows, status in results:
        if status == 'failed':
            continue
        try:
            df = pd.read_parquet(OUTPUT_DIR / f"{sid}.parquet")
            combined[sid] = df[sid]
            success_count += 1
        except:
            pass

    combined = combined.ffill()
    combined.to_parquet(OUTPUT)

    real = [c for c in combined.columns if combined[c].notna().sum() > 100]
    print(f"\nSaved: {OUTPUT}")
    print(f"Rows: {len(combined)}")
    print(f"Real columns: {len(real)}")
    print(f"Failed: {len(SERIES) - success_count}")


if __name__ == "__main__":
    main()
