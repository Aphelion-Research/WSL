"""Asset graph configuration."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DUCKDB_PATH = REPO_ROOT / "data" / "dominion.duckdb"

# Asset nodes
ASSET_NODES = [
    "gold", "dxy", "vix", "tips_yield", "crude",
    "eurusd", "yield_spread", "cpi", "fed_funds", "gld_etf"
]

# Edge thresholds
CORRELATION_THRESHOLD = 0.3  # |corr| > 0.3 creates edge
GRANGER_P_THRESHOLD = 0.05   # p-value < 0.05 creates edge

# GAT parameters
EMBEDDING_DIM = 64
N_ATTENTION_HEADS = 2
N_GAT_LAYERS = 2
LEARNING_RATE = 0.01
N_EPOCHS = 50

# Graph update frequency
GRAPH_UPDATE_WINDOW = 20  # bars
ROLLING_CORR_WINDOW = 60  # bars for correlation computation
