"""TCA configuration."""
from pathlib import Path

# DuckDB path
DUCKDB_PATH = Path(__file__).resolve().parents[1] / "data" / "dominion.duckdb"
