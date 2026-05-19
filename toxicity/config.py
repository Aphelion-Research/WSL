"""Toxicity monitor configuration."""
from pathlib import Path

# DuckDB path
DUCKDB_PATH = Path(__file__).resolve().parents[1] / "data" / "dominion.duckdb"

# Alert thresholds
VPIN_THRESHOLD_HIGH = 0.7
VPIN_THRESHOLD_MEDIUM = 0.5
OFI_SIGMA_THRESHOLD = 3.0
ADVERSE_SELECTION_THRESHOLD_BPS = 10.0
TOXICITY_SCORE_THRESHOLD = 0.8
