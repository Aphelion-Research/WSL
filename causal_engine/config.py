"""Causal engine configuration."""
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
DUCKDB_PATH = REPO_ROOT / "data" / "dominion.duckdb"

# PC algorithm parameters
PC_ALPHA = 0.05  # Significance level for independence tests
PC_MAX_COND_SET_SIZE = 3  # Maximum conditioning set size
PC_TOP_N_FEATURES = 50  # Number of top features (by IC) to include in causal graph

# Transfer entropy parameters
TE_K_NEIGHBORS = 5  # k-NN for entropy estimation
TE_TOP_N_PAIRS = 20  # Number of top feature pairs to compute TE for

# Compute frequency
CAUSAL_COMPUTE_FREQUENCY_DAYS = 7  # Run causal discovery weekly
