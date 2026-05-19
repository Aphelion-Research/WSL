"""Tests for Kalman fusion."""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from data_pipeline.fusion.kalman import KalmanFilter, KalmanFilterBank
from data_pipeline.fusion.bridge import brownian_bridge
from data_pipeline.fusion.conflict import resolve_conflict, detect_anomaly


def test_kalman_filter_converges():
    """Test Kalman filter converges on known signal."""
    kf = KalmanFilter(process_noise=0.01, observation_noise=0.1)

    # Generate noisy observations of constant 100
    true_price = 100.0
    observations = [true_price + np.random.normal(0, 0.1) for _ in range(100)]

    for obs in observations:
        filtered, uncertainty, innovation = kf.update(obs)

    # Should converge near true price
    assert abs(filtered - true_price) < 1.0

    # Uncertainty should decrease
    assert uncertainty < 1.0


def test_kalman_filter_bank_trust_update():
    """Test trust score updates correctly."""
    bank = KalmanFilterBank()

    bank.init_trust("source_a", 0.5)

    # Good innovation -> trust increases
    bank.update_trust("source_a", innovation=0.1, uncertainty=1.0)
    assert bank.trust_scores["source_a"] > 0.5

    # Bad innovation -> trust decreases
    bank.update_trust("source_a", innovation=5.0, uncertainty=1.0)
    assert bank.trust_scores["source_a"] < 0.5


def test_brownian_bridge_respects_ohlc():
    """Test Brownian bridge stays within OHLC bounds."""
    open_price = 1800.0
    high_price = 1820.0
    low_price = 1790.0
    close_price = 1810.0

    start_time = datetime(2025, 1, 1, 10, 0)
    end_time = datetime(2025, 1, 1, 10, 1)

    ticks = brownian_bridge(
        open_price, high_price, low_price, close_price,
        start_time, end_time, n_ticks=100
    )

    # First tick should be open
    assert ticks[0][1] == open_price

    # Last tick should be close
    assert ticks[-1][1] == close_price

    # All ticks should be within [low, high]
    prices = [t[1] for t in ticks]
    assert min(prices) >= low_price * 0.99  # Allow small epsilon
    assert max(prices) <= high_price * 1.01


def test_conflict_resolution_quarantine():
    """Test conflict resolution quarantines 3σ outlier."""
    observations = {
        "source_a": 1800.0,
        "source_b": 1801.0,
        "source_c": 1900.0,  # Outlier
    }

    fused_price = 1800.5
    confidence = 1.0
    trust_scores = {"source_a": 0.8, "source_b": 0.8, "source_c": 0.5}

    final_price, quarantine_flag, quarantined = resolve_conflict(
        observations, fused_price, confidence, trust_scores
    )

    assert quarantine_flag == True
    assert quarantined == "source_c"


def test_anomaly_detection():
    """Test anomaly detection via z-score."""
    historical = pd.Series([1800.0 + i for i in range(100)])  # Add variation

    # Normal price
    is_anomaly, z_score = detect_anomaly(1850.0, historical.mean(), historical.std())
    assert is_anomaly == False

    # Anomalous price
    is_anomaly, z_score = detect_anomaly(3000.0, historical.mean(), historical.std())
    assert is_anomaly == True
    assert z_score > 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
