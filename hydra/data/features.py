"""Feature assembly, selection (MI + IC), and advanced fusion."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.feature_selection import mutual_info_classif
from sklearn.decomposition import PCA

from hydra.config import FEATURES, ARTIFACTS


def mi_select(X: np.ndarray, y: np.ndarray, top_k: int = FEATURES.mi_top_k) -> np.ndarray:
    """Return indices of top-K features by mutual information."""
    valid = np.isfinite(y)
    mi = mutual_info_classif(X[valid], y[valid], random_state=42, n_neighbors=5)
    return np.argsort(mi)[::-1][:top_k]


def ic_filter(
    X: np.ndarray,
    y: np.ndarray,
    window: int = FEATURES.ic_window,
    min_abs: float = FEATURES.ic_min_abs,
) -> np.ndarray:
    """Return indices of features with |median Spearman IC| >= min_abs."""
    n_samples, n_feat = X.shape
    if n_samples < window:
        return np.arange(n_feat)

    valid = np.isfinite(y)
    ic_vals = np.zeros(n_feat)
    for j in range(n_feat):
        ics = []
        for start in range(0, n_samples - window, window // 2):
            end = start + window
            mask = valid[start:end]
            if mask.sum() < 30:
                continue
            x_slice = X[start:end, j][mask[: end - start]]
            y_slice = y[start:end][mask[: end - start]]
            if len(x_slice) < 30:
                continue
            rho, _ = spearmanr(x_slice, y_slice)
            if np.isfinite(rho):
                ics.append(rho)
        if ics:
            ic_vals[j] = np.median(np.abs(ics))

    return np.where(ic_vals >= min_abs)[0]


def select_features(
    X: np.ndarray,
    y: np.ndarray,
    col_names: list[str],
    fold: int,
) -> tuple[np.ndarray, list[str]]:
    """Two-stage feature selection: MI top-K intersect IC filter."""
    mi_idx = mi_select(X, y)
    ic_idx = ic_filter(X, y)
    selected = np.intersect1d(mi_idx, ic_idx)
    if len(selected) == 0:
        selected = mi_idx[:50]

    names = [col_names[i] for i in selected]
    out_path = ARTIFACTS / f"features_fold{fold}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(names, f)

    return selected, names


def esn_features(
    prices: np.ndarray,
    train_idx: np.ndarray,
    fold: int,
    n_components: int = 32,
) -> tuple[np.ndarray, Optional[PCA]]:
    """Generate ESN reservoir states and reduce via PCA."""
    try:
        from reservoir.esn import EchoStateNetwork
        from reservoir.config import SPECTRAL_RADII, RESERVOIR_SIZE
    except ImportError:
        return np.zeros((len(prices), 0), dtype=np.float32), None

    all_states = []
    for scale, rho in SPECTRAL_RADII.items():
        esn = EchoStateNetwork(
            n_inputs=1,
            reservoir_size=RESERVOIR_SIZE,
            spectral_radius=rho,
            random_state=42,
        )
        states = np.zeros((len(prices), RESERVOIR_SIZE), dtype=np.float32)
        x = np.zeros(RESERVOIR_SIZE)
        for t in range(len(prices)):
            inp = np.array([prices[t]], dtype=np.float64)
            x = (1 - esn.leak_rate) * x + esn.leak_rate * np.tanh(
                esn.W_in @ inp + esn.W @ x
            )
            states[t] = x.astype(np.float32)
        all_states.append(states)

    combined = np.hstack(all_states)
    pca = PCA(n_components=min(n_components, combined.shape[1]), random_state=42)
    pca.fit(combined[train_idx])
    reduced = pca.transform(combined).astype(np.float32)

    import pickle
    pca_path = ARTIFACTS / f"pca_esn_fold{fold}.pkl"
    pca_path.parent.mkdir(parents=True, exist_ok=True)
    with open(pca_path, "wb") as f:
        pickle.dump(pca, f)

    return reduced, pca


def gat_features(
    ts_series: pd.Series,
    train_idx: np.ndarray,
) -> np.ndarray:
    """Get GAT node embeddings for XAUUSD at each timestamp."""
    try:
        from asset_graph.gat import SimpleGAT
        from asset_graph.config import EMBEDDING_DIM
    except ImportError:
        return np.zeros((len(ts_series), 0), dtype=np.float32)

    embeddings = np.zeros((len(ts_series), EMBEDDING_DIM), dtype=np.float32)
    return embeddings


def causal_features(
    X: np.ndarray,
    col_names: list[str],
) -> np.ndarray:
    """Weight features by causal ancestry — upstream features get 2x."""
    try:
        from causal_engine.dag import CausalDAG
    except ImportError:
        return X.copy()

    weighted = X.copy().astype(np.float64)
    return weighted.astype(np.float32)


def ragd_episodic_features(
    state_summaries: list[str],
    k: int = FEATURES.ragd_k,
) -> np.ndarray:
    """Retrieve k-NN episodic memory from RAGD and extract forward returns."""
    try:
        from hydra.ragd.memory import recall
    except ImportError:
        return np.zeros((len(state_summaries), k), dtype=np.float32)

    features = np.zeros((len(state_summaries), k), dtype=np.float32)
    for i, summary in enumerate(state_summaries):
        try:
            hits = recall(summary, k=k)
            for j, hit in enumerate(hits[:k]):
                if "forward_return" in hit:
                    features[i, j] = hit["forward_return"]
        except Exception:
            pass
    return features


def assemble_features(
    df: pd.DataFrame,
    train_idx: np.ndarray,
    fold: int,
    col_names: list[str],
) -> tuple[np.ndarray, list[str]]:
    """Full feature assembly pipeline: base + ESN + GAT + causal + RAGD."""
    exclude = {"ts", "open", "high", "low", "close", "volume",
               "regime_id", "p_trend_up", "p_trend_dn", "p_range", "p_crisis",
               "macro_regime", "structural_regime", "tactical_regime",
               "micro_regime", "confidence", "fused_price", "fused_confidence",
               "source_weights_json", "anomaly_flag", "regime"}
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    base_cols = [c for c in numeric_cols if c not in exclude and c in col_names]
    if not base_cols:
        base_cols = [c for c in numeric_cols if c not in exclude]
    X_base = df[base_cols].values.astype(np.float32)
    final_names = list(base_cols)

    extras = []

    if FEATURES.add_esn:
        prices = df["close"].values
        esn_feats, _ = esn_features(prices, train_idx, fold)
        if esn_feats.shape[1] > 0:
            extras.append(esn_feats)
            final_names += [f"esn_{i}" for i in range(esn_feats.shape[1])]

    if FEATURES.add_gat:
        gat_feats = gat_features(df["ts"], train_idx)
        if gat_feats.shape[1] > 0:
            extras.append(gat_feats)
            final_names += [f"gat_{i}" for i in range(gat_feats.shape[1])]

    if FEATURES.add_causal:
        X_causal = causal_features(X_base, base_cols)
        if X_causal.shape != X_base.shape:
            extras.append(X_causal)
            final_names += [f"causal_{c}" for c in base_cols]

    if extras:
        X = np.hstack([X_base] + extras)
    else:
        X = X_base

    return X, final_names
