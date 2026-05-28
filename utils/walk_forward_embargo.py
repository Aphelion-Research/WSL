"""
Walk-Forward Fold Creation with Proper Embargo
===============================================
Fixes label leakage across train/val/test boundaries by enforcing embargo gaps.

Problem: If label at bar T uses shift(-N) to look N bars forward, last N bars
of train have labels computed using val/test data = leakage.

Solution: Add embargo gap = max(label_horizon, hold_bars, feature_lookback)
between train/val and val/test boundaries.
"""
import numpy as np
import pandas as pd
from typing import List, Dict


def create_walk_forward_folds_with_embargo(
    df: pd.DataFrame,
    train_months: int = 12,
    val_months: int = 3,
    test_months: int = 3,
    step_months: int = 3,
    embargo_bars: int = 252,
) -> List[Dict]:
    """Create walk-forward folds with embargo gaps to prevent label leakage.

    Args:
        df: DataFrame with 'ts' timestamp column
        train_months: Number of months for training
        val_months: Number of months for validation
        test_months: Number of months for testing
        step_months: Step size for rolling window
        embargo_bars: Embargo gap in bars (default 252 = 21 hours for M5)
            Should be: max(label_horizon, max_hold_bars, max_feature_lookback)

    Returns:
        List of fold dicts with train/val/test indices and embargo gaps

    Example:
        ```
        # For M5 model:
        # - Label horizon: 12 bars (1 hour)
        # - Max hold: 96 bars (8 hours)
        # - Feature lookback: 252 bars (21 hours for rolling stats)
        # → embargo_bars = 252

        folds = create_walk_forward_folds_with_embargo(
            df, embargo_bars=252
        )
        ```

    Timeline with embargo:
        [-------- TRAIN --------][EMBARGO][--- VAL ---][EMBARGO][--- TEST ---]
        ^                       ^         ^            ^        ^
        |                       |         |            |        |
        train_start         train_end  val_start  val_end  test_start

    Embargo prevents:
        1. Train labels from using val data
        2. Val labels from using test data
        3. Feature lookback from crossing boundaries
    """
    df = df.sort_values("ts").reset_index(drop=True)
    df["year_month"] = pd.to_datetime(df["ts"]).dt.to_period("M")
    months = sorted(df["year_month"].unique())
    n_months = len(months)

    folds = []
    start_idx = train_months

    while start_idx + val_months + test_months <= n_months:
        # Month boundaries (no embargo yet)
        train_end_month = months[start_idx - 1]
        val_start_month = months[start_idx]
        val_end_month = months[start_idx + val_months - 1]
        test_start_month = months[start_idx + val_months]
        test_end_month = months[start_idx + val_months + test_months - 1]

        # Get bar indices for each month boundary
        train_mask_raw = df["year_month"] <= train_end_month
        val_mask_raw = (df["year_month"] >= val_start_month) & (df["year_month"] <= val_end_month)
        test_mask_raw = (df["year_month"] >= test_start_month) & (df["year_month"] <= test_end_month)

        train_idx_raw = np.where(train_mask_raw.values)[0]
        val_idx_raw = np.where(val_mask_raw.values)[0]
        test_idx_raw = np.where(test_mask_raw.values)[0]

        if len(train_idx_raw) == 0 or len(val_idx_raw) == 0 or len(test_idx_raw) == 0:
            start_idx += step_months
            continue

        # Apply embargo: remove last N bars from train, first N bars from val/test
        train_end_idx = train_idx_raw[-1]
        val_start_idx = val_idx_raw[0]
        val_end_idx = val_idx_raw[-1]
        test_start_idx = test_idx_raw[0]

        # Embargo between train and val
        train_embargo_cutoff = train_end_idx - embargo_bars
        val_embargo_start = val_start_idx + embargo_bars

        # Embargo between val and test
        val_embargo_cutoff = val_end_idx - embargo_bars
        test_embargo_start = test_start_idx + embargo_bars

        # Apply embargos
        train_idx = train_idx_raw[train_idx_raw <= train_embargo_cutoff]
        val_idx = val_idx_raw[(val_idx_raw >= val_embargo_start) & (val_idx_raw <= val_embargo_cutoff)]
        test_idx = test_idx_raw[test_idx_raw >= test_embargo_start]

        # Skip fold if any set too small after embargo
        if len(train_idx) < 1000 or len(val_idx) < 100 or len(test_idx) < 100:
            start_idx += step_months
            continue

        # Get timestamps for logging
        train_end_ts = df.loc[train_idx[-1], "ts"]
        val_start_ts = df.loc[val_idx[0], "ts"]
        val_end_ts = df.loc[val_idx[-1], "ts"]
        test_start_ts = df.loc[test_idx[0], "ts"]
        test_end_ts = df.loc[test_idx[-1], "ts"]

        folds.append({
            "train_idx": train_idx,
            "val_idx": val_idx,
            "test_idx": test_idx,
            "train_end": str(train_end_ts),
            "val_range": f"{val_start_ts} to {val_end_ts}",
            "test_range": f"{test_start_ts} to {test_end_ts}",
            "embargo_bars": embargo_bars,
            "train_size": len(train_idx),
            "val_size": len(val_idx),
            "test_size": len(test_idx),
        })

        start_idx += step_months

    return folds


