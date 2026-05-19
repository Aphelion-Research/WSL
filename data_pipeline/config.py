"""Pipeline configuration: paths, API endpoints, constants."""
import os
from pathlib import Path
from datetime import datetime

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
DUCKDB_PATH = REPO_ROOT / "data" / "dominion.duckdb"
REPORTS_DIR = REPO_ROOT / "reports"
DOMDATA_CLI = REPO_ROOT / "domdata" / "domdata.py"

# API keys
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
FRED_API_KEY = os.getenv("FRED_API_KEY")

# RAGD endpoint
RAGD_URL = "http://127.0.0.1:7474"

# Source configurations
YAHOO_TICKERS = ["GC=F", "GLD"]
YAHOO_DAILY_PERIOD = "5y"
YAHOO_HOURLY_PERIOD = "60d"

FRED_SERIES = {
    "DGS10": "10-year Treasury yield",
    "DGS2": "2-year Treasury yield",
    "DFII10": "10-year TIPS yield",
    "DTWEXBGS": "Dollar index (DXY proxy)",
    "VIXCLS": "VIX",
    "DCOILWTICO": "WTI Crude oil",
    "CPIAUCSL": "CPI inflation",
    "FEDFUNDS": "Fed funds rate",
    "T10Y2Y": "10Y-2Y yield spread",
    "T10YIEM": "10-year breakeven inflation",
}
FRED_YEARS = 5

ALPHAVANTAGE_RATE_LIMIT_DELAY = 13  # seconds between requests (free tier: 25/day)
ALPHAVANTAGE_SYMBOLS = ["GLD"]

# COT data
COT_URLS = {
    2022: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2022.zip",
    2023: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2023.zip",
    2024: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2024.zip",
    2025: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2025.zip",  # May 404 if not yet available
    2026: "https://www.cftc.gov/files/dea/history/fut_fin_xls_2026.zip",  # May 404 if not yet available
}
COT_GOLD_CODE = "088691"  # COMEX gold futures

# Kalman filter bank parameters
KALMAN_FILTERS = {
    "tick": {"process_noise": 0.001, "observation_noise": 0.1},
    "m1": {"process_noise": 0.01, "observation_noise": 0.5},
    "m15": {"process_noise": 0.05, "observation_noise": 1.0},
    "h1": {"process_noise": 0.1, "observation_noise": 2.0},
    "h4": {"process_noise": 0.2, "observation_noise": 3.0},
    "d1": {"process_noise": 0.5, "observation_noise": 5.0},
}

# Feature computation windows
FEATURE_WINDOWS = [5, 10, 20, 50, 100, 252]
IC_WINDOW = 252  # bars for IC computation

# Health monitoring thresholds
STALENESS_THRESHOLDS = {
    "yahoo": 24 * 3600,  # 24 hours
    "fred": 48 * 3600,  # 48 hours
    "alphavantage": 24 * 3600,
    "cot": 8 * 24 * 3600,  # 8 days (weekly report)
    "mt5": 3600,  # 1 hour
}

ANOMALY_Z_SCORE_FLAG = 3.0
ANOMALY_Z_SCORE_QUARANTINE = 5.0
DRIFT_KL_THRESHOLD = 2.0

# Brownian bridge parameters
TICKS_PER_BAR = 100

# FOMC meeting dates 2026 (for Fed proximity feature)
FOMC_DATES_2026 = [
    datetime(2026, 1, 28),
    datetime(2026, 3, 17),
    datetime(2026, 4, 28),
    datetime(2026, 6, 16),
    datetime(2026, 7, 28),
    datetime(2026, 9, 22),
    datetime(2026, 11, 3),
    datetime(2026, 12, 15),
]
