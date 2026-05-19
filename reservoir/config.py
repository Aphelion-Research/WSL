"""Reservoir configuration."""
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
DUCKDB_PATH = REPO_ROOT / "data" / "dominion.duckdb"

# ESN parameters (reduced for 32GB RAM)
RESERVOIR_SIZE = 3000  # Reduced from 5000
SPECTRAL_RADII = {
    "fast": 0.5,
    "medium": 0.9,
    "slow": 0.99
}
LEAK_RATES = {
    "fast": 0.1,
    "medium": 0.3,
    "slow": 0.7
}
SPARSITY = 0.1  # 10% connections
INPUT_SCALING = 0.1
WASHOUT_STEPS = 100

# Readout parameters
RIDGE_ALPHAS = [1e-6, 1e-4, 1e-2, 1.0, 10.0]  # Cross-validation grid
TRAIN_SPLIT = 0.8  # 80% train, 20% test

# Feature selection
TOP_N_FEATURES_ESN = 100  # Top features by IC for ESN input
