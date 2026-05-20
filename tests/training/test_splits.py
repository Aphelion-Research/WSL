"""Test chronological splits with embargo/purge."""
import numpy as np
import pandas as pd
import pytest

from hydra.training.splits import (
    ChronologicalSplit,
    compute_embargo_purge,
    validate_split_safety,
)


def test_compute_embargo_purge():
    """Test embargo/purge computation."""
    embargo, purge = compute_embargo_purge(
        horizon_bars=20,
        max_feature_lookback=252,
        safety_margin=12,
    )

    # Agent 1 recommendation: embargo >= horizon + safety
    assert embargo >= 20 + 12, f"Embargo {embargo} too small"

    # Purge >= max(horizon, lookback) + safety
    assert purge >= max(20, 252) + 12, f"Purge {purge} too small"


def test_chronological_split_expanding():
    """Test expanding window splits."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=5000, freq="5min"),
        "close": np.random.randn(5000),
    })

    splitter = ChronologicalSplit(
        n_splits=3,
        expanding_window=True,
        embargo_bars=32,
        purge_bars=48,
    )

    splits = splitter.split(df)

    assert len(splits) > 0, "No splits generated"

    for i, (train_idx, val_idx, test_idx, meta) in enumerate(splits):
        # Check no overlap
        assert len(np.intersect1d(train_idx, val_idx)) == 0
        assert len(np.intersect1d(train_idx, test_idx)) == 0
        assert len(np.intersect1d(val_idx, test_idx)) == 0

        # Check chronological order
        assert train_idx[-1] < val_idx[0]
        assert val_idx[-1] < test_idx[0]

        # Check expanding window (train grows)
        if i > 0:
            prev_train_size = splits[i - 1][3].train_size
            assert meta.train_size > prev_train_size

        print(f"Split {i + 1}: train={meta.train_size}, val={meta.val_size}, test={meta.test_size}")


def test_chronological_split_oos():
    """Test single OOS split."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=5000, freq="5min"),
        "close": np.random.randn(5000),
    })

    splitter = ChronologicalSplit(
        embargo_bars=32,
        purge_bars=48,
    )

    train_idx, oos_idx, meta = splitter.get_oos_split(df, oos_frac=0.15)

    # Check sizes
    assert len(train_idx) > 0
    assert len(oos_idx) > 0
    assert len(oos_idx) / len(df) < 0.20  # Roughly 15% OOS

    # Check no overlap
    assert len(np.intersect1d(train_idx, oos_idx)) == 0

    # Check chronological
    assert train_idx[-1] < oos_idx[0]

    # Check embargo
    gap = oos_idx[0] - train_idx[-1]
    assert gap >= 32 + 48

    print(f"OOS split: train={len(train_idx)}, oos={len(oos_idx)}, gap={gap}")


def test_validate_split_safety():
    """Test split safety validation."""
    train_idx = np.arange(0, 1000)
    val_idx = np.arange(1100, 1200)
    test_idx = np.arange(1300, 1400)

    checks = validate_split_safety(
        train_idx, val_idx, test_idx,
        horizon_bars=20,
        embargo_bars=32,
    )

    assert checks["no_train_val_overlap"]
    assert checks["no_train_test_overlap"]
    assert checks["no_val_test_overlap"]
    assert checks["chronological_train_val"]
    assert checks["chronological_val_test"]
    assert checks["embargo_train_val_sufficient"]
    assert checks["embargo_val_test_sufficient"]
    assert checks["no_label_leakage_train_val"]

    print(f"All safety checks passed: {sum(checks.values())}/{len(checks)}")


def test_split_safety_fails_on_overlap():
    """Test split safety catches overlaps."""
    train_idx = np.arange(0, 1000)
    val_idx = np.arange(990, 1100)  # Overlaps with train!
    test_idx = np.arange(1200, 1300)

    checks = validate_split_safety(
        train_idx, val_idx, test_idx,
        horizon_bars=20,
        embargo_bars=32,
    )

    # Should fail chronological check (overlap)
    assert not checks["chronological_train_val"]

    print(f"Correctly detected overlap: {checks}")


def test_split_insufficient_data():
    """Test error handling for insufficient data."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=100, freq="5min"),
        "close": np.random.randn(100),
    })

    splitter = ChronologicalSplit(
        min_train_size=1000,  # Requires more data than available
        embargo_bars=32,
        purge_bars=48,
    )

    with pytest.raises(ValueError, match="Insufficient data"):
        splitter.split(df)


if __name__ == "__main__":
    test_compute_embargo_purge()
    test_chronological_split_expanding()
    test_chronological_split_oos()
    test_validate_split_safety()
    test_split_safety_fails_on_overlap()
    test_split_insufficient_data()
    print("\nAll split tests passed!")
