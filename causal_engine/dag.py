"""DAG construction, storage, and visualization."""
import json
import duckdb
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import requests

from causal_engine.config import DUCKDB_PATH


def init_dag_schema(db_path: Path = DUCKDB_PATH) -> None:
    """Initialize DAG tables in DuckDB."""
    conn = duckdb.connect(str(db_path))

    conn.execute("""
        CREATE TABLE IF NOT EXISTS causal_dag (
            source_feature VARCHAR NOT NULL,
            target_feature VARCHAR NOT NULL,
            edge_type VARCHAR NOT NULL,  -- 'undirected', 'directed', 'bidirected'
            confidence DOUBLE,
            p_value DOUBLE,
            cond_set_json VARCHAR,
            computed_at TIMESTAMP NOT NULL,
            run_id VARCHAR NOT NULL,
            PRIMARY KEY (source_feature, target_feature, run_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS causal_dag_runs (
            run_id VARCHAR PRIMARY KEY,
            computed_at TIMESTAMP NOT NULL,
            n_features INTEGER,
            n_edges INTEGER,
            alpha DOUBLE,
            algorithm VARCHAR DEFAULT 'PC'
        )
    """)

    conn.close()


def store_dag(
    adj_matrix: np.ndarray,
    features: List[str],
    edge_info: Dict,
    run_id: str,
    alpha: float,
    db_path: Path = DUCKDB_PATH
) -> None:
    """Store DAG in DuckDB."""
    conn = duckdb.connect(str(db_path))

    # Count edges
    n_edges = int(np.sum(adj_matrix) / 2)  # Undirected graph

    # Store run metadata
    conn.execute("""
        INSERT INTO causal_dag_runs (run_id, computed_at, n_features, n_edges, alpha)
        VALUES (?, ?, ?, ?, ?)
    """, [run_id, datetime.now(), len(features), n_edges, alpha])

    # Store edges
    edges = []
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            if adj_matrix[i, j] == 1:
                info = edge_info.get((i, j), {})
                p_value = info.get('p_value', 1.0)
                cond_set = info.get('cond_set', [])

                edges.append({
                    'source_feature': features[i],
                    'target_feature': features[j],
                    'edge_type': 'undirected',
                    'confidence': 1.0 - p_value,
                    'p_value': p_value,
                    'cond_set_json': json.dumps(cond_set),
                    'computed_at': datetime.now(),
                    'run_id': run_id
                })

    if edges:
        df = pd.DataFrame(edges)
        conn.execute("""
            INSERT OR REPLACE INTO causal_dag
            SELECT * FROM df
        """)

    conn.close()


def query_causal_predecessors(
    target: str,
    run_id: Optional[str] = None,
    min_confidence: float = 0.5,
    db_path: Path = DUCKDB_PATH
) -> pd.DataFrame:
    """Query which features causally precede target."""
    conn = duckdb.connect(str(db_path))

    if run_id is None:
        # Get latest run
        run_id_query = """
            SELECT run_id FROM causal_dag_runs
            ORDER BY computed_at DESC LIMIT 1
        """
        result = conn.execute(run_id_query).fetchone()
        if not result:
            conn.close()
            return pd.DataFrame()
        run_id = result[0]

    query = """
        SELECT source_feature, target_feature, confidence, p_value
        FROM causal_dag
        WHERE (source_feature = ? OR target_feature = ?)
          AND run_id = ?
          AND confidence >= ?
        ORDER BY confidence DESC
    """

    result = conn.execute(query, [target, target, run_id, min_confidence]).fetchdf()
    conn.close()

    return result


def export_dag_to_json(
    run_id: str,
    db_path: Path = DUCKDB_PATH
) -> Dict:
    """Export DAG as JSON for RAGD storage."""
    conn = duckdb.connect(str(db_path))

    # Get run metadata
    meta_query = """
        SELECT * FROM causal_dag_runs WHERE run_id = ?
    """
    meta = conn.execute(meta_query, [run_id]).fetchdf()

    # Get edges
    edges_query = """
        SELECT * FROM causal_dag WHERE run_id = ?
    """
    edges = conn.execute(edges_query, [run_id]).fetchdf()

    conn.close()

    dag_json = {
        'run_id': run_id,
        'metadata': meta.to_dict('records')[0] if not meta.empty else {},
        'edges': edges.to_dict('records')
    }

    return dag_json


def send_dag_to_ragd(dag_json: Dict, ragd_url: str = "http://127.0.0.1:7474") -> bool:
    """Send DAG to RAGD memory."""
    try:
        response = requests.post(
            f"{ragd_url}/memory/remember",
            json={
                "text": f"Causal DAG computed: {dag_json['metadata'].get('n_edges', 0)} edges among {dag_json['metadata'].get('n_features', 0)} features",
                "tag": "causal_dag",
                "metadata": dag_json
            },
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Failed to send DAG to RAGD: {e}")
        return False


def visualize_dag_ascii(
    adj_matrix: np.ndarray,
    features: List[str],
    max_nodes: int = 10
) -> str:
    """Generate ASCII art visualization of DAG."""
    # Show only top nodes by degree
    degrees = adj_matrix.sum(axis=1)
    top_indices = np.argsort(degrees)[-max_nodes:]

    lines = []
    lines.append("CAUSAL DAG (top {} nodes by degree):".format(max_nodes))
    lines.append("=" * 60)

    for idx in top_indices:
        feature = features[idx]
        neighbors = [features[j] for j in range(len(features))
                    if adj_matrix[idx, j] == 1]

        lines.append(f"{feature:30} → {len(neighbors)} connections")
        if neighbors and len(neighbors) <= 5:
            for neighbor in neighbors[:5]:
                lines.append(f"  └─ {neighbor}")

    return "\n".join(lines)
