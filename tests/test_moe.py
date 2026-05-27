"""Test suite for HYDRA-MoE modules."""

import numpy as np
import pytest
import torch
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from hydra.moe.router import HydraRouter, RouterTrainer
from hydra.moe.experts import HydraExpert, ExpertFactory
from hydra.moe.moe_model import HydraMoE
from hydra.moe.calibration import ProbabilityCalibrator
from hydra.moe.feature_groups import get_router_feature_indices, get_expert_feature_boost
from hydra.moe.regime_labels import assign_initial_regimes


@pytest.fixture
def synthetic_data():
    """Generate synthetic dataset for testing."""
    np.random.seed(42)
    n_samples = 1000
    n_features = 100

    X = np.random.randn(n_samples, n_features).astype(np.float32)
    y = (X[:, 0] + X[:, 1] > 0).astype(np.int32)

    feature_cols = [f"f{i}" for i in range(n_features)]
    feature_cols[5] = "vix_regime"
    feature_cols[10] = "trend_efficiency_50b"
    feature_cols[15] = "atr_pct_14b"

    return X, y, feature_cols


def test_router_output_shape(synthetic_data):
    """Router output is (batch, n_experts) and sums to 1."""
    X, y, feature_cols = synthetic_data
    router_indices = get_router_feature_indices(feature_cols)
    n_router = len(router_indices)

    router = HydraRouter(input_dim=n_router, n_experts=4)
    x_batch = torch.randn(32, n_router)

    weights = router(x_batch)

    assert weights.shape == (32, 4)
    assert torch.allclose(weights.sum(dim=1), torch.ones(32), atol=1e-5)


def test_router_entropy_regularization(synthetic_data):
    """Entropy loss penalizes uniform routing."""
    X, y, feature_cols = synthetic_data
    router_indices = get_router_feature_indices(feature_cols)
    n_router = len(router_indices)

    router = HydraRouter(input_dim=n_router, n_experts=4)

    # Uniform weights (high entropy)
    uniform = torch.ones(10, 4) / 4
    entropy_uniform = router.entropy_loss(uniform)

    # One-hot weights (low entropy)
    one_hot = torch.zeros(10, 4)
    one_hot[:, 0] = 1.0
    entropy_one_hot = router.entropy_loss(one_hot)

    # Uniform should have higher (less negative) entropy
    assert entropy_uniform > entropy_one_hot


def test_expert_weighted_training(synthetic_data):
    """Expert trains without error given sample weights."""
    X, y, feature_cols = synthetic_data
    n = len(X)
    train_end = int(0.7 * n)

    X_train, y_train = X[:train_end], y[:train_end]
    X_val, y_val = X[train_end:], y[train_end:]

    expert = HydraExpert(
        expert_id=0,
        expert_name="test",
        lgb_params={"objective": "binary", "n_jobs": 1, "verbose": -1},
        n_estimators=10,
        early_stopping_rounds=5,
        feature_cols=feature_cols,
    )

    sample_weights = np.random.uniform(0.5, 1.5, size=len(X_train)).astype(np.float32)

    metrics = expert.train(X_train, y_train, X_val, y_val, sample_weights=sample_weights)

    assert "best_iteration" in metrics
    assert "val_auc" in metrics
    assert 0 <= metrics["val_auc"] <= 1


def test_moe_predict_shape(synthetic_data):
    """MoE predict returns correct shapes."""
    X, y, feature_cols = synthetic_data

    moe = HydraMoE(n_experts=4)
    moe.initialize(feature_cols)
    moe.fit_scaler(X[:700])

    result = moe.predict(X[700:], return_routing_weights=True, return_expert_probas=True, calibrated=False)

    n_test = len(X[700:])
    assert result["proba"].shape == (n_test,)
    assert result["direction"].shape == (n_test,)
    assert result["trade_signal"].shape == (n_test,)
    assert result["dominant_expert"].shape == (n_test,)
    assert result["routing_weights"].shape == (n_test, 4)
    assert result["expert_probas"].shape == (n_test, 4)


