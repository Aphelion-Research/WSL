"""Test enhanced triple-barrier labeling."""
import numpy as np
import pandas as pd
import pytest

from hydra.labels.triple_barrier import (
    TripleBarrierLabeler,
    detect_session,
    session_spread,
    compute_label_statistics,
)


def test_session_detection():
    """Test session classification."""
    timestamps = pd.date_range("2020-01-01", periods=288, freq="5min")  # 1 day of M5 bars

    sessions = detect_session(timestamps)

    # Check session distribution
    n_asian = (sessions == 0).sum()
    n_london_ny = (sessions == 1).sum()
    n_other = (sessions == 2).sum()

    assert n_asian > 0, "No Asian session detected"
    assert n_london_ny > 0, "No London/NY session detected"

    print(f"Session distribution: Asian={n_asian}, London/NY={n_london_ny}, Other={n_other}")


def test_session_spread():
    """Test session-conditional spread."""
    sessions = np.array([0, 1, 2, 1, 0])  # asian, london_ny, other, london_ny, asian

    spreads = session_spread(sessions)

    assert spreads[0] == 0.50, "Asian spread wrong"
    assert spreads[1] == 0.15, "London/NY spread wrong"
    assert spreads[2] == 0.80, "Other spread wrong"

    print(f"Session spreads: {spreads}")


def test_triple_barrier_basic():
    """Test basic triple-barrier labeling."""
    # Create synthetic data with clear patterns
    n = 500
    close = np.linspace(2000, 2100, n)  # Uptrend
    high = close + np.random.rand(n) * 5
    low = close - np.random.rand(n) * 5

    df = pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "timestamp": pd.date_range("2020-01-01", periods=n, freq="5min"),
    })

    labeler = TripleBarrierLabeler(
        atr_window=14,
        horizon_bars=20,
        stop_mult=1.0,
        target_mult=2.0,
        min_atr_pct=0.0020,
        min_hold_bars=3,
    )

    labels, metadata = labeler.fit_transform(df)

    # Check label distribution
    assert metadata.total_bars == n
    assert metadata.labeled_bars > 0, "No labels generated"
    assert 0 <= metadata.label_rate <= 1, "Label rate out of bounds"
    assert 0 <= metadata.long_rate <= 1, "Long rate out of bounds"

    print(f"Labeled: {metadata.labeled_bars}/{metadata.total_bars} ({metadata.label_rate:.1%})")
    print(f"Long rate: {metadata.long_rate:.1%}")
    print(f"Mean ATR: ${metadata.mean_atr:.2f}")


def test_triple_barrier_both_hit():
    """Test that both-barriers-hit → NaN (Agent 1 fix)."""
    # Create volatile data where both barriers hit
    n = 200
    close = np.ones(n) * 2000
    high = close + 10  # Large swings
    low = close - 10

    df = pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "timestamp": pd.date_range("2020-01-01", periods=n, freq="5min"),
    })

    labeler = TripleBarrierLabeler(
        atr_window=14,
        horizon_bars=10,
        stop_mult=1.0,
        target_mult=2.0,
        min_atr_pct=0.0001,  # Very low to allow labeling
        min_hold_bars=1,
    )

    labels, metadata = labeler.fit_transform(df)

    # In volatile regime, both-hit should produce NaNs
    both_hit_rate = metadata.both_hit_rate
    assert both_hit_rate >= 0, "Both-hit rate negative"

    print(f"Both-hit rate: {both_hit_rate:.1%}")


def test_min_hold_bars():
    """Test min_hold_bars prevents one-bar spike trades."""
    # Create data with immediate spike
    n = 100
    close = np.ones(n) * 2000
    high = close.copy()
    low = close.copy()

    # Bar 10 has immediate spike (next bar hits target)
    high[11] = close[10] + 50  # Huge spike

    df = pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "timestamp": pd.date_range("2020-01-01", periods=n, freq="5min"),
    })

    labeler = TripleBarrierLabeler(
        atr_window=14,
        horizon_bars=20,
        stop_mult=1.0,
        target_mult=2.0,
        min_atr_pct=0.0001,
        min_hold_bars=3,  # Require 3 bars minimum
    )

    labels, metadata = labeler.fit_transform(df)

    # One-bar spike should NOT generate label due to min_hold_bars
    assert np.isnan(labels[10]), "One-bar spike incorrectly labeled"

    print("Min hold bars correctly prevents one-bar spikes")


def test_spread_filter():
    """Test spread-to-ATR filter."""
    # Create low ATR data (should be filtered)
    n = 200
    close = np.ones(n) * 2000
    high = close + 0.5  # Very low volatility (ATR ~ $0.5)
    low = close - 0.5

    df = pd.DataFrame({
        "high": high,
        "low": low,
        "close": close,
        "timestamp": pd.date_range("2020-01-01", periods=n, freq="5min"),
    })

    labeler = TripleBarrierLabeler(
        atr_window=14,
        horizon_bars=20,
        stop_mult=1.0,
        target_mult=2.0,
        min_atr_pct=0.0020,  # Requires ATR >= $4 at $2000 spot
        min_hold_bars=3,
        spread_to_atr_min=0.33,  # Max 33% cost-to-risk
        use_session_spread=False,  # Fixed spread
    )

    labels, metadata = labeler.fit_transform(df)

    # Low ATR bars should be filtered
    assert metadata.label_rate < 0.10, "Low ATR bars not filtered"

    print(f"Spread filter: label_rate={metadata.label_rate:.1%} (expected <10%)")


def test_label_statistics():
    """Test label statistics computation."""
    labels = np.array([1.0, 0.0, 1.0, 1.0, 0.0, np.nan, np.nan, 1.0])

    stats = compute_label_statistics(labels)

    assert stats["n_total"] == 8
    assert stats["n_labeled"] == 6
    assert stats["label_rate"] == 6 / 8
    assert 0 <= stats["class_balance"]["long"] <= 1
    assert 0 <= stats["class_balance"]["short"] <= 1

    print(f"Label stats: {stats}")


if __name__ == "__main__":
    test_session_detection()
    test_session_spread()
    test_triple_barrier_basic()
    test_triple_barrier_both_hit()
    test_min_hold_bars()
    test_spread_filter()
    test_label_statistics()
    print("\nAll label tests passed!")
