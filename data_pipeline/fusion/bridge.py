"""Brownian bridge tick reconstruction from OHLCV bars."""
import numpy as np
import pandas as pd
from typing import List, Tuple
from datetime import datetime, timedelta


def brownian_bridge(
    open_price: float,
    high_price: float,
    low_price: float,
    close_price: float,
    start_time: datetime,
    end_time: datetime,
    n_ticks: int = 100,
    sigma: float = 0.01,
) -> List[Tuple[datetime, float, float]]:
    """Reconstruct synthetic ticks via Brownian bridge.

    Generates a path that:
    - Starts at open_price
    - Ends at close_price
    - Passes through high_price and low_price
    - Follows Brownian bridge dynamics

    Args:
        open_price: Bar open
        high_price: Bar high
        low_price: Bar low
        close_price: Bar close
        start_time: Bar start timestamp
        end_time: Bar end timestamp
        n_ticks: Number of synthetic ticks to generate
        sigma: Volatility parameter

    Returns:
        List of (timestamp, price, confidence) tuples
    """
    if n_ticks < 4:
        n_ticks = 4

    # Time grid
    dt = (end_time - start_time).total_seconds() / n_ticks
    times = [start_time + timedelta(seconds=i * dt) for i in range(n_ticks + 1)]

    # Generate base Brownian bridge path
    # W(t) = O + (C-O)*t/T + sqrt(t*(T-t)/T) * σ * Z(t)
    T = n_ticks
    path = np.zeros(n_ticks + 1)
    path[0] = open_price
    path[-1] = close_price

    # Generate path
    for i in range(1, n_ticks):
        t = i
        mu = open_price + (close_price - open_price) * (t / T)
        std = sigma * np.sqrt((t * (T - t)) / T)
        path[i] = np.random.normal(mu, std)

    # Ensure high and low are reached
    # Insert high at random time in first half
    high_idx = np.random.randint(1, n_ticks // 2)
    path[high_idx] = high_price

    # Insert low at random time in second half
    low_idx = np.random.randint(n_ticks // 2, n_ticks)
    path[low_idx] = low_price

    # Smooth transitions around high/low
    for idx in [high_idx, low_idx]:
        if idx > 0 and idx < n_ticks:
            path[idx - 1] = (path[idx - 1] + path[idx]) / 2
            if idx < n_ticks - 1:
                path[idx + 1] = (path[idx + 1] + path[idx]) / 2

    # Compute confidence scores based on distance from extrema
    confidence = np.ones(n_ticks + 1) * 0.5
    confidence[0] = 1.0  # Open is exact
    confidence[-1] = 1.0  # Close is exact
    confidence[high_idx] = 1.0  # High is exact
    confidence[low_idx] = 1.0  # Low is exact

    # Package as list of tuples
    ticks = [(times[i], path[i], confidence[i]) for i in range(n_ticks + 1)]

    return ticks


def reconstruct_ticks_from_bars(df: pd.DataFrame, n_ticks: int = 100) -> pd.DataFrame:
    """Reconstruct synthetic ticks from OHLCV bars.

    Args:
        df: DataFrame with columns: timestamp, open, high, low, close
        n_ticks: Number of ticks per bar

    Returns:
        DataFrame with columns: timestamp, bar_timestamp, tick_price, confidence
    """
    all_ticks = []

    for idx, row in df.iterrows():
        bar_timestamp = row["timestamp"]
        open_price = row["open"]
        high_price = row["high"]
        low_price = row["low"]
        close_price = row["close"]

        # Assume 1-minute bars if not specified
        start_time = bar_timestamp
        end_time = bar_timestamp + timedelta(minutes=1)

        ticks = brownian_bridge(
            open_price, high_price, low_price, close_price,
            start_time, end_time, n_ticks
        )

        for tick_time, tick_price, tick_conf in ticks:
            all_ticks.append({
                "timestamp": tick_time,
                "bar_timestamp": bar_timestamp,
                "tick_price": tick_price,
                "confidence": tick_conf,
            })

    return pd.DataFrame(all_ticks)