def calculate_embargo_bars(
    label_horizon: int,
    max_hold_bars: int,
    max_feature_lookback: int,
) -> int:
    """Calculate required embargo size.

    Args:
        label_horizon: How many bars forward does label look? (e.g., shift(-12))
        max_hold_bars: Maximum holding period in backtest (e.g., 96 bars)
        max_feature_lookback: Maximum lookback in features (e.g., 252 for 1yr rolling)

    Returns:
        Embargo size in bars

    Example:
        ```
        # M5 model:
        embargo = calculate_embargo_bars(
            label_horizon=12,        # shift(-12)
            max_hold_bars=96,        # up to 96 bar holds
            max_feature_lookback=252 # 1 year rolling stats
        )
        # → embargo = 252 bars
        ```
    """
    return max(label_horizon, max_hold_bars, max_feature_lookback)


def verify_embargo(df: pd.DataFrame, fold: Dict) -> Dict[str, bool]:
    """Verify that embargo gaps are sufficient.

    Args:
        df: DataFrame with 'ts' column
        fold: Fold dict from create_walk_forward_folds_with_embargo()

    Returns:
        Dict with verification results

    Example:
        ```
        for fold in folds:
            check = verify_embargo(df, fold)
            if not all(check.values()):
                print(f"WARNING: Fold {fold['train_end']} failed embargo check")
                print(check)
        ```
    """
    train_idx = fold["train_idx"]
    val_idx = fold["val_idx"]
    test_idx = fold["test_idx"]
    embargo_bars = fold["embargo_bars"]

    checks = {}

    # Check train-val gap
    train_last = train_idx[-1]
    val_first = val_idx[0]
    gap_train_val = val_first - train_last
    checks["train_val_gap_sufficient"] = gap_train_val >= embargo_bars

    # Check val-test gap
    val_last = val_idx[-1]
    test_first = test_idx[0]
    gap_val_test = test_first - val_last
    checks["val_test_gap_sufficient"] = gap_val_test >= embargo_bars

    # Check no overlap
    checks["no_train_val_overlap"] = train_last < val_first
    checks["no_val_test_overlap"] = val_last < test_first

    # Check timestamps are sorted
    train_ts = df.loc[train_idx, "ts"].values
    val_ts = df.loc[val_idx, "ts"].values
    test_ts = df.loc[test_idx, "ts"].values
    checks["train_sorted"] = np.all(train_ts[:-1] <= train_ts[1:])
    checks["val_sorted"] = np.all(val_ts[:-1] <= val_ts[1:])
    checks["test_sorted"] = np.all(test_ts[:-1] <= test_ts[1:])

    return checks


# Example usage
if __name__ == "__main__":
    # Example: M5 model embargo calculation
    print("M5 Model Embargo Calculation:")
    print("=" * 50)
    print(f"  Label horizon (shift(-12)): 12 bars")
    print(f"  Max hold bars: 96 bars")
    print(f"  Max feature lookback: 252 bars (1 year rolling)")
    embargo_m5 = calculate_embargo_bars(12, 96, 252)
    print(f"  → Embargo required: {embargo_m5} bars")
    print(f"    = {embargo_m5 * 5} minutes = {embargo_m5 * 5 / 60:.1f} hours")

    print("\nM15 Model Embargo Calculation:")
    print("=" * 50)
    print(f"  Label horizon (shift(-16)): 16 bars")
    print(f"  Max hold bars: 96 bars (M5 equiv)")
    print(f"  Max feature lookback: 252 bars")
    embargo_m15 = calculate_embargo_bars(16, 96, 252)
    print(f"  → Embargo required: {embargo_m15} bars (in M5 bars)")

    print("\nHydra Embargo Calculation:")
    print("=" * 50)
    print(f"  Label horizon (triple barrier): 5-20 bars")
    print(f"  Max hold bars: 50 bars")
    print(f"  Max feature lookback: 252 bars")
    embargo_hydra = calculate_embargo_bars(20, 50, 252)
    print(f"  → Embargo required: {embargo_hydra} bars")
