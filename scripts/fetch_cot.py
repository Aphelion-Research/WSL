"""Fetch COT data from CFTC."""
import requests
import pandas as pd
import zipfile
import io
from pathlib import Path

COT_DIR = Path("data/cot")
COT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = COT_DIR / "cot_gold_weekly.parquet"


def main():
    if OUTPUT.exists():
        df = pd.read_parquet(OUTPUT)
        print(f"COT cached: {len(df)} rows")
        return

    all_dfs = []
    for year in range(2015, 2027):
        url = f"https://www.cftc.gov/files/dea/history/fut_disagg_txt_{year}.zip"
        print(f"  Fetching COT {year}...")
        try:
            r = requests.get(url, timeout=120)
            if r.status_code != 200:
                print(f"    {year}: HTTP {r.status_code}")
                continue
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                for fname in z.namelist():
                    if fname.endswith('.txt'):
                        with z.open(fname) as f:
                            df = pd.read_csv(f, low_memory=False)
                            # Filter for gold
                            gold_mask = df['Market_and_Exchange_Names'].str.contains('GOLD', case=False, na=False)
                            gold_df = df[gold_mask].copy()
                            if len(gold_df) > 0:
                                all_dfs.append(gold_df)
                                print(f"    {year}: {len(gold_df)} gold rows")
        except Exception as e:
            print(f"    {year}: ERROR {e}")
            continue

    if not all_dfs:
        print("ERROR: No COT data fetched!")
        # Create minimal placeholder
        pd.DataFrame().to_parquet(OUTPUT)
        return

    cot = pd.concat(all_dfs, ignore_index=True)
    cot['Report_Date_as_YYYY-MM-DD'] = pd.to_datetime(cot['Report_Date_as_YYYY-MM-DD'])
    cot = cot.sort_values('Report_Date_as_YYYY-MM-DD')

    # Extract key columns
    result = pd.DataFrame()
    result['date'] = cot['Report_Date_as_YYYY-MM-DD']

    # Managed money
    mm_long_col = [c for c in cot.columns if 'M_Money' in c and 'Long' in c and 'Spread' not in c]
    mm_short_col = [c for c in cot.columns if 'M_Money' in c and 'Short' in c and 'Spread' not in c]

    if mm_long_col:
        result['mm_long'] = pd.to_numeric(cot[mm_long_col[0]], errors='coerce').values
    if mm_short_col:
        result['mm_short'] = pd.to_numeric(cot[mm_short_col[0]], errors='coerce').values

    # Commercial
    comm_long_col = [c for c in cot.columns if 'Comm' in c and 'Long' in c and 'Positions' in c]
    comm_short_col = [c for c in cot.columns if 'Comm' in c and 'Short' in c and 'Positions' in c]
    if comm_long_col:
        result['comm_long'] = pd.to_numeric(cot[comm_long_col[0]], errors='coerce').values
    if comm_short_col:
        result['comm_short'] = pd.to_numeric(cot[comm_short_col[0]], errors='coerce').values

    # Open interest
    oi_col = [c for c in cot.columns if 'Open_Interest' in c and 'Old' not in c]
    if oi_col:
        result['open_interest'] = pd.to_numeric(cot[oi_col[0]], errors='coerce').values

    result = result.set_index('date')
    result = result[~result.index.duplicated(keep='last')]
    result.to_parquet(OUTPUT)
    print(f"\nCOT gold weekly: {len(result)} rows, {result.index.min()} to {result.index.max()}")


if __name__ == "__main__":
    main()
