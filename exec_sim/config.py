"""Execution simulator configuration."""
from pathlib import Path

# DuckDB path
DUCKDB_PATH = Path(__file__).resolve().parents[1] / "data" / "dominion.duckdb"

# Almgren-Chriss impact parameters
IMPACT_GAMMA = 0.0001  # permanent impact coefficient (bps per unit of daily volume)
IMPACT_ETA = 0.142  # temporary impact coefficient (bps)
IMPACT_DELTA = 0.6  # temporary impact exponent

# Strategy defaults
DEFAULT_SLICE_INTERVAL_MIN = 5  # minutes
DEFAULT_POV_TARGET = 0.10  # 10% participation rate
