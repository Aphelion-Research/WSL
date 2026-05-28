"""Fetch 10 years of XAUUSD M5 data from Dukascopy."""
import requests
import struct
import lzma
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import time
import sys

DATA_DIR = Path("data/dukascopy_daily")
OUTPUT = Path("data/mt5_history/XAUUSD_M5_10yr.parquet")


def fetch_dukascopy_hour(year, month, day, hour):
    url = f"https://datafeed.dukascopy.com/datafeed/XAUUSD/{year}/{month-1:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200 or len(r.content) == 0:
            return None
        data = lzma.decompress(r.content)
        if len(data) == 0:
            return None
        ticks = []
        for i in range(0, len(data), 20):
            chunk = data[i:i+20]
            if len(chunk) < 20:
                break
            t_ms, ask, bid, avol, bvol = struct.unpack('>IIIff', chunk)
            ask_price = ask / 1000.0
            bid_price = bid / 1000.0
            mid = (ask_price + bid_price) / 2.0
            ticks.append({
                'time_ms': t_ms,
                'mid': mid,
                'ask': ask_price,
                'bid': bid_price,
                'spread': ask_price - bid_price,
                'volume': avol + bvol
            })
        return ticks
    except (lzma.LZMAError, requests.exceptions.RequestException):
        return None


def ticks_to_m5(ticks, base_dt):
    if not ticks:
        return None
    df = pd.DataFrame(ticks)
    df['timestamp'] = base_dt + pd.to_timedelta(df['time_ms'], unit='ms')
    df = df.set_index('timestamp')
    ohlcv = df['mid'].resample('5min').ohlc()
    ohlcv.columns = ['open', 'high', 'low', 'close']
    ohlcv['tick_volume'] = df['volume'].resample('5min').count()
    ohlcv['spread'] = df['spread'].resample('5min').mean()
    ohlcv = ohlcv.dropna(subset=['open'])
    return ohlcv


def fetch_day(date):
    daily_file = DATA_DIR / f"{date.strftime('%Y%m%d')}.parquet"
    if daily_file.exists():
        return pd.read_parquet(daily_file)

    all_ticks = []
    for hour in range(24):
        ticks = fetch_dukascopy_hour(date.year, date.month, date.day, hour)
        if ticks:
            base_dt = datetime(date.year, date.month, date.day, hour)
            for t in ticks:
                t['timestamp'] = base_dt + timedelta(milliseconds=t['time_ms'])
            all_ticks.extend(ticks)
        time.sleep(0.05)

    if not all_ticks:
        return None

    df = pd.DataFrame(all_ticks)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.set_index('timestamp')
    ohlcv = df['mid'].resample('5min').ohlc()
    ohlcv.columns = ['open', 'high', 'low', 'close']
    ohlcv['tick_volume'] = df['volume'].resample('5min').count()
    ohlcv['spread'] = df['spread'].resample('5min').mean()
    ohlcv = ohlcv.dropna(subset=['open'])

    if len(ohlcv) > 0:
        ohlcv.to_parquet(daily_file)
    return ohlcv


def main():
    start = datetime(2015, 1, 1)
    end = datetime(2026, 5, 20)

    # Check what we already have
    existing_files = list(DATA_DIR.glob("*.parquet"))
    existing_dates = set()
    for f in existing_files:
        try:
            existing_dates.add(datetime.strptime(f.stem, '%Y%m%d').date())
        except ValueError:
            pass

    print(f"Already have {len(existing_dates)} daily files")

    current = start
    total_bars = 0
    days_fetched = 0
    days_skipped = 0

    while current <= end:
        if current.weekday() >= 5:  # skip weekends
            current += timedelta(days=1)
            continue

        if current.date() in existing_dates:
            current += timedelta(days=1)
            days_skipped += 1
            continue

        result = fetch_day(current)
        days_fetched += 1

        if result is not None and len(result) > 0:
            total_bars += len(result)
            if days_fetched % 20 == 0:
                print(f"  {current.date()} | {len(result)} bars | total new: {total_bars} | days: {days_fetched}")
        else:
            if days_fetched % 50 == 0:
                print(f"  {current.date()} | empty | days: {days_fetched}")

        current += timedelta(days=1)

        # Rate limit
        if days_fetched % 100 == 0:
            time.sleep(1)

    # Concatenate all daily files
    print("\nConcatenating all daily files...")
    all_files = sorted(DATA_DIR.glob("*.parquet"))
    if not all_files:
        print("ERROR: No data fetched!")
        sys.exit(1)

    dfs = []
    for f in all_files:
        try:
            dfs.append(pd.read_parquet(f))
        except Exception:
            continue

    master = pd.concat(dfs, axis=0)
    master = master.sort_index()
    master = master[~master.index.duplicated(keep='first')]
    master.to_parquet(OUTPUT)

    print(f"\nFINAL: {len(master)} M5 bars")
    print(f"Date range: {master.index.min()} to {master.index.max()}")
    print(f"Saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
