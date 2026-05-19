"""LOB configuration."""
from pathlib import Path

# DuckDB path
DUCKDB_PATH = Path(__file__).resolve().parents[1] / "data" / "dominion.duckdb"

# LOB parameters
SNAPSHOT_INTERVAL = 100  # snapshots every N ticks
BOOK_DEPTH = 10  # levels per side

# Metric windows
OFI_WINDOW_1S = 1  # seconds
OFI_WINDOW_5S = 5
OFI_WINDOW_1M = 60

# VPIN parameters
VPIN_BUCKETS = 50  # buckets per day
VPIN_WINDOW = 50  # rolling window for VPIN

# Spread parameters
ROLL_WINDOW = 20  # bars for Roll spread
