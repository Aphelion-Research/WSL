#!/usr/bin/env python3
"""Resumable parallel Dukascopy XAUUSD M5 fetcher."""
import requests
import struct
import lzma
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import csv

DATA_DIR = Path("data/dukascopy_daily")
DATA_DIR.mkdir(parents=True, exist_ok=True)
FAILED_LOG = DATA_DIR / "failed_days.csv"
OUTPUT = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")

START_DATE = datetime(2015, 1, 1)
END_DATE = datetime(2026, 5, 20)
THREADS = 8
RETRY_LIMIT = 3


def fetch_hour(year, month, day, hour):
    """Fetch one hour of ticks from Dukascopy."""
    url = f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{year}/{month-1:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200 or len(r.content) == 0:
            return None
        data = lzma.decompress(r.content)
        if len(data) == 0:
            return None

        base_ts = datetime(year, month, day, hour)
        ticks = []
        for i in range(0, len(data), 20):
            chunk = data[i:i+20]
            if len(chunk) < 20:
                break
            t_ms, ask_raw, bid_raw, avol, bvol = struct.unpack('>IIIff', chunk)
            ask = ask_raw / 1000.0
            bid = bid_raw / 1000.0
            mid = (ask + bid) / 2.0
            ts = base_ts + timedelta(milliseconds=t_ms)
            ticks.append((ts, mid, avol + bvol, ask - bid))
        return ticks
    except (lzma.LZMAError, requests.exceptions.RequestException):
        return None


def fetch_day(date, retry=0):
    """Fetch one day, return M5 bars or None."""
    daily_file = DATA_DIR / f"{date.strftime('%Y%m%d')}.parquet"
    if daily_file.exists():
        try:
            df = pd.read_parquet(daily_file)
            if len(df) > 0:
                return ('cached', date, len(df))
        except:
            daily_file.unlink()

    all_ticks = []
    failed_hours = 0
    for hour in range(24):
        ticks = fetch_hour(date.year, date.month, date.day, hour)
        if ticks:
            all_ticks.extend(ticks)
        else:
            failed_hours += 1
        time.sleep(0.05)

    if not all_ticks or len(all_ticks) < 10:
        if retry < RETRY_LIMIT:
            time.sleep(1)
            return fetch_day(date, retry + 1)
        return ('failed', date, 0)

    df = pd.DataFrame(all_ticks, columns=['timestamp', 'mid', 'volume', 'spread'])
    df = df.set_index('timestamp')
    ohlcv = df['mid'].resample('5min').ohlc()
    ohlcv.columns = ['open', 'high', 'low', 'close']
    ohlcv['tick_volume'] = df['volume'].resample('5min').count()
    ohlcv['spread'] = df['spread'].resample('5min').mean()
    ohlcv = ohlcv.dropna(subset=['open'])

    if len(ohlcv) > 0:
        ohlcv.to_parquet(daily_file)
        return ('success', date, len(ohlcv))
    else:
        if retry < RETRY_LIMIT:
            time.sleep(1)
            return fetch_day(date, retry + 1)
        return ('failed', date, 0)


def main():
    print("="*60)
    print("DUKASCOPY XAUUSD M5 FETCHER")
    print("="*60)

    # Find existing
    existing = set()
    for f in DATA_DIR.glob("*.parquet"):
        try:
            d = datetime.strptime(f.stem, '%Y%m%d')
            existing.add(d.date())
        except ValueError:
            pass
    print(f"Already cached: {len(existing)} days")

    # Generate date range
    dates = []
    current = START_DATE
    while current <= END_DATE:
        if current.weekday() < 5:  # skip weekends
            if current.date() not in existing:
                dates.append(current)
        current += timedelta(days=1)

    print(f"Need to fetch: {len(dates)} days")
    if len(dates) == 0:
        print("Nothing to fetch, combining cached files...")
    else:
        print(f"Using {THREADS} threads\n")

        total_success = 0
        total_failed = 0
        total_bars = 0
        failed_dates = []

        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = {executor.submit(fetch_day, d): d for d in dates}
            completed = 0

            for future in as_completed(futures):
                status, date, bars = future.result()
                completed += 1

                if status == 'success':
                    total_success += 1
                    total_bars += bars
                elif status == 'failed':
                    total_failed += 1
                    failed_dates.append(date)

                if completed % 100 == 0:
                    print(f"  Progress: {completed}/{len(dates)} | Success: {total_success} | Failed: {total_failed} | Bars: {total_bars}")

        print(f"\nFetch complete:")
        print(f"  Success: {total_success}")
        print(f"  Failed:  {total_failed}")
        print(f"  Bars:    {total_bars}")

        if failed_dates:
            with open(FAILED_LOG, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['date'])
                for d in sorted(failed_dates):
                    writer.writerow([d.strftime('%Y-%m-%d')])
            print(f"  Failed days logged: {FAILED_LOG}")

    # Combine all daily files
    print("\nCombining all cached daily files...")
    all_files = sorted(DATA_DIR.glob("*.parquet"))
    all_files = [f for f in all_files if f.name != "failed_days.csv"]
    print(f"  Found {len(all_files)} daily files")

    dfs = []
    for f in all_files:
        try:
            df = pd.read_parquet(f)
            if len(df) > 0:
                dfs.append(df)
        except:
            continue

    if not dfs:
        print("ERROR: No data!")
        return

    master = pd.concat(dfs, axis=0)
    master = master.sort_index()
    master = master[~master.index.duplicated(keep='first')]

    # Add required columns
    master['time'] = master.index
    master['real_volume'] = 0.0

    # Standardize column order
    master = master[['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume']]
    master['timestamp'] = pd.to_datetime(master['time'])

    # Validate
    dups = master.duplicated(subset=['time']).sum()
    gaps = 0
    if len(master) > 1:
        time_diffs = master['timestamp'].diff()
        expected = pd.Timedelta('5min')
        gaps = (time_diffs > expected * 1.5).sum()

    master.to_parquet(OUTPUT, index=False)

    print("\n" + "="*60)
    print("RESULT")
    print("="*60)
    print(f"Source:      Dukascopy")
    print(f"Rows:        {len(master)}")
    print(f"Date range:  {master['timestamp'].min()} to {master['timestamp'].max()}")
    print(f"Duplicates:  {dups}")
    print(f"Gaps (>7m):  {gaps}")
    print(f"Output:      {OUTPUT}")
    print(f"Failed days: {total_failed if len(dates) > 0 else 0}")
    print(f"Target 500K: {'YES' if len(master) >= 500000 else 'NO'}")
    print("="*60)


if __name__ == "__main__":
    main()
