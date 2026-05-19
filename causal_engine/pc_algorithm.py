"""PC (Peter-Clark) algorithm for causal discovery."""
import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Optional, Set
from scipy.stats import norm
from itertools import combinations

from causal_engine.config import PC_ALPHA, PC_MAX_COND_SET_SIZE


def fisher_z_test(
    data: pd.DataFrame,
    x: str,
    y: str,
    z: Optional[List[str]] = None,
    alpha: float = PC_ALPHA
) -> Tuple[bool, float]:
    """Test conditional independence X ⊥ Y | Z using Fisher's Z-transform.

    Returns:
        (is_independent, p_value)
    """
    if z is None:
        z = []

    # Compute partial correlation
    if len(z) == 0:
        # Zero-order correlation
        corr = data[[x, y]].corr().iloc[0, 1]
    else:
        # Partial correlation
        corr = partial_correlation(data, x, y, z)

    n = len(data)

    # Fisher's Z-transform
    if abs(corr) >= 1.0:
        # Perfect correlation → dependent
        return False, 0.0

    z_score = 0.5 * np.log((1 + corr) / (1 - corr))

    # Standard error
    se = 1.0 / np.sqrt(n - len(z) - 3)

    # Test statistic
    test_stat = abs(z_score) / se

    # Two-tailed p-value
    p_value = 2 * (1 - norm.cdf(test_stat))

    # Independent if p-value > alpha
    is_independent = p_value > alpha

    return is_independent, p_value


def partial_correlation(
    data: pd.DataFrame,
    x: str,
    y: str,
    z: List[str]
) -> float:
    """Compute partial correlation between x and y given z."""
    if not z:
        return data[[x, y]].corr().iloc[0, 1]

    # Regress x on z
    X_z = data[z].values
    x_vals = data[x].values
    y_vals = data[y].values

    # Simple linear regression
    beta_xz = np.linalg.lstsq(X_z, x_vals, rcond=None)[0]
    resid_x = x_vals - X_z @ beta_xz

    beta_yz = np.linalg.lstsq(X_z, y_vals, rcond=None)[0]
    resid_y = y_vals - X_z @ beta_yz

    # Correlation of residuals
    if np.std(resid_x) == 0 or np.std(resid_y) == 0:
        return 0.0

    return np.corrcoef(resid_x, resid_y)[0, 1]


def pc_algorithm(
    data: pd.DataFrame,
    alpha: float = PC_ALPHA,
    max_cond_size: int = PC_MAX_COND_SET_SIZE
) -> Tuple[np.ndarray, Dict]:
    """Run PC algorithm for causal discovery.

    Args:
        data: Feature matrix (n_samples x n_features)
        alpha: Significance level
        max_cond_size: Max conditioning set size

    Returns:
        (adjacency_matrix, edge_info)
        adjacency_matrix: n x n, 1 = edge exists
        edge_info: {(i,j): {'p_value': float, 'cond_set': list}}
    """
    features = data.columns.tolist()
    n_features = len(features)

    # Step 1: Start with complete undirected graph
    adj_matrix = np.ones((n_features, n_features))
    np.fill_diagonal(adj_matrix, 0)

    edge_info = {}

    # Step 2: Remove edges using conditional independence
    for cond_size in range(max_cond_size + 1):
        changed = False

        for i in range(n_features):
            for j in range(i + 1, n_features):
                if adj_matrix[i, j] == 0:
                    continue  # Already removed

                # Find neighbors of i (excluding j)
                neighbors_i = [k for k in range(n_features)
                              if k != j and adj_matrix[i, k] == 1]

                if len(neighbors_i) < cond_size:
                    continue

                # Test all conditioning sets of size cond_size
                for cond_set_idx in combinations(neighbors_i, cond_size):
                    cond_set = [features[k] for k in cond_set_idx]

                    is_indep, p_value = fisher_z_test(
                        data, features[i], features[j], cond_set, alpha
                    )

                    if is_indep:
                        # Remove edge
                        adj_matrix[i, j] = 0
                        adj_matrix[j, i] = 0
                        edge_info[(i, j)] = {
                            'removed': True,
                            'p_value': p_value,
                            'cond_set': cond_set,
                            'cond_size': cond_size
                        }
                        changed = True
                        break

        if not changed:
            break

    # Step 3: Orient edges (simplified — full Meek rules omitted for brevity)
    # For now, keep as undirected skeleton
    # In production: implement v-structure detection + Meek rules

    return adj_matrix, edge_info


def extract_causal_paths(
    adj_matrix: np.ndarray,
    features: List[str],
    target: str,
    max_path_length: int = 3
) -> List[List[str]]:
    """Extract causal paths leading to target feature.

    Args:
        adj_matrix: Adjacency matrix from PC algorithm
        features: Feature names
        target: Target feature name
        max_path_length: Maximum path length to extract

    Returns:
        List of paths, each path is list of feature names
    """
    target_idx = features.index(target)

    paths = []

    def dfs(current_idx: int, path: List[int], visited: Set[int]):
        if len(path) > max_path_length:
            return

        if current_idx == target_idx and len(path) > 1:
            paths.append([features[i] for i in path])
            return

        visited.add(current_idx)

        for next_idx in range(len(features)):
            if next_idx not in visited and adj_matrix[current_idx, next_idx] == 1:
                dfs(next_idx, path + [next_idx], visited)

        visited.remove(current_idx)

    # Start from all nodes
    for start_idx in range(len(features)):
        if start_idx != target_idx:
            dfs(start_idx, [start_idx], set())

    return paths


def compute_causal_strength(
    data: pd.DataFrame,
    source: str,
    target: str,
    adj_matrix: np.ndarray,
    features: List[str]
) -> float:
    """Compute causal strength from source to target.

    Simple approximation: partial correlation controlling for all other connected nodes.
    """
    source_idx = features.index(source)
    target_idx = features.index(target)

    if adj_matrix[source_idx, target_idx] == 0:
        return 0.0

    # Find all neighbors of source (excluding target)
    neighbors = [features[i] for i in range(len(features))
                if i != target_idx and adj_matrix[source_idx, i] == 1]

    if neighbors:
        pcorr = partial_correlation(data, source, target, neighbors)
    else:
        pcorr = data[[source, target]].corr().iloc[0, 1]

    return abs(pcorr)
