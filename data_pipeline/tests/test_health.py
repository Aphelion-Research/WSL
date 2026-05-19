"""Tests for health monitoring."""
import pytest
import pandas as pd
from datetime import datetime, timedelta

from data_pipeline.health.anomaly import AnomalyDetector


def test_anomaly_detector_price():
    """Test price anomaly detection."""
    detector = AnomalyDetector()

    historical = pd.Series([1800.0 + i for i in range(252)])  # Add variation

    # Normal price
    is_flagged, is_quarantined, z_score = detector.detect_price_anomaly(
        1900.0, historical
    )
    assert is_flagged == False
    assert is_quarantined == False

    # Anomalous price (>3σ)
    is_flagged, is_quarantined, z_score = detector.detect_price_anomaly(
        3000.0, historical
    )
    assert is_flagged == True
    assert z_score > 3.0

    # Quarantine threshold (>5σ)
    is_flagged, is_quarantined, z_score = detector.detect_price_anomaly(
        5000.0, historical
    )
    assert is_quarantined == True


def test_anomaly_detector_volume():
    """Test volume anomaly detection."""
    detector = AnomalyDetector()

    historical = pd.Series([1000.0 + i * 10 for i in range(100)])  # Add variation

    # Normal volume
    is_anomaly, z_score = detector.detect_volume_anomaly(1500.0, historical)
    assert is_anomaly == False

    # Anomalous volume (>5σ)
    is_anomaly, z_score = detector.detect_volume_anomaly(10000.0, historical)
    assert is_anomaly == True


def test_source_divergence_detection():
    """Test source divergence detection."""
    detector = AnomalyDetector()

    fused_price = 1800.0
    fused_confidence = 1.0

    # Source agrees
    is_divergent = detector.detect_source_divergence(
        1801.0, fused_price, fused_confidence
    )
    assert is_divergent == False

    # Source diverges (>2σ)
    is_divergent = detector.detect_source_divergence(
        1850.0, fused_price, fused_confidence
    )
    assert is_divergent == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
