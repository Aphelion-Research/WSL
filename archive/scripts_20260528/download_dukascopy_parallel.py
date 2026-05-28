"""
Parallel Dukascopy XAU/USD M5 downloader.
Downloads real tick data 2003-2014, aggregates to M5.
Multi-threaded with progress bar and resume capability.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import requests
import lzma
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json
import time
import warnings
warnings.filterwarnings('ignore')

OUTPUT_FILE = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
CHECKPOINT_FILE = Path("data/mt5_history/.download_checkpoint.json")
CACHE_DIR = Path("data/mt5_history/.dukascopy_cache")
CACHE_DIR.mkdir(exist_ok=True, parents=True)


def download_dukascopy_hour(symbol, year, month, day, hour, retry=3):
    """
    Download Dukascopy bi5 file for one hour.
    Returns list of tick dicts or None.
    """
    base_url = "https://datafeed.dukascopy.com/datafeed"
    url = f"{base_url}/{symbol}/{year}/{month:02d}/{day:02d}/{hour:02d}h_ticks.bi5"

    for attempt in range(retry):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                return None

            # Decompress
            decompressed = lzma.decompress(response.content)

            # Parse binary: 20 bytes per tick
            # time_ms (4), ask (4), bid (4), ask_vol (4), bid_vol (4)
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

                # XAU/USD point = 0.001
                point = 0.001
                ask_price = ask * point
                bid_price = bid * point

                base_time = datetime(year, month+1, day, hour)
                tick_time = base_time + timedelta(milliseconds=time_ms)

                ticks.append({
                    'time': tick_time,
                    'ask': ask_price,
                    'bid': bid_price,
                    'ask_volume': ask_vol,
                    'bid_volume': bid_vol,
                })

            return ticks

        except Exception as e:
            if attempt < retry - 1:
                time.sleep(0.5)
            else:
                return None

    return None


def aggregate_ticks_to_m5(ticks):
    """Aggregate tick list to M5 OHLC bars."""
    if not ticks:
        return None

    df = pd.DataFrame(ticks)
    df = df.set_index('time').sort_index()

    # Mid price
    df['mid'] = (df['ask'] + df['bid']) / 2
    df['spread'] = df['ask'] - df['bid']

    # Resample to 5min
    m5 = df.resample('5min').agg({
        'mid': ['first', 'max', 'min', 'last'],
        'spread': 'mean',
        'ask_volume': 'sum',
    })

    m5.columns = ['open', 'high', 'low', 'close', 'spread', 'tick_volume']
    m5 = m5.dropna(subset=['close'])

    if len(m5) == 0:
        return None

    return m5.reset_index()


def download_day(symbol, year, month, day):
    """Download all 24 hours for one day, return M5 bars."""
    day_ticks = []

    for hour in range(24):
        ticks = download_dukascopy_hour(symbol, year, month, day, hour)
        if ticks:
            day_ticks.extend(ticks)

    if not day_ticks:
        return None

    m5_bars = aggregate_ticks_to_m5(day_ticks)
    return m5_bars


def load_checkpoint():
    """Load download progress."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {'completed': [], 'failed': []}


def save_checkpoint(checkpoint):
    """Save download progress."""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f)


def build_task_list(start_year, end_year, checkpoint):
    """Build list of (year, month, day) tuples to download."""
    tasks = []
    completed_set = set(tuple(x) for x in checkpoint['completed'])

    for year in range(start_year, end_year + 1):
        for month in range(12):  # 0-11
            # Days in month
            if month == 11:
                days = 31
            elif month in [3, 5, 8, 10]:
                days = 30
            elif month == 1:
                days = 29 if year % 4 == 0 else 28
            else:
                days = 31

            for day in range(1, days + 1):
                task = (year, month, day)
                if task not in completed_set:
                    tasks.append(task)

    return tasks


def worker_download_day(task, symbol='XAUUSD'):
    """Worker function for parallel download."""
    year, month, day = task

    # Check cache first
    cache_file = CACHE_DIR / f"{year}_{month:02d}_{day:02d}.parquet"
    if cache_file.exists():
        try:
            return pd.read_parquet(cache_file), task, True
        except:
            cache_file.unlink()

    # Download
    m5_bars = download_day(symbol, year, month, day)

    if m5_bars is not None and len(m5_bars) > 0:
        # Cache result
        m5_bars.to_parquet(cache_file)
        return m5_bars, task, True
    else:
        return None, task, False


