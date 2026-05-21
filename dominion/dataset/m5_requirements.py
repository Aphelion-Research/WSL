"""
M5 data requirements for HYDRA dataset.
Checks if M5 source exists, otherwise blocks training with exact instructions.
"""
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import duckdb


@dataclass
class M5Status:
    """M5 data availability status."""
    exists: bool
    source: str | None
    rows: int
    date_range: tuple[str, str] | None
    blocker_message: str | None


def check_m5_parquet() -> M5Status:
    """Check for M5 parquet file."""
    m5_path = Path("data/mt5_history/XAUUSD_M5.parquet")

    if not m5_path.exists():
        return M5Status(
            exists=False,
            source=None,
            rows=0,
            date_range=None,
            blocker_message=(
                "M5 DATA MISSING\n"
                "\n"
                "Required: data/mt5_history/XAUUSD_M5.parquet\n"
                "Status: FILE NOT FOUND\n"
                "\n"
                "To generate M5 data:\n"
                "  1. Check if domdata CLI can fetch M5:\n"
                "     domdata xaurates\n"
                "\n"
                "  2. If MT5 broker supports M5, fetch history:\n"
                "     python scripts/fetch_mt5_m5.py\n"
                "\n"
                "  3. OR resample from tick data (if gold_ticks has enough rows):\n"
                "     python scripts/resample_ticks_to_m5.py\n"
                "\n"
                "  4. OR use H1 for smoke testing only (add --allow-smoke flag):\n"
                "     python scripts/build_full_dataset.py --timeframe H1 --allow-smoke\n"
                "\n"
                "Current alternatives:\n"
                "  - data/mt5_history/XAUUSD_H1.parquet EXISTS (50K bars)\n"
                "  - data/mt5_history/XAUUSD_H4.parquet EXISTS (26K bars)\n"
                "  - data/mt5_history/XAUUSD_D1.parquet EXISTS (7K bars)\n"
                "  - DuckDB gold_ticks EXISTS (~2K rows, TOO SMALL for M5 resample)\n"
            )
        )

    # Load and check
    import pandas as pd
    df = pd.read_parquet(m5_path)

    return M5Status(
        exists=True,
        source=str(m5_path),
        rows=len(df),
        date_range=(str(df['time'].min()), str(df['time'].max())),
        blocker_message=None
    )


def check_m5_duckdb() -> M5Status:
    """Check for M5 data in DuckDB."""
    try:
        con = duckdb.connect('data/dominion.duckdb', read_only=True)

        # Check for M5 table
        tables = con.execute("SHOW TABLES").fetchall()
        m5_tables = [t[0] for t in tables if 'm5' in t[0].lower() or '5min' in t[0].lower()]

        if not m5_tables:
            con.close()
            return M5Status(
                exists=False,
                source=None,
                rows=0,
                date_range=None,
                blocker_message="No M5 tables found in DuckDB"
            )

        # Try first M5 table
        table_name = m5_tables[0]
        result = con.execute(f"SELECT COUNT(*) as n, MIN(time) as start, MAX(time) as end FROM {table_name}").fetchone()
        con.close()

        return M5Status(
            exists=True,
            source=f"duckdb://{table_name}",
            rows=result[0],
            date_range=(str(result[1]), str(result[2])),
            blocker_message=None
        )

    except Exception as e:
        return M5Status(
            exists=False,
            source=None,
            rows=0,
            date_range=None,
            blocker_message=f"DuckDB M5 check failed: {e}"
        )


def require_m5_or_block() -> M5Status:
    """
    Check for M5 data. If missing, return blocker status.
    Training must not proceed unless --allow-smoke flag is used.
    """
    # Check parquet first
    status = check_m5_parquet()
    if status.exists:
        return status

    # Check DuckDB fallback
    status = check_m5_duckdb()
    if status.exists:
        return status

    # No M5 data found - return blocker from parquet check (most detailed message)
    return check_m5_parquet()
