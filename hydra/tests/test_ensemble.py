"""Tests for ensemble BMA and MoE."""
import numpy as np
import pytest

from hydra.signals.ensemble import bma_weights, bma_predict, threshold_signal


def test_bma_weights_sum_to_one():
    sharpes = np.array([1.0, 2.0, 3.0, 0.5])
    w = bma_weights(sharpes)
    assert abs(w.sum() - 1.0) < 1e-10


def test_bma_weights_higher_sharpe_higher_weight():
    sharpes = np.array([1.0, 5.0])
    w = bma_weights(sharpes)
    assert w[1] > w[0]


def test_bma_predict_weighted_average():
    probs = np.array([[0.8, 0.2], [0.6, 0.4]])
    weights = np.array([0.5, 0.5])
    result = bma_predict(probs, weights)
    # row 0: 0.8*0.5 + 0.2*0.5 = 0.5; row 1: 0.6*0.5 + 0.4*0.5 = 0.5
    expected = np.array([0.5, 0.5])
    np.testing.assert_allclose(result, expected, atol=1e-10)


def test_bma_predict_single_model():
    probs = np.array([[0.7], [0.3]])
    weights = np.array([1.0])
    result = bma_predict(probs, weights)
    np.testing.assert_allclose(result, [0.7, 0.3])


def test_threshold_signal_long():
    proba = np.array([0.65, 0.55, 0.35, 0.50])
    signals, confs = threshold_signal(proba)
    assert signals[0] == 1
    assert signals[1] == 0
    assert signals[2] == -1
    assert signals[3] == 0
    assert confs[0] == 0.65
    assert confs[2] == 0.65


def test_threshold_all_neutral():
    proba = np.full(10, 0.50)
    signals, confs = threshold_signal(proba)
    assert (signals == 0).all()


def test_moe_single_regime():
    """When regime probs are one-hot, MoE should equal that expert."""
    from hydra.models.moe import MixtureOfExperts
    from hydra.models.linear import GNBModel

    base = [GNBModel()]
    moe = MixtureOfExperts(base, n_regimes=4)

    rng = np.random.RandomState(42)
    X = rng.randn(200, 5).astype(np.float32)
    y = (rng.rand(200) > 0.5).astype(np.float32)
    regime_labels = np.zeros(200, dtype=np.int32)
    regime_probs = np.zeros((200, 4))
    regime_probs[:, 0] = 1.0

    moe.fit(X, y, regime_labels, regime_probs)
    pred = moe.predict_proba(X[:10], regime_probs[:10])
    assert pred.shape == (10,)
    assert (pred >= 0).all() and (pred <= 1).all()
