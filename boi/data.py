"""Data loading and preprocessing for BOI."""
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from research_core.data_contracts import validate_ohlcv


def load_timeframe(path: Path, name: str) -> Optional[pd.DataFrame]:
    """Load single timeframe data.

    Args:
        path: Path to parquet file
        name: Timeframe name (for logging)

    Returns:
        DataFrame with DatetimeIndex, or None if not found
    """
    if not path.exists():
        print(f"  {name}: Not found at {path}")
        return None

    df = pd.read_parquet(path)

    # Set time column as index if needed
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')
    elif not isinstance(df.index, pd.DatetimeIndex):
        # Index might already be datetime but not DatetimeIndex type
        try:
            df.index = pd.to_datetime(df.index)
        except:
            pass

    # Validate
    try:
        validate_ohlcv(df)
    except Exception as e:
        print(f"  {name}: Validation failed: {e}")
        return None

    # Check if timestamps look valid
    if df.index[0].year < 1990:
        print(f"  {name}: Invalid timestamps (year < 1990), skipping")
        return None

    print(f"  {name}: {len(df):,} bars ({df.index[0]} to {df.index[-1]})")
    return df


def load_all_timeframes(config: Dict) -> Dict[str, pd.DataFrame]:
    """Load all timeframes from config.

    Args:
        config: Config dict with data paths

    Returns:
        Dict of {timeframe: DataFrame}
    """
    print("Loading timeframes...")

    data = {}

    for tf, key in [
        ('m15', 'm15_path'),
        ('m5', 'm5_path'),
        ('h1', 'h1_path'),
        ('h4', 'h4_path'),
        ('d1', 'd1_path'),
    ]:
        path = Path(config['data'].get(key, ''))
        if path.exists():
            df = load_timeframe(path, tf.upper())
            if df is not None:
                data[tf] = df

    if 'm15' not in data:
        raise ValueError("M15 data (decision timeframe) is required")

    return data


def split_by_date(
    df: pd.DataFrame,
    train_start: str,
    train_end: str,
    val_start: str,
    val_end: str,
    oos_start: str,
    oos_end: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split data by date ranges.

    Args:
        df: DataFrame with DatetimeIndex
        train_start, train_end: Train period
        val_start, val_end: Validation period
        oos_start, oos_end: OOS period

    Returns:
        Tuple of (train, val, oos)
    """
    train = df[(df.index >= train_start) & (df.index <= train_end)]
    val = df[(df.index >= val_start) & (df.index <= val_end)]
    oos = df[(df.index >= oos_start) & (df.index <= oos_end)]

    return train, val, oos
