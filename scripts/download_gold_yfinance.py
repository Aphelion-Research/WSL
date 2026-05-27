"""
Download XAU/USD historical data from Yahoo Finance.
Fast, free, extends back to ~2000.
Then merge with existing Dukascopy M5 data.
"""
import pandas as pd
import yfinance as yf
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

OUTPUT_FILE = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
DAILY_OUTPUT = Path("data/mt5_history/XAUUSD_daily_yfinance.parquet")


def download_gold_daily(start_date='2000-01-01', end_date='2026-12-31'):
    """Download daily XAU/USD from Yahoo Finance."""
    print(f"Downloading XAU/USD daily data from {start_date} to {end_date}...")

    # Yahoo Finance ticker for gold
    ticker = yf.Ticker("GC=F")  # Gold Futures

    # Download
    df = ticker.history(start=start_date, end=end_date, interval='1d')

    if df.empty:
        print("Failed to download. Trying alternate ticker...")
        # Try spot gold
        ticker = yf.Ticker("GOLD")
        df = ticker.history(start=start_date, end=end_date, interval='1d')

    if df.empty:
        raise ValueError("Could not download gold data from yfinance")

    # Clean
    df = df.reset_index()
    df = df.rename(columns={
        'Date': 'time',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume',
    })

    df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
    df['time'] = pd.to_datetime(df['time'])

    return df


def expand_daily_to_m5(daily_df):
    """
    Expand daily OHLC to M5 bars (synthetic).
    Uses linear interpolation between daily OHLC points.
    NOT as accurate as real tick data, but extends history.
    """
    print("\nExpanding daily bars to M5 (synthetic)...")

    all_m5 = []

    for _, row in daily_df.iterrows():
        date = row['time']
        o, h, l, c = row['open'], row['high'], row['low'], row['close']

        # Generate 24h of M5 bars (288 bars per day)
        # Market hours: use 00:00-23:55 UTC (forex runs 24/5)
        # Skip weekends
        if date.dayofweek >= 5:
            continue

        # Simple synthetic: distribute OHLC across day
        # Hour 0-8: move from O to L
        # Hour 8-16: move from L to H
        # Hour 16-24: move from H to C

        bars_per_section = 96  # 8 hours × 12 bars/hour

        section_1_prices = pd.Series([o] + list(pd.Series([o, l]).interpolate(method='linear', limit_area='inside')[1:-1]) + [l] * (bars_per_section - 2))
        section_2_prices = pd.Series([l] + list(pd.Series([l, h]).interpolate(method='linear', limit_area='inside')[1:-1]) + [h] * (bars_per_section - 2))
        section_3_prices = pd.Series([h] + list(pd.Series([h, c]).interpolate(method='linear', limit_area='inside')[1:-1]) + [c] * (bars_per_section - 2))

        # Concatenate
        all_prices = pd.concat([section_1_prices, section_2_prices, section_3_prices]).reset_index(drop=True)

        # Generate timestamps
        start_time = pd.Timestamp(date)
        times = [start_time + pd.Timedelta(minutes=i*5) for i in range(288)]

        # Build M5 bars (use price as all OHLC for simplicity)
        for i, t in enumerate(times):
            price = all_prices.iloc[i] if i < len(all_prices) else c
            all_m5.append({
                'time': t,
                'open': price,
                'high': price * 1.0001,  # tiny spread
                'low': price * 0.9999,
                'close': price,
                'tick_volume': 10,  # placeholder
                'spread': price * 0.0001,
            })

    m5_df = pd.DataFrame(all_m5)
    return m5_df


def main():
    print("="*80)
    print("DOWNLOAD XAU/USD HISTORICAL DATA")
    print("="*80)

    # Check existing
    if OUTPUT_FILE.exists():
        existing = pd.read_parquet(OUTPUT_FILE)
        existing['time'] = pd.to_datetime(existing['time'])
        print(f"\nExisting M5 data: {existing['time'].min().date()} to {existing['time'].max().date()}")
        print(f"  Bars: {len(existing):,}")
        oldest_existing = existing['time'].min()
    else:
        existing = None
        oldest_existing = pd.Timestamp('2026-01-01')
        print("\nNo existing M5 data")

    # Download daily from yfinance
    print("\n" + "-"*80)
    print("METHOD: Yahoo Finance (instant, free)")
    print("-"*80)

    daily_df = download_gold_daily(start_date='2000-01-01', end_date=oldest_existing.strftime('%Y-%m-%d'))

    print(f"  Downloaded: {len(daily_df)} daily bars")
    print(f"  Range: {daily_df['time'].min().date()} to {daily_df['time'].max().date()}")

    # Save daily data separately
    daily_df.to_parquet(DAILY_OUTPUT)
    print(f"  Saved daily: {DAILY_OUTPUT}")

    # Option 1: Use daily as-is (for daily models)
    # Option 2: Expand to M5 (synthetic, less accurate)

    print("\n" + "-"*80)
    print("EXPANDING DAILY → M5 (SYNTHETIC)")
    print("-"*80)
    print("Note: Synthetic M5 bars are interpolated from daily OHLC.")
    print("      Less accurate than real tick data, but extends history.")

    m5_synthetic = expand_daily_to_m5(daily_df)
    print(f"  Generated: {len(m5_synthetic):,} M5 bars")

    # Merge with existing
    if existing is not None:
        print(f"\nMerging synthetic ({len(m5_synthetic):,}) with real M5 ({len(existing):,})...")
        # Ensure same timezone
        if pd.api.types.is_datetime64tz_dtype(existing['time']):
            m5_synthetic['time'] = pd.to_datetime(m5_synthetic['time']).dt.tz_localize('UTC')
        else:
            m5_synthetic['time'] = pd.to_datetime(m5_synthetic['time']).dt.tz_localize(None)
            existing['time'] = pd.to_datetime(existing['time']).dt.tz_localize(None)

        combined = pd.concat([m5_synthetic, existing], ignore_index=True)
        combined = combined.sort_values('time').drop_duplicates(subset=['time'])
        combined = combined.reset_index(drop=True)
    else:
        combined = m5_synthetic

    # Save
    combined.to_parquet(OUTPUT_FILE)

    print(f"\n{'='*80}")
    print("COMPLETE")
    print(f"{'='*80}")
    print(f"  Final M5 dataset:")
    print(f"    Range: {combined['time'].min().date()} to {combined['time'].max().date()}")
    print(f"    Bars: {len(combined):,}")
    print(f"    File: {OUTPUT_FILE}")
    print(f"    Size: {OUTPUT_FILE.stat().st_size / 1024 / 1024:.1f} MB")
    print(f"\n  Breakdown:")
    print(f"    2000-2014: Synthetic (yfinance daily expanded)")
    print(f"    2015-2026: Real tick data (Dukascopy M5)")


if __name__ == "__main__":
    main()
