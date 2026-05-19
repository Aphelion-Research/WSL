"""Exec features configuration."""
from pathlib import Path

# DuckDB path
DUCKDB_PATH = Path(__file__).resolve().parents[1] / "data" / "dominion.duckdb"

# IC thresholds
IC_STRONG_THRESHOLD = 0.03  # Strong short-term predictor
IC_DECAY_THRESHOLD = 0.5  # 50% drop triggers alert

# Feature windows
ROLLING_WINDOW_SHORT = 20
ROLLING_WINDOW_LONG = 252