def main():
    print("="*80)
    print("DUKASCOPY PARALLEL DOWNLOADER - XAU/USD M5 (2003-2014)")
    print("="*80)

    # Check existing
    if OUTPUT_FILE.exists():
        existing = pd.read_parquet(OUTPUT_FILE)
        existing['time'] = pd.to_datetime(existing['time'])
        print(f"\nExisting data: {existing['time'].min().date()} to {existing['time'].max().date()}")
        print(f"Bars: {len(existing):,}")
        print("  (Will replace 2003-2014 synthetic with real Dukascopy ticks)")
    else:
        existing = None
        print("\nNo existing data")

    # Always download 2003-2014 (replace synthetic if present)
    start_year = 2003
    end_year = 2014

    print(f"\nTarget download: {start_year} to {end_year}")

    # Load checkpoint
    checkpoint = load_checkpoint()
    print(f"Checkpoint: {len(checkpoint['completed'])} days completed, {len(checkpoint['failed'])} failed")

    # Build task list
    tasks = build_task_list(start_year, end_year, checkpoint)
    print(f"Tasks to download: {len(tasks)} days")

    if len(tasks) == 0:
        print("\nAll days already downloaded!")
        return

    # Parallel download
    print(f"\nStarting parallel download (16 workers)...")
    print("Progress will be saved. Safe to Ctrl+C and resume later.\n")

    all_data = []
    failed_tasks = []

    with ThreadPoolExecutor(max_workers=16) as executor:
        # Submit all tasks
        futures = {executor.submit(worker_download_day, task): task for task in tasks}

        # Progress bar
        with tqdm(total=len(tasks), desc="Downloading", unit="day") as pbar:
            for future in as_completed(futures):
                task = futures[future]
                try:
                    m5_bars, task_id, success = future.result()

                    if success and m5_bars is not None:
                        all_data.append(m5_bars)
                        checkpoint['completed'].append(list(task_id))

                        # Save checkpoint every 100 tasks
                        if len(checkpoint['completed']) % 100 == 0:
                            save_checkpoint(checkpoint)

                    else:
                        failed_tasks.append(task_id)
                        checkpoint['failed'].append(list(task_id))

                except Exception as e:
                    failed_tasks.append(task)
                    checkpoint['failed'].append(list(task))

                pbar.update(1)

    # Final checkpoint save
    save_checkpoint(checkpoint)

    print(f"\nDownload complete!")
    print(f"  Success: {len(all_data)} days")
    print(f"  Failed: {len(failed_tasks)} days")

    if len(all_data) == 0:
        print("\nNo new data downloaded. Check network or date range.")
        return

    # Combine all downloaded data
    print("\nCombining downloaded bars...")
    new_data = pd.concat(all_data, ignore_index=True)
    new_data = new_data.sort_values('time').drop_duplicates(subset=['time'])

    print(f"  New bars: {len(new_data):,}")
    print(f"  Range: {new_data['time'].min().date()} to {new_data['time'].max().date()}")

    # Merge with existing
    if existing is not None:
        print(f"\nMerging with existing data...")

        # Ensure timezone compatibility
        if pd.api.types.is_datetime64tz_dtype(existing['time']):
            new_data['time'] = pd.to_datetime(new_data['time']).dt.tz_localize('UTC')
        else:
            new_data['time'] = pd.to_datetime(new_data['time']).dt.tz_localize(None)
            existing['time'] = pd.to_datetime(existing['time']).dt.tz_localize(None)

        combined = pd.concat([new_data, existing], ignore_index=True)
        combined = combined.sort_values('time').drop_duplicates(subset=['time'])
    else:
        combined = new_data

    # Save
    print(f"\nSaving to {OUTPUT_FILE}...")
    combined.to_parquet(OUTPUT_FILE)

    print(f"\n{'='*80}")
    print("COMPLETE")
    print(f"{'='*80}")
    print(f"  Final dataset:")
    print(f"    Range: {combined['time'].min().date()} to {combined['time'].max().date()}")
    print(f"    Bars: {len(combined):,}")
    print(f"    File: {OUTPUT_FILE}")
    print(f"    Size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.1f} MB")

    if failed_tasks:
        print(f"\n  {len(failed_tasks)} days failed to download.")
        print(f"  Re-run script to retry failed days.")

    # Clean up checkpoint if 100% complete
    if len(failed_tasks) == 0:
        CHECKPOINT_FILE.unlink(missing_ok=True)
        print(f"\n  Checkpoint cleared (download 100% complete)")


if __name__ == "__main__":
    main()
