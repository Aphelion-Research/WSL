#!/usr/bin/env python3
"""
Fetch XAUUSD M5 history via domdata CLI and save to parquet.
"""
import subprocess
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

OUTPUT_PATH = Path("data/mt5_history/XAUUSD_M5.parquet")

def fetch_m5_batch(start_pos: int, count: int) -> list[dict]:
    """Fetch one batch of M5 bars via domdata."""
    result = subprocess.run(
        ["domdata", "rates-pos", "XAUUSD", "M5", str(start_pos), str(count)],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode != 0:
        raise RuntimeError(f"domdata failed: {result.stderr}")

    return json.loads(result.stdout)


def fetch_all_m5(max_bars: int = 500_000, batch_size: int = 10_000) -> pd.DataFrame:
    """Fetch all available M5 bars."""
    print(f"Fetching M5 history (max {max_bars} bars, batch size {batch_size})...")

    all_bars = []
    start_pos = 0

    while start_pos < max_bars:
        print(f"  Fetching bars {start_pos} to {start_pos + batch_size}...", end=" ", flush=True)

        try:
            batch = fetch_m5_batch(start_pos, batch_size)
        except RuntimeError as e:
            print(f"FAILED: {e}")
            break

        if not batch or len(batch) == 0:
            print("No more data")
            break

        all_bars.extend(batch)
        print(f"OK ({len(batch)} bars)")

        # Stop if we got less than requested (end of history)
        if len(batch) < batch_size:
            break

        start_pos += batch_size

    print(f"\nTotal bars fetched: {len(all_bars)}")

    if len(all_bars) == 0:
        raise RuntimeError("No M5 data available")

    # Convert to DataFrame
    df = pd.DataFrame(all_bars)

    # Convert time to datetime
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)

    # Sort by time (newest first from domdata, reverse to oldest first)
    df = df.sort_values('time').reset_index(drop=True)

    return df


def validate_m5_data(df: pd.DataFrame) -> dict:
    """Validate M5 data quality."""
    print("\nValidating M5 data...")

    errors = []

    # Check columns
    required_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume']
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing columns: {missing_cols}")

    # Check duplicates
    if df['time'].duplicated().any():
        dup_count = df['time'].duplicated().sum()
        errors.append(f"Duplicate timestamps: {dup_count}")

    # Check OHLC validity
    invalid_high = (df['high'] < df[['open', 'close']].max(axis=1)).sum()
    invalid_low = (df['low'] > df[['open', 'close']].min(axis=1)).sum()
    invalid_prices = (df['close'] <= 0).sum()

    if invalid_high > 0:
        errors.append(f"Invalid high: {invalid_high} bars")
    if invalid_low > 0:
        errors.append(f"Invalid low: {invalid_low} bars")
    if invalid_prices > 0:
        errors.append(f"Invalid prices (<=0): {invalid_prices} bars")

    # Check date range
    date_range = (df['time'].max() - df['time'].min()).days / 365.25
    if date_range < 1.0:
        errors.append(f"Date range too small: {date_range:.1f} years")

    # Stats
    stats = {
        'rows': len(df),
        'start_date': str(df['time'].min()),
        'end_date': str(df['time'].max()),
        'years': round(date_range, 1),
        'valid': len(errors) == 0,
        'errors': errors
    }

    # Print
    print(f"  Rows: {stats['rows']:,}")
    print(f"  Date range: {stats['start_date'][:10]} to {stats['end_date'][:10]}")
    print(f"  Years: {stats['years']}")

    if errors:
        print(f"  ❌ VALIDATION FAILED:")
        for err in errors:
            print(f"    - {err}")
    else:
        print(f"  ✓ VALIDATION PASSED")

    return stats


def main():
    print("=" * 80)
    print("XAUUSD M5 HISTORY FETCH")
    print("=" * 80)
    print()

    # Fetch
    df = fetch_all_m5(max_bars=500_000, batch_size=10_000)

    # Validate
    stats = validate_m5_data(df)

    if not stats['valid']:
        print("\n❌ M5 data validation failed. Not saving.")
        return 1

    # Save
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, index=False)

    file_size_mb = OUTPUT_PATH.stat().st_size / 1024 / 1024

    print(f"\n✓ M5 data saved to: {OUTPUT_PATH}")
    print(f"  Size: {file_size_mb:.1f} MB")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")
    print(f"  Date range: {stats['start_date'][:10]} to {stats['end_date'][:10]}")
    print(f"  Years: {stats['years']}")

    print("\n" + "=" * 80)
    print("M5 FETCH COMPLETE")
    print("=" * 80)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