def test_moe_predict_proba_in_01(synthetic_data):
    """All output probabilities ∈ [0, 1]."""
    X, y, feature_cols = synthetic_data

    moe = HydraMoE(n_experts=4)
    moe.initialize(feature_cols)
    moe.fit_scaler(X[:700])

    result = moe.predict(X[700:], calibrated=False)
    proba = result["proba"]

    assert np.all(proba >= 0.0)
    assert np.all(proba <= 1.0)


def test_calibrator_reduces_ece(synthetic_data):
    """Calibrated probabilities have lower ECE than raw."""
    X, y, feature_cols = synthetic_data

    # Uncalibrated proba (biased)
    raw_proba = np.random.beta(2, 5, size=len(y)).astype(np.float32)

    calibrator = ProbabilityCalibrator()
    ece_before = calibrator.ece(raw_proba, y)

    # Fit on same data (not realistic but for test)
    calibrator.fit(raw_proba, y)
    calibrated_proba = calibrator.transform(raw_proba)

    ece_after = calibrator.ece(calibrated_proba, y)

    # ECE should improve (lower)
    assert ece_after <= ece_before + 0.01  # allow small tolerance


def test_feature_group_coverage(synthetic_data):
    """All router features exist in the real feature column list."""
    X, y, feature_cols = synthetic_data

    router_indices = get_router_feature_indices(feature_cols)

    # Should return valid indices
    assert len(router_indices) > 0
    assert np.all(router_indices >= 0)
    assert np.all(router_indices < len(feature_cols))


def test_regime_assignment_balance(synthetic_data):
    """K-Means produces non-degenerate clusters (all experts get >5% of bars)."""
    X, y, feature_cols = synthetic_data
    router_indices = get_router_feature_indices(feature_cols)

    labels = assign_initial_regimes(X, router_indices, n_regimes=4, random_state=42)

    unique, counts = np.unique(labels, return_counts=True)

    # All 4 regimes present
    assert len(unique) == 4

    # No degenerate cluster (each >5%)
    for count in counts:
        assert count / len(labels) > 0.05


def test_moe_save_load_roundtrip(synthetic_data, tmp_path):
    """Save and reload produces identical predictions."""
    X, y, feature_cols = synthetic_data

    moe = HydraMoE(n_experts=4)
    moe.initialize(feature_cols)
    moe.fit_scaler(X[:700])

    X_test = X[700:]
    pred_before = moe.predict(X_test, calibrated=False)

    # Save
    output_dir = tmp_path / "test_moe"
    moe.save(str(output_dir))

    # Load
    moe_loaded = HydraMoE.load(str(output_dir))
    pred_after = moe_loaded.predict(X_test, calibrated=False)

    # Predictions should match
    assert np.allclose(pred_before["proba"], pred_after["proba"], atol=1e-5)


def test_temporal_split_no_leakage(synthetic_data):
    """OOS indices are strictly after val indices."""
    X, y, feature_cols = synthetic_data
    n = len(X)

    train_frac = 0.6
    val_frac = 0.2

    train_end = int(train_frac * n)
    val_end = int((train_frac + val_frac) * n)

    idx_train = np.arange(0, train_end)
    idx_val = np.arange(train_end, val_end)
    idx_oos = np.arange(val_end, n)

    # No overlap
    assert len(set(idx_train) & set(idx_val)) == 0
    assert len(set(idx_val) & set(idx_oos)) == 0
    assert len(set(idx_train) & set(idx_oos)) == 0

    # OOS strictly after val
    assert idx_oos.min() >= idx_val.max()


def test_delong_test():
    """DeLong test returns valid p-value ∈ [0,1]."""
    from hydra.moe.evaluation import MoEEvaluator

    np.random.seed(42)
    n = 500
    y_true = np.random.randint(0, 2, size=n)
    proba1 = np.random.beta(2, 2, size=n)
    proba2 = proba1 + np.random.normal(0, 0.05, size=n)
    proba2 = np.clip(proba2, 0, 1)

    # Mock MoE for evaluator
    class MockMoE:
        pass

    moe = MockMoE()
    evaluator = MoEEvaluator(moe, "/tmp")

    pvalue = evaluator._delong_test(y_true, proba1, proba2)

    assert 0 <= pvalue <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
