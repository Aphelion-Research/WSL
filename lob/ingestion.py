"""Tick and quote ingestion for LOB."""
import pandas as pd
import numpy as np
import duckdb
from pathlib import Path
from typing import Optional


def load_gold_ticks(db_path: Path, limit: Optional[int] = None) -> pd.DataFrame:
    """Load gold_ticks from DuckDB.

    Args:
        db_path: Path to DuckDB database
        limit: Optional row limit

    Returns:
        DataFrame with columns: timestamp, tick_price, confidence
    """
    conn = duckdb.connect(str(db_path))

    query = "SELECT timestamp, tick_price, confidence FROM gold_ticks ORDER BY timestamp"
    if limit:
        query += f" LIMIT {limit}"

    df = conn.execute(query).fetchdf()
    conn.close()

    return df


def generate_synthetic_quotes(df: pd.DataFrame, spread_bps: float = 2.0) -> pd.DataFrame:
    """Generate synthetic bid/ask from mid prices using fixed spread.

    Args:
        df: DataFrame with 'tick_price' column (mid prices)
        spread_bps: Bid-ask spread in basis points

    Returns:
        DataFrame with bid, ask, bid_size, ask_size columns added
    """
    if df.empty:
        return df

    # Fixed spread approach for synthetic data
    spread_fraction = spread_bps / 10000.0
    half_spread = df['tick_price'] * spread_fraction / 2

    df['bid'] = df['tick_price'] - half_spread
    df['ask'] = df['tick_price'] + half_spread

    # Synthetic sizes (random but realistic)
    np.random.seed(42)
    df['bid_size'] = np.random.uniform(10, 100, size=len(df))
    df['ask_size'] = np.random.uniform(10, 100, size=len(df))

    # Ensure bid < ask
    df['bid'] = df[['bid', 'ask']].min(axis=1) - 0.01
    df['ask'] = df[['bid', 'ask']].max(axis=1) + 0.01

    return df


def compute_roll_spread(prices: pd.Series, window: int = 20) -> float:
    """Compute Roll (1984) implicit spread estimate.

    Roll spread = 2 * sqrt(max(-cov(Δp_t, Δp_{t-1}), 0))

    Args:
        prices: Price series
        window: Rolling window size

    Returns:
        Roll spread estimate
    """
    if len(prices) < window + 1:
        return 0.0

    # Compute price changes
    delta_p = prices.diff()

    # Compute covariance of consecutive changes
    cov = delta_p.rolling(window).cov(delta_p.shift(1)).iloc[-1]

    # Roll spread formula
    spread = 2 * np.sqrt(max(-cov, 0))

    return spread if not np.isnan(spread) else 0.0


def prepare_lob_data(db_path: Path, limit: Optional[int] = None) -> pd.DataFrame:
    """Prepare tick data for LOB processing.

    Loads ticks from gold_ticks, generates synthetic bid/ask quotes.

    Args:
        db_path: Path to DuckDB database
        limit: Optional row limit

    Returns:
        DataFrame ready for LOB state machine
    """
    # Load ticks
    df = load_gold_ticks(db_path, limit=limit)

    if df.empty:
        # Generate minimal synthetic data for testing
        print("WARNING: gold_ticks empty, generating synthetic data")
        timestamps = pd.date_range('2024-01-01', periods=1000, freq='1s')
        prices = 2000 + np.random.randn(1000).cumsum() * 0.5
        df = pd.DataFrame({
            'timestamp': timestamps,
            'tick_price': prices,
            'confidence': 0.8
        })

    # Generate synthetic quotes
    df = generate_synthetic_quotes(df)

    return df
