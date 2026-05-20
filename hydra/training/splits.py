"""Chronological train/val/OOS splits with embargo and purge.

Implements Agent 1 recommendations:
- Embargo >= horizon_bars to prevent label leakage
- Purge >= max_feature_lookback to prevent feature leakage
- Walk-forward validation if enough data
- No shuffle (chronological only)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from hydra.config import CV, TARGET


@dataclass
class SplitMetadata:
    """Metadata for a single train/val/test split."""

    train_size: int
    val_size: int
    test_size: int
    train_date_range: tuple[str, str]
    val_date_range: tuple[str, str]
    test_date_range: tuple[str, str]
    embargo_bars: int
    purge_bars: int
    total_bars: int


def compute_embargo_purge(
    horizon_bars: int = TARGET.horizon_bars,
    max_feature_lookback: int = 252,  # From FEATURES.ic_window
    safety_margin: int = 12,
) -> tuple[int, int]:
    """Compute safe embargo and purge values (Agent 1 recommendation).

    Embargo: Prevents test labels from using training data
    Purge: Prevents test features from using training data

    Returns:
        (embargo_bars, purge_bars)
    """
    # Agent 1: embargo_bars = max(horizon_bars + safety_margin, 32)
    embargo = max(horizon_bars + safety_margin, 32)

    # Agent 1: purge_bars = max(horizon_bars, max_feature_lookback) + safety_margin
    purge = max(horizon_bars, max_feature_lookback) + safety_margin

    return embargo, purge


class ChronologicalSplit:
    """Walk-forward chronological split with embargo/purge."""

    def __init__(
        self,
        n_splits: int = CV.n_splits,
        train_frac: float = CV.train_frac,
        val_frac: float = CV.val_frac,
        test_frac: float = CV.test_frac,
        embargo_bars: Optional[int] = None,
        purge_bars: Optional[int] = None,
        min_train_size: int = 1000,
        expanding_window: bool = True,
    ):
        """Initialize splitter.

        Args:
            n_splits: Number of walk-forward folds
            train_frac: Fraction for training (if expanding_window=False)
            val_frac: Fraction for validation
            test_frac: Fraction for test/OOS
            embargo_bars: Gap after train before val/test (computed if None)
            purge_bars: Gap after val before test (computed if None)
            min_train_size: Minimum training samples required
            expanding_window: If True, train size grows; else sliding window
        """
        self.n_splits = n_splits
        self.train_frac = train_frac
        self.val_frac = val_frac
        self.test_frac = test_frac
        self.min_train_size = min_train_size
        self.expanding_window = expanding_window

        # Compute safe embargo/purge if not provided
        if embargo_bars is None or purge_bars is None:
            self.embargo_bars, self.purge_bars = compute_embargo_purge()
        else:
            self.embargo_bars = embargo_bars
            self.purge_bars = purge_bars

    def split(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
    ) -> list[tuple[np.ndarray, np.ndarray, np.ndarray, SplitMetadata]]:
        """Generate walk-forward splits.

        Returns:
            List of (train_idx, val_idx, test_idx, metadata) tuples
        """
        n = len(df)

        if n < self.min_train_size + self.embargo_bars + 100:
            raise ValueError(
                f"Insufficient data: {n} rows, need >= {self.min_train_size + self.embargo_bars + 100}"
            )

        # Extract timestamps for metadata
        if timestamp_col in df.columns:
            timestamps = pd.to_datetime(df[timestamp_col])
        else:
            timestamps = pd.date_range("2020-01-01", periods=n, freq="D")

        splits = []

        # Compute fold sizes
        fold_size = n // (self.n_splits + 2)  # Reserve space for val/test

        for k in range(self.n_splits):
            if self.expanding_window:
                # Expanding window: train grows each fold
                train_end = (k + 1) * fold_size + self.min_train_size
            else:
                # Sliding window: train size fixed
                train_start = k * fold_size
                train_end = train_start + int(n * self.train_frac)

            # Embargo after train
            val_start = train_end + self.embargo_bars + self.purge_bars

            # Validation size
            val_size = max(1, int(fold_size * self.val_frac / (1 - self.train_frac)))
            val_end = val_start + val_size

            # Embargo after val
            test_start = val_end + self.embargo_bars

            # Test size
            test_size = max(1, int(fold_size * self.test_frac / (1 - self.train_frac)))
            test_end = test_start + test_size

            # Check bounds
            if test_end > n:
                break

            # Generate indices
            if self.expanding_window:
                train_idx = np.arange(0, train_end)
            else:
                train_idx = np.arange(train_start, train_end)

            val_idx = np.arange(val_start, val_end)
            test_idx = np.arange(test_start, test_end)

            # Metadata
            metadata = SplitMetadata(
                train_size=len(train_idx),
                val_size=len(val_idx),
                test_size=len(test_idx),
                train_date_range=(
                    str(timestamps.iloc[train_idx[0]]),
                    str(timestamps.iloc[train_idx[-1]]),
                ),
                val_date_range=(
                    str(timestamps.iloc[val_idx[0]]),
                    str(timestamps.iloc[val_idx[-1]]),
                ),
                test_date_range=(
                    str(timestamps.iloc[test_idx[0]]),
                    str(timestamps.iloc[test_idx[-1]]),
                ),
                embargo_bars=self.embargo_bars,
                purge_bars=self.purge_bars,
                total_bars=n,
            )

            splits.append((train_idx, val_idx, test_idx, metadata))

        if not splits:
            raise ValueError(
                f"Could not generate any splits with n={n}, embargo={self.embargo_bars}, "
                f"purge={self.purge_bars}, fold_size={fold_size}"
            )

        return splits

    def get_oos_split(
        self,
        df: pd.DataFrame,
        oos_frac: float = 0.15,
        timestamp_col: str = "timestamp",
    ) -> tuple[np.ndarray, np.ndarray, SplitMetadata]:
        """Single train/OOS split for final evaluation.

        Returns:
            (train_idx, oos_idx, metadata)
        """
        n = len(df)
        oos_size = int(n * oos_frac)
        train_end = n - oos_size - self.embargo_bars - self.purge_bars

        if train_end < self.min_train_size:
            raise ValueError(
                f"Insufficient data for OOS split: train_end={train_end}, "
                f"min_train_size={self.min_train_size}"
            )

        train_idx = np.arange(0, train_end)
        oos_start = train_end + self.embargo_bars + self.purge_bars
        oos_idx = np.arange(oos_start, n)

        # Extract timestamps
        if timestamp_col in df.columns:
            timestamps = pd.to_datetime(df[timestamp_col])
        else:
            timestamps = pd.date_range("2020-01-01", periods=n, freq="D")

        metadata = SplitMetadata(
            train_size=len(train_idx),
            val_size=0,
            test_size=len(oos_idx),
            train_date_range=(
                str(timestamps.iloc[train_idx[0]]),
                str(timestamps.iloc[train_idx[-1]]),
            ),
            val_date_range=("", ""),
            test_date_range=(
                str(timestamps.iloc[oos_idx[0]]),
                str(timestamps.iloc[oos_idx[-1]]),
            ),
            embargo_bars=self.embargo_bars,
            purge_bars=self.purge_bars,
            total_bars=n,
        )

        return train_idx, oos_idx, metadata


def validate_split_safety(
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    test_idx: np.ndarray,
    horizon_bars: int = TARGET.horizon_bars,
    embargo_bars: Optional[int] = None,
) -> dict[str, bool]:
    """Validate that split has no temporal leakage.

    Returns dict of safety checks (all must be True)
    """
    if embargo_bars is None:
        embargo_bars, _ = compute_embargo_purge()

    checks = {}

    # Check 1: No overlap between sets
    checks["no_train_val_overlap"] = len(np.intersect1d(train_idx, val_idx)) == 0
    checks["no_train_test_overlap"] = len(np.intersect1d(train_idx, test_idx)) == 0
    checks["no_val_test_overlap"] = len(np.intersect1d(val_idx, test_idx)) == 0

    # Check 2: Chronological order
    checks["chronological_train_val"] = train_idx[-1] < val_idx[0] if len(val_idx) > 0 else True
    checks["chronological_val_test"] = val_idx[-1] < test_idx[0] if len(val_idx) > 0 else True

    # Check 3: Embargo gap sufficient
    if len(val_idx) > 0:
        gap_train_val = val_idx[0] - train_idx[-1]
        checks["embargo_train_val_sufficient"] = gap_train_val >= embargo_bars
    else:
        checks["embargo_train_val_sufficient"] = True

    if len(val_idx) > 0 and len(test_idx) > 0:
        gap_val_test = test_idx[0] - val_idx[-1]
        checks["embargo_val_test_sufficient"] = gap_val_test >= embargo_bars
    else:
        checks["embargo_val_test_sufficient"] = True

    # Check 4: Label horizon doesn't overlap
    if len(val_idx) > 0:
        last_train_label_uses = train_idx[-1] + horizon_bars
        checks["no_label_leakage_train_val"] = last_train_label_uses <= val_idx[0]
    else:
        checks["no_label_leakage_train_val"] = True

    return checks
