"""Column naming contracts to prevent leakage."""

# Forbidden patterns in feature column names
# These indicate forward-looking or outcome-based data
FORBIDDEN_FEATURE_PATTERNS = [
    "label",
    "target",
    "fwd",
    "forward",
    "future",
    "next_",
    "lead_",
    "pnl",
    "profit",
    "outcome",
    "return_",  # forward return
]

# Required OHLCV columns for execution simulation
REQUIRED_OHLCV_COLUMNS = [
    "open",
    "high",
    "low",
    "close",
    "spread",  # Dominion-specific: bid-ask spread in points
]

# Optional but recommended columns
OPTIONAL_OHLCV_COLUMNS = [
    "tick_volume",
    "real_volume",
]
