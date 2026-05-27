"""Unsupervised regime assignment for expert initialization."""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler
from loguru import logger


def assign_initial_regimes(
    X: np.ndarray,
    router_indices: np.ndarray,
    n_regimes: int = 4,
    method: str = "kmeans",
    random_state: int = 42,
) -> np.ndarray:
    """Cluster bars into regime groups using router features only.

    Args:
        X: Full feature matrix (n_samples, n_features).
        router_indices: Indices of router features in X.
        n_regimes: Number of regime clusters (must match K experts).
        method: "kmeans" or "gmm".
        random_state: Random seed.

    Returns:
        Hard regime labels (n_samples,) in {0, 1, 2, 3}.
    """
    X_router = X[:, router_indices].copy()
    X_router = np.nan_to_num(X_router, nan=0.0, posinf=0.0, neginf=0.0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_router)

    if method == "gmm":
        model = GaussianMixture(n_components=n_regimes, random_state=random_state, n_init=3)
        labels = model.fit_predict(X_scaled)
    else:
        model = KMeans(n_clusters=n_regimes, random_state=random_state, n_init=10)
        labels = model.fit_predict(X_scaled)

    labels = _reorder_clusters(labels, X_router, router_indices, n_regimes)

    unique, counts = np.unique(labels, return_counts=True)
    for u, c in zip(unique, counts):
        logger.info(f"  Regime {u}: {c:,} bars ({100*c/len(labels):.1f}%)")

    return labels


def _reorder_clusters(
    labels: np.ndarray,
    X_router: np.ndarray,
    router_indices: np.ndarray,
    n_regimes: int,
) -> np.ndarray:
    """Reorder cluster IDs to match semantic regime names.

    Heuristic based on centroid properties:
        - Highest volatility → Crisis/Vol (3)
        - Highest trend efficiency + positive returns → Trend-Up (0)
        - Highest trend efficiency + negative returns → Trend-Down (1)
        - Lowest trend efficiency + low vol → Mean-Revert (2)
    """
    centroids = np.array([X_router[labels == k].mean(axis=0) for k in range(n_regimes)])
    n_features = X_router.shape[1]

    # Compute scores for each cluster
    vol_score = np.zeros(n_regimes)
    trend_score = np.zeros(n_regimes)
    ret_score = np.zeros(n_regimes)

    for i in range(n_features):
        centroid_col = centroids[:, i]
        # No column name access — use position-based heuristic on centroid variance
        vol_score += np.abs(centroid_col) * 0.01

    # Use variance of each cluster as volatility proxy
    for k in range(n_regimes):
        cluster_data = X_router[labels == k]
        vol_score[k] = cluster_data.std(axis=0).mean()
        trend_score[k] = np.abs(cluster_data.mean(axis=0)).mean()
        ret_score[k] = cluster_data.mean(axis=0).sum()

    # Assignment by ranking
    mapping = {}
    remaining = list(range(n_regimes))

    # Crisis: highest vol_score
    crisis_idx = remaining[np.argmax([vol_score[i] for i in remaining])]
    mapping[crisis_idx] = 3
    remaining.remove(crisis_idx)

    # Trend-Up: highest ret_score among remaining
    trend_up_idx = remaining[np.argmax([ret_score[i] for i in remaining])]
    mapping[trend_up_idx] = 0
    remaining.remove(trend_up_idx)

    # Trend-Down: lowest ret_score among remaining
    trend_down_idx = remaining[np.argmin([ret_score[i] for i in remaining])]
    mapping[trend_down_idx] = 1
    remaining.remove(trend_down_idx)

    # Mean-Revert: whatever is left
    mapping[remaining[0]] = 2

    new_labels = np.array([mapping[l] for l in labels], dtype=np.int32)
    return new_labels


def get_soft_regime_weights(
    X: np.ndarray,
    router_indices: np.ndarray,
    n_regimes: int = 4,
    sigma: float = 1.0,
    random_state: int = 42,
) -> np.ndarray:
    """Compute soft routing weights via RBF kernel on cluster distances.

    Args:
        X: Full feature matrix.
        router_indices: Indices of router features.
        n_regimes: Number of clusters.
        sigma: RBF bandwidth parameter.
        random_state: Random seed.

    Returns:
        Soft weights array (n_samples, n_regimes) summing to 1 per row.
    """
    X_router = X[:, router_indices].copy()
    X_router = np.nan_to_num(X_router, nan=0.0, posinf=0.0, neginf=0.0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_router)

    kmeans = KMeans(n_clusters=n_regimes, random_state=random_state, n_init=10)
    kmeans.fit(X_scaled)

    # Compute distances to each centroid
    distances = np.zeros((len(X_scaled), n_regimes))
    for k in range(n_regimes):
        diff = X_scaled - kmeans.cluster_centers_[k]
        distances[:, k] = np.sqrt((diff ** 2).sum(axis=1))

    # RBF kernel
    weights = np.exp(-(distances ** 2) / (2 * sigma ** 2))

    # Normalize to simplex
    row_sums = weights.sum(axis=1, keepdims=True)
    row_sums = np.maximum(row_sums, 1e-10)
    weights = weights / row_sums

    return weights.astype(np.float32)
