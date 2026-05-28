"""Resample M5 to M15 for BOI."""
import pandas as pd
from pathlib import Path


def resample_m5_to_m15(m5: pd.DataFrame) -> pd.DataFrame:
    """Resample M5 bars to M15.

    Args:
        m5: M5 OHLCV DataFrame with DatetimeIndex

    Returns:
        M15 OHLCV DataFrame
    """
    m15 = pd.DataFrame()

    m15['open'] = m5['open'].resample('15min').first()
    m15['high'] = m5['high'].resample('15min').max()
    m15['low'] = m5['low'].resample('15min').min()
    m15['close'] = m5['close'].resample('15min').last()
    m15['tick_volume'] = m5['tick_volume'].resample('15min').sum()

    if 'spread' in m5.columns:
        m15['spread'] = m5['spread'].resample('15min').mean()
    else:
        m15['spread'] = 0.30  # Default spread

    # Drop incomplete bars (NaN)
    m15 = m15.dropna()

    return m15


if __name__ == "__main__":
    # Standalone script to generate M15 from M5
    print("Resampling M5 → M15...")

    m5_path = Path("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
    m15_path = Path("data/mt5_history/XAUUSD_M15.parquet")

    if not m5_path.exists():
        print(f"✗ M5 data not found at {m5_path}")
        exit(1)

    print(f"  Loading {m5_path}...")
    m5 = pd.read_parquet(m5_path)

    if 'time' in m5.columns:
        m5['time'] = pd.to_datetime(m5['time'])
        m5 = m5.set_index('time')

    print(f"  M5: {len(m5):,} bars")

    print(f"  Resampling...")
    m15 = resample_m5_to_m15(m5)

    print(f"  M15: {len(m15):,} bars ({m15.index[0]} to {m15.index[-1]})")

    print(f"  Saving to {m15_path}...")
    m15.to_parquet(m15_path)

    print("✓ Done")
