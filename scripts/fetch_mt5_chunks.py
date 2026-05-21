#!/usr/bin/env python3
"""Fetch XAUUSD M5 history in chunks via domdata."""
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path
import time

CHUNK = 50000
MAX_CHUNKS = 100
OUTPUT = Path("data/mt5_history/XAUUSD_M5_expanded.parquet")
TMP_DIR = Path("/tmp/mt5_chunks")
TMP_DIR.mkdir(exist_ok=True)

def fetch_chunk(start_pos, count):
    """Fetch one chunk via domdata."""
    tmp = TMP_DIR / f"chunk_{start_pos}_{count}.csv"
    if tmp.exists():
        try:
            df = pd.read_csv(tmp)
            if len(df) > 0:
                return df
        except:
            pass

    cmd = [
        "domdata", "rates-pos", "XAUUSD", "M5",
        str(start_pos), str(count),
        "--format", "csv", "--out", str(tmp)
    ]
    try:
        result = subprocess.run(cmd, timeout=120, capture_output=True, text=True)
        if tmp.exists() and tmp.stat().st_size > 0:
            df = pd.read_csv(tmp)
            if len(df) > 0:
                return df
    except:
        pass
    return None

def main():
    print("Fetching M5 bars in chunks from MT5...")
    all_dfs = []
    total = 0
    start_pos = 0

    for i in range(MAX_CHUNKS):
        print(f"  Chunk {i+1}: start_pos={start_pos}, count={CHUNK}...", end=" ", flush=True)
        df = fetch_chunk(start_pos, CHUNK)

        if df is None or len(df) == 0:
            print("empty, stopping")
            break

        df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
        all_dfs.append(df)
        total += len(df)
        print(f"{len(df)} rows (total: {total})")

        if len(df) < CHUNK:
            print(f"  Got {len(df)} < {CHUNK}, reached end")
            break

        start_pos += CHUNK
        time.sleep(0.5)

    if not all_dfs:
        print("ERROR: No data fetched!")
        return

    print(f"\nCombining {len(all_dfs)} chunks...")
    master = pd.concat(all_dfs, ignore_index=True)
    master = master.sort_values('timestamp')
    master = master.drop_duplicates(subset=['timestamp'], keep='first')

    print(f"  Before dedup: {sum(len(df) for df in all_dfs)} rows")
    print(f"  After dedup:  {len(master)} rows")
    print(f"  Range: {master['timestamp'].min()} to {master['timestamp'].max()}")

    master.to_parquet(OUTPUT, index=False)
    print(f"\nSaved: {OUTPUT}")
    print(f"Rows: {len(master)}")
    print(f"Columns: {list(master.columns)}")

if __name__ == "__main__":
    main()
