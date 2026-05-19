"""Dynamic heterogeneous graph construction."""
import numpy as np
import pandas as pd
import duckdb
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

from asset_graph.config import (
    DUCKDB_PATH, ASSET_NODES, CORRELATION_THRESHOLD,
    GRANGER_P_THRESHOLD, ROLLING_CORR_WINDOW
)


def init_graph_schema(db_path: Path = DUCKDB_PATH) -> None:
    """Initialize asset graph tables."""
    conn = duckdb.connect(str(db_path))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS asset_graph_edges (
            timestamp TIMESTAMP NOT NULL,
            source_node VARCHAR NOT NULL,
            target_node VARCHAR NOT NULL,
            edge_type VARCHAR NOT NULL,  -- 'correlation', 'causal', 'granger'
            weight DOUBLE NOT NULL,
            window_bars INTEGER,
            PRIMARY KEY (timestamp, source_node, target_node, edge_type)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS asset_embeddings (
            timestamp TIMESTAMP NOT NULL,
            node VARCHAR NOT NULL,
            embedding_json VARCHAR NOT NULL,
            computed_at TIMESTAMP NOT NULL,
            PRIMARY KEY (timestamp, node)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS graph_metrics (
            timestamp TIMESTAMP PRIMARY KEY,
            gold_centrality DOUBLE,
            gold_isolation_score DOUBLE,
            n_edges INTEGER,
            avg_edge_weight DOUBLE
        )
    """)

    conn.close()


def build_correlation_graph(
    data: pd.DataFrame,
    threshold: float = CORRELATION_THRESHOLD
) -> Tuple[np.ndarray, Dict]:
    """Build graph from correlation matrix.

    Args:
        data: DataFrame with asset prices (columns = assets)
        threshold: Correlation threshold for edge creation

    Returns:
        (adjacency_matrix, edge_weights)
    """
    # Compute correlation
    corr = data.corr().abs()

    # Create adjacency matrix
    adj = (corr > threshold).astype(int).values.copy()  # Make writable copy
    np.fill_diagonal(adj, 0)

    # Edge weights
    edge_weights = {}
    for i in range(len(data.columns)):
        for j in range(i + 1, len(data.columns)):
            if adj[i, j] == 1:
                edge_weights[(i, j)] = corr.iloc[i, j]

    return adj, edge_weights


def store_graph_snapshot(
    adj_matrix: np.ndarray,
    node_names: List[str],
    edge_weights: Dict,
    timestamp: datetime,
    edge_type: str = "correlation",
    window_bars: int = None,
    db_path: Path = DUCKDB_PATH
) -> None:
    """Store graph snapshot in DuckDB."""
    conn = duckdb.connect(str(db_path))

    edges = []
    for (i, j), weight in edge_weights.items():
        edges.append({
            'timestamp': timestamp,
            'source_node': node_names[i],
            'target_node': node_names[j],
            'edge_type': edge_type,
            'weight': weight,
            'window_bars': window_bars
        })

    if edges:
        df = pd.DataFrame(edges)
        conn.execute("""
            INSERT OR REPLACE INTO asset_graph_edges
            SELECT * FROM df
        """)

    conn.close()


def compute_node_centrality(adj_matrix: np.ndarray, node_idx: int) -> float:
    """Compute degree centrality for a node."""
    return adj_matrix[node_idx].sum() / (len(adj_matrix) - 1)


def compute_isolation_score(
    adj_matrix: np.ndarray,
    node_idx: int,
    edge_weights: Dict
) -> float:
    """Compute isolation score (inverse of average edge weight).

    Higher score = more isolated.
    """
    weights = [w for (i, j), w in edge_weights.items()
              if i == node_idx or j == node_idx]

    if not weights:
        return 1.0  # Fully isolated

    avg_weight = np.mean(weights)
    return 1.0 - avg_weight  # Invert so high = isolated


def store_graph_metrics(
    adj_matrix: np.ndarray,
    node_names: List[str],
    edge_weights: Dict,
    timestamp: datetime,
    db_path: Path = DUCKDB_PATH
) -> None:
    """Store graph-level metrics."""
    conn = duckdb.connect(str(db_path))

    # Find gold index
    try:
        gold_idx = node_names.index("gold")
    except ValueError:
        gold_idx = 0  # Default

    gold_centrality = compute_node_centrality(adj_matrix, gold_idx)
    gold_isolation = compute_isolation_score(adj_matrix, gold_idx, edge_weights)
    n_edges = int(adj_matrix.sum() / 2)
    avg_edge_weight = np.mean(list(edge_weights.values())) if edge_weights else 0.0

    conn.execute("""
        INSERT OR REPLACE INTO graph_metrics
        (timestamp, gold_centrality, gold_isolation_score, n_edges, avg_edge_weight)
        VALUES (?, ?, ?, ?, ?)
    """, [timestamp, gold_centrality, gold_isolation, n_edges, avg_edge_weight])

    conn.close()
