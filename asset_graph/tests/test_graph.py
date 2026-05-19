"""Tests for asset graph."""
import pytest
import numpy as np
import pandas as pd

from asset_graph.graph import build_correlation_graph, compute_node_centrality


def test_correlation_graph():
    """Test correlation graph construction."""
    np.random.seed(42)

    # Generate correlated data
    n = 100
    x = np.random.randn(n)
    y = x + np.random.randn(n) * 0.1  # Highly correlated
    z = np.random.randn(n)  # Independent

    data = pd.DataFrame({"x": x, "y": y, "z": z})

    adj, weights = build_correlation_graph(data, threshold=0.3)

    # x and y should be connected
    assert adj[0, 1] == 1

    # Edge weights should be in [0, 1]
    for weight in weights.values():
        assert 0 <= weight <= 1


def test_node_centrality():
    """Test centrality computation."""
    # Simple graph: node 0 connected to all others
    adj = np.array([
        [0, 1, 1, 1],
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [1, 0, 0, 0]
    ])

    centrality_0 = compute_node_centrality(adj, 0)
    centrality_1 = compute_node_centrality(adj, 1)

    # Node 0 has degree 3/3 = 1.0
    assert centrality_0 == 1.0

    # Node 1 has degree 1/3 ≈ 0.33
    assert abs(centrality_1 - 1.0/3.0) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
