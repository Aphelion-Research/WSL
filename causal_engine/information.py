"""Transfer entropy and mutual information computation."""
import numpy as np
import pandas as pd
from typing import Tuple, List
from sklearn.feature_selection import mutual_info_regression
from sklearn.neighbors import KNeighborsRegressor

from causal_engine.config import TE_K_NEIGHBORS


def transfer_entropy(
    x: np.ndarray,
    y: np.ndarray,
    k: int = TE_K_NEIGHBORS,
    lag: int = 1
) -> float:
    """Compute transfer entropy from X to Y using k-NN estimator.

    TE(X→Y) = H(Y_t | Y_{t-lag}) - H(Y_t | Y_{t-lag}, X_{t-lag})

    Args:
        x: Source time series
        y: Target time series
        k: Number of neighbors for k-NN
        lag: Time lag

    Returns:
        Transfer entropy (nats)
    """
    if len(x) != len(y):
        raise ValueError("x and y must have same length")

    n = len(y) - lag
    if n < k + 1:
        return 0.0

    # Prepare data
    y_t = y[lag:]
    y_t_lag = y[:-lag]
    x_t_lag = x[:-lag]

    # Compute H(Y_t | Y_{t-lag})
    h_y_given_y = conditional_entropy_knn(y_t, y_t_lag, k)

    # Compute H(Y_t | Y_{t-lag}, X_{t-lag})
    combined = np.column_stack([y_t_lag, x_t_lag])
    h_y_given_yx = conditional_entropy_knn(y_t, combined, k)

    # TE = H(Y|Y) - H(Y|Y,X)
    te = h_y_given_y - h_y_given_yx

    return max(te, 0.0)  # TE should be non-negative


def conditional_entropy_knn(
    y: np.ndarray,
    x: np.ndarray,
    k: int
) -> float:
    """Estimate H(Y|X) using k-NN.

    Approximation: H(Y|X) ≈ -E[log p(y|x)]
    where p(y|x) is estimated via k-NN density estimation.
    """
    if x.ndim == 1:
        x = x.reshape(-1, 1)

    n = len(y)
    if n < k + 1:
        return 0.0

    # Fit k-NN
    knn = KNeighborsRegressor(n_neighbors=k)
    knn.fit(x, y)

    # Predict
    y_pred = knn.predict(x)

    # Residual variance (proxy for conditional entropy)
    residuals = y - y_pred
    var = np.var(residuals)

    if var <= 0:
        return 0.0

    # H(Y|X) ≈ 0.5 * log(2πe * var)
    h = 0.5 * np.log(2 * np.pi * np.e * var)

    return max(h, 0.0)


def compute_all_transfer_entropies(
    data: pd.DataFrame,
    top_n_pairs: int = 20
) -> pd.DataFrame:
    """Compute transfer entropy for top N feature pairs.

    Args:
        data: Feature matrix
        top_n_pairs: Number of pairs to compute (by correlation magnitude)

    Returns:
        DataFrame with columns: source, target, te_score
    """
    features = data.columns.tolist()

    # Compute correlation matrix
    corr_matrix = data.corr().abs()

    # Get top pairs by correlation
    pairs = []
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            pairs.append((features[i], features[j], corr_matrix.iloc[i, j]))

    pairs.sort(key=lambda x: x[2], reverse=True)
    top_pairs = pairs[:top_n_pairs]

    # Compute TE for each pair
    results = []
    for source, target, corr in top_pairs:
        x = data[source].values
        y = data[target].values

        te_forward = transfer_entropy(x, y)
        te_backward = transfer_entropy(y, x)

        results.append({
            'source': source,
            'target': target,
            'te_forward': te_forward,
            'te_backward': te_backward,
            'te_net': te_forward - te_backward,
            'correlation': corr
        })

    return pd.DataFrame(results)


def compute_mutual_information_scores(
    features_df: pd.DataFrame,
    target: pd.Series
) -> pd.Series:
    """Compute mutual information between each feature and target.

    Args:
        features_df: Feature matrix
        target: Target variable (e.g., next-bar gold return)

    Returns:
        Series with MI scores for each feature
    """
    # Remove NaN
    valid_mask = ~(features_df.isna().any(axis=1) | target.isna())
    features_clean = features_df[valid_mask]
    target_clean = target[valid_mask]

    if len(features_clean) < 10:
        return pd.Series(0.0, index=features_df.columns)

    # Compute MI
    mi_scores = mutual_info_regression(
        features_clean.values,
        target_clean.values,
        random_state=42
    )

    return pd.Series(mi_scores, index=features_df.columns)
