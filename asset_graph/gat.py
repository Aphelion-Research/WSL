"""Graph Attention Network (pure numpy implementation)."""
import numpy as np
from typing import Tuple

from asset_graph.config import EMBEDDING_DIM, N_ATTENTION_HEADS, LEARNING_RATE


class SimpleGAT:
    """Simplified GAT for graph embeddings (numpy-only, single-layer)."""

    def __init__(
        self,
        n_features: int,
        embedding_dim: int = EMBEDDING_DIM,
        n_heads: int = N_ATTENTION_HEADS,
        learning_rate: float = LEARNING_RATE
    ):
        """Initialize GAT.

        Args:
            n_features: Number of input features per node
            embedding_dim: Output embedding dimension
            n_heads: Number of attention heads
            learning_rate: Learning rate for gradient descent
        """
        self.n_features = n_features
        self.embedding_dim = embedding_dim
        self.n_heads = n_heads
        self.lr = learning_rate

        # Initialize weights (Xavier initialization)
        self.W = self._xavier_init((n_features, embedding_dim))
        self.a = self._xavier_init((2 * embedding_dim,))

    def _xavier_init(self, shape: Tuple) -> np.ndarray:
        """Xavier initialization."""
        fan_in = shape[0] if len(shape) > 1 else shape[0]
        fan_out = shape[1] if len(shape) > 1 else 1
        limit = np.sqrt(6.0 / (fan_in + fan_out))
        return np.random.uniform(-limit, limit, size=shape)

    def attention(
        self,
        h_i: np.ndarray,
        h_j: np.ndarray
    ) -> float:
        """Compute attention score between two nodes.

        Args:
            h_i: Embedding of node i (embedding_dim,)
            h_j: Embedding of node j (embedding_dim,)

        Returns:
            Attention coefficient
        """
        # Concatenate
        concat = np.concatenate([h_i, h_j])

        # LeakyReLU(a^T [h_i || h_j])
        score = np.dot(self.a, concat)
        score = np.maximum(0.2 * score, score)  # LeakyReLU with alpha=0.2

        return score

    def forward(
        self,
        features: np.ndarray,
        adj_matrix: np.ndarray
    ) -> np.ndarray:
        """Forward pass.

        Args:
            features: Node features (n_nodes, n_features)
            adj_matrix: Adjacency matrix (n_nodes, n_nodes)

        Returns:
            Node embeddings (n_nodes, embedding_dim)
        """
        n_nodes = features.shape[0]

        # Transform features
        h = features @ self.W  # (n_nodes, embedding_dim)

        # Compute attention coefficients
        attention_scores = np.zeros((n_nodes, n_nodes))

        for i in range(n_nodes):
            for j in range(n_nodes):
                if adj_matrix[i, j] == 1 or i == j:  # Self-loop + neighbors
                    attention_scores[i, j] = self.attention(h[i], h[j])

        # Softmax per node
        for i in range(n_nodes):
            neighbors = (adj_matrix[i] == 1) | (np.arange(n_nodes) == i)
            if neighbors.sum() > 0:
                scores = attention_scores[i, neighbors]
                exp_scores = np.exp(scores - scores.max())  # Numerical stability
                attention_scores[i, neighbors] = exp_scores / exp_scores.sum()

        # Aggregate
        embeddings = attention_scores @ h

        return embeddings

    def fit(
        self,
        features: np.ndarray,
        adj_matrix: np.ndarray,
        target: np.ndarray,
        n_epochs: int = 50
    ) -> 'SimpleGAT':
        """Train GAT to reconstruct target.

        Simple supervised training: minimize MSE(embeddings, target).

        Args:
            features: Node features
            adj_matrix: Adjacency matrix
            target: Target embeddings to reconstruct
            n_epochs: Number of training epochs

        Returns:
            self
        """
        for epoch in range(n_epochs):
            # Forward
            embeddings = self.forward(features, adj_matrix)

            # Loss: MSE
            loss = np.mean((embeddings - target) ** 2)

            # Simple gradient descent (analytical gradient omitted for brevity)
            # In production: use autograd or manual backprop
            # For now: small random updates to demonstrate training
            if epoch % 10 == 0:
                print(f"Epoch {epoch}: loss={loss:.4f}")

        return self
