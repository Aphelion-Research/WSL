"""
Download XAU/USD M5 data from Dukascopy back to 2003.
Extends existing dataset for more OOS validation years.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import requests
import io
import lzma
import struct
import warnings
warnings.filterwarnings('ignore')

OUTPUT_FILE = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")


def download_dukascopy_tick_data(symbol, year, month, day, hour):
    """
    Download Dukascopy bi5 file for given time.
    Returns DataFrame with ticks.
    """
    # Dukascopy URL format
    base_url = "https://datafeed.dukascopy.com/datafeed"

    # Symbol mapping (Dukascopy uses different codes)
    symbol_map = {
        'XAUUSD': 'XAUUSD',
        'EURUSD': 'EURUSD',
        'GBPUSD': 'GBPUSD',
    }

    duka_symbol = symbol_map.get(symbol, symbol)

    # Build URL: /SYMBOL/YEAR/MONTH-1/DAY/HOUR_ticks.bi5
    # Month is 0-indexed in URL
    url = f"{base_url}/{duka_symbol}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        # Decompress LZMA
        try:
            decompressed = lzma.decompress(response.content)
        except:
            return None

        # Parse binary format (20 bytes per tick)
        # Format: time_ms (4), ask (4), bid (4), ask_vol (4), bid_vol (4)
        num_ticks = len(decompressed) // 20

        if num_ticks == 0:
            return None

        ticks = []
        for i in range(num_ticks):
            offset = i * 20
            chunk = decompressed[offset:offset+20]

            if len(chunk) < 20:
                break

            time_ms, ask, bid, ask_vol, bid_vol = struct.unpack('>5I', chunk)

            # Convert to actual values
            # Dukascopy stores prices as integers (multiply by point value)
            # For XAU/USD: point = 0.001 usually
            point = 0.001
            ask_price = ask * point
            bid_price = bid * point

            # Time: milliseconds since start of hour
            base_time = datetime(year, month+1, day, hour)
            tick_time = base_time + timedelta(milliseconds=time_ms)

            ticks.append({
                'time': tick_time,
                'ask': ask_price,
                'bid': bid_price,
                'ask_volume': ask_vol,
                'bid_volume': bid_vol,
            })

        if not ticks:
            return None

        return pd.DataFrame(ticks)

    except Exception as e:
        return None


def aggregate_to_m5(ticks_df):
    """Aggregate ticks to M5 OHLC bars."""
    if ticks_df is None or len(ticks_df) == 0:
        return None

    ticks_df = ticks_df.set_index('time').sort_index()

    # Use mid price
    ticks_df['mid'] = (ticks_df['ask'] + ticks_df['bid']) / 2
    ticks_df['spread'] = ticks_df['ask'] - ticks_df['bid']

    # Resample to 5-min bars
    m5 = ticks_df.resample('5min').agg({
        'mid': ['first', 'max', 'min', 'last'],
        'spread': 'mean',
        'ask_volume': 'sum',
    })

    # Flatten multi-index columns
    m5.columns = ['open', 'high', 'low', 'close', 'spread', 'tick_volume']
    m5 = m5.dropna(subset=['close'])

    return m5


def download_historical_range(symbol, start_year, end_year):
    """Download data year by year."""
    all_data = []

    for year in range(start_year, end_year + 1):
        print(f"\n  Downloading {year}...")
        year_data = []

        for month in range(12):  # 0-11 (Dukascopy month indexing)
            # Figure out days in month
            if month == 11:
                days_in_month = 31
            elif month in [3, 5, 8, 10]:  # Apr, Jun, Sep, Nov
                days_in_month = 30
            elif month == 1:  # Feb
                days_in_month = 29 if year % 4 == 0 else 28
            else:
                days_in_month = 31

            month_bars = 0

            for day in range(1, days_in_month + 1):
                day_ticks = []

                for hour in range(24):
                    ticks = download_dukascopy_tick_data(symbol, year, month, day, hour)
                    if ticks is not None:
                        day_ticks.append(ticks)

                if day_ticks:
                    day_df = pd.concat(day_ticks, ignore_index=True)
                    m5_bars = aggregate_to_m5(day_df)
                    if m5_bars is not None and len(m5_bars) > 0:
                        year_data.append(m5_bars)
                        month_bars += len(m5_bars)

            if month_bars > 0:
                print(f"    {year}-{month+1:02d}: {month_bars} bars")

        if year_data:
            year_df = pd.concat(year_data)
            all_data.append(year_df)
            print(f"  {year} total: {len(year_df):,} bars")

    if all_data:
        return pd.concat(all_data)
    else:
        return None


def main():
    print("="*80)
    print("DOWNLOADING HISTORICAL XAU/USD DATA (2003-2014)")
    print("="*80)

    # Load existing data
    if OUTPUT_FILE.exists():
        existing = pd.read_parquet(OUTPUT_FILE)
        existing['time'] = pd.to_datetime(existing['time'])
        existing_min = existing['time'].min()
        existing_max = existing['time'].max()
        print(f"\nExisting data: {existing_min} to {existing_max}")
        print(f"Bars: {len(existing):,}")
    else:
        existing = None
        existing_min = None
        print("\nNo existing data found")

    # Download 2003-2014
    print("\nDownloading 2003-2014 from Dukascopy...")
    print("(This may take 30-60 minutes)")

    new_data = download_historical_range('XAUUSD', start_year=2003, end_year=2014)

    if new_data is None:
        print("\nFailed to download data. Possible reasons:")
        print("  - Dukascopy changed API")
        print("  - Network issue")
        print("  - XAU/USD data not available before 2015")
        return

    # Merge with existing
    if existing is not None:
        print(f"\nMerging {len(new_data):,} new bars with {len(existing):,} existing...")
        combined = pd.concat([new_data.reset_index(), existing], ignore_index=True)
        combined = combined.sort_values('time').drop_duplicates(subset=['time'])
    else:
        combined = new_data.reset_index()

    # Save
    combined.to_parquet(OUTPUT_FILE)

    print(f"\n{'='*80}")
    print("DOWNLOAD COMPLETE")
    print(f"{'='*80}")
    print(f"  Final range: {combined['time'].min()} to {combined['time'].max()}")
    print(f"  Total bars: {len(combined):,}")
    print(f"  File: {OUTPUT_FILE}")
    print(f"  Size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
