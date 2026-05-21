"""Fast parallel Dukascopy fetch + combine with existing MT5 data."""
import requests
import struct
import lzma
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

DATA_DIR = Path("data/dukascopy_daily")
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT = Path("data/mt5_history/XAUUSD_M5_10yr.parquet")


def fetch_day_data(date):
    daily_file = DATA_DIR / f"{date.strftime('%Y%m%d')}.parquet"
    if daily_file.exists():
        try:
            df = pd.read_parquet(daily_file)
            if len(df) > 0:
                return (date, len(df))
        except Exception:
            pass

    all_ticks = []
    for hour in range(24):
        url = f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{date.year}/{date.month-1:02d}/{date.day:02d}/{hour:02d}h_ticks.bi5"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200 or len(r.content) == 0:
                continue
            data = lzma.decompress(r.content)
            if len(data) == 0:
                continue
            base_dt = datetime(date.year, date.month, date.day, hour)
            for i in range(0, len(data), 20):
                chunk = data[i:i+20]
                if len(chunk) < 20:
                    break
                t_ms, ask, bid, avol, bvol = struct.unpack('>IIIff', chunk)
                ask_price = ask / 1000.0
                bid_price = bid / 1000.0
                mid = (ask_price + bid_price) / 2.0
                ts = base_dt + timedelta(milliseconds=t_ms)
                all_ticks.append((ts, mid, avol + bvol, ask_price - bid_price))
        except (lzma.LZMAError, requests.exceptions.RequestException):
            continue

    if not all_ticks:
        return (date, 0)

    df = pd.DataFrame(all_ticks, columns=['timestamp', 'mid', 'volume', 'spread'])
    df = df.set_index('timestamp')
    ohlcv = df['mid'].resample('5min').ohlc()
    ohlcv.columns = ['open', 'high', 'low', 'close']
    ohlcv['tick_volume'] = df['volume'].resample('5min').count()
    ohlcv['spread'] = df['spread'].resample('5min').mean()
    ohlcv = ohlcv.dropna(subset=['open'])

    if len(ohlcv) > 0:
        ohlcv.to_parquet(daily_file)
    return (date, len(ohlcv))


def main():
    start = datetime(2015, 1, 1)
    end = datetime(2026, 5, 19)

    # Generate all weekday dates
    dates = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            dates.append(current)
        current += timedelta(days=1)

    print(f"Total dates to fetch: {len(dates)}")

    # Check existing
    existing = set()
    for f in DATA_DIR.glob("*.parquet"):
        try:
            existing.add(datetime.strptime(f.stem, '%Y%m%d'))
        except ValueError:
            pass
    print(f"Already have: {len(existing)} files")

    to_fetch = [d for d in dates if d not in existing]
    print(f"Need to fetch: {len(to_fetch)} days")

    # Parallel fetch with 8 threads
    total_bars = 0
    fetched = 0
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_day_data, d): d for d in to_fetch}
        for future in as_completed(futures):
            date, bars = future.result()
            total_bars += bars
            fetched += 1
            if fetched % 100 == 0:
                print(f"  Progress: {fetched}/{len(to_fetch)} days, {total_bars} new bars")

    # Combine all
    print("\nCombining all daily files + existing MT5...")
    all_dfs = []

    # Load Dukascopy daily files
    for f in sorted(DATA_DIR.glob("*.parquet")):
        try:
            df = pd.read_parquet(f)
            if len(df) > 0:
                all_dfs.append(df)
        except Exception:
            continue

    # Also load existing MT5 data
    mt5_file = Path("data/mt5_history/XAUUSD_M5.parquet")
    if mt5_file.exists():
        mt5 = pd.read_parquet(mt5_file)
        if 'time' in mt5.columns:
            mt5['time'] = pd.to_datetime(mt5['time'])
            mt5 = mt5.set_index('time')
        all_dfs.append(mt5)
        print(f"  Added existing MT5: {len(mt5)} rows")

    if not all_dfs:
        print("ERROR: No data!")
        return

    master = pd.concat(all_dfs, axis=0)
    master = master.sort_index()
    master = master[~master.index.duplicated(keep='first')]

    # Standardize columns
    for col in ['open', 'high', 'low', 'close', 'tick_volume', 'spread']:
        if col not in master.columns:
            master[col] = np.nan

    master = master[['open', 'high', 'low', 'close', 'tick_volume', 'spread']]
    master = master.dropna(subset=['close'])

    master.to_parquet(OUTPUT)
    print(f"\nFINAL: {len(master)} M5 bars")
    print(f"Date range: {master.index.min()} to {master.index.max()}")


if __name__ == "__main__":
    main()
