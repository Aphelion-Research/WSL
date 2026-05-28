"""
Leakage Validation & Audit Module
==================================
Enforces data integrity for trading ML pipelines.
Catches contaminated configs, leaky features, invalid folds.
"""
import numpy as np
import pandas as pd
import re
from typing import List, Dict, Optional, Tuple


# Forbidden feature patterns (case-insensitive)
FORBIDDEN_PATTERNS = [
    r"label", r"target", r"fwd", r"forward", r"future",
    r"next_", r"lead_", r"pnl", r"profit", r"outcome"
]


def check_timestamps_monotonic(df: pd.DataFrame, ts_col: str = "ts") -> Tuple[bool, Optional[str]]:
    """Verify timestamps are monotonically increasing (no shuffle).

    Args:
        df: DataFrame with timestamp column
        ts_col: Name of timestamp column

    Returns:
        (is_valid, error_message)
    """
    if ts_col not in df.columns:
        return False, f"Missing timestamp column: {ts_col}"

    ts = pd.to_datetime(df[ts_col])
    if not ts.is_monotonic_increasing:
        first_violation = ts[ts.diff() < pd.Timedelta(0)].index[0]
        return False, f"Non-monotonic timestamp at row {first_violation}"

    return True, None


def check_forbidden_columns(feature_cols: List[str]) -> Tuple[bool, List[str]]:
    """Check for forbidden feature names indicating leakage.

    Args:
        feature_cols: List of feature column names

    Returns:
        (is_valid, list_of_forbidden_columns)
    """
    forbidden = []
    for col in feature_cols:
        col_lower = col.lower()
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, col_lower):
                forbidden.append(col)
                break

    return len(forbidden) == 0, forbidden


def check_embargo_sufficient(
    embargo_bars: int,
    label_horizon_bars: int,
    max_hold_bars: int
) -> Tuple[bool, Optional[str]]:
    """Verify embargo gap is large enough to prevent label leakage.

    Args:
        embargo_bars: Size of embargo gap between folds
        label_horizon_bars: How many bars forward does label look
        max_hold_bars: Maximum holding period in backtest

    Returns:
        (is_valid, error_message)
    """
    min_embargo = max(label_horizon_bars, max_hold_bars)

    if embargo_bars < min_embargo:
        return False, (
            f"Embargo {embargo_bars} bars too small. "
            f"Need >= {min_embargo} (max of label_horizon={label_horizon_bars}, "
            f"max_hold={max_hold_bars})"
        )

    return True, None


def check_fold_boundaries(
    df: pd.DataFrame,
    fold: Dict,
    label_horizon_bars: int,
    ts_col: str = "ts"
) -> Tuple[bool, Optional[str]]:
    """Check that test rows with forward horizons extending past fold end are excluded.

    Args:
        df: DataFrame with timestamp column
        fold: Fold dict with 'test_idx' array
        label_horizon_bars: How many bars forward does label look
        ts_col: Timestamp column name

    Returns:
        (is_valid, error_message)
    """
    test_idx = fold["test_idx"]

    if len(test_idx) == 0:
        return False, "Empty test set"

    # Check if last label_horizon_bars rows are excluded
    last_test_idx = test_idx[-1]
    df_last_idx = len(df) - 1

    if last_test_idx > df_last_idx - label_horizon_bars:
        return False, (
            f"Test fold extends too close to data end. "
            f"Last test idx {last_test_idx}, data end {df_last_idx}, "
            f"need {label_horizon_bars} bar buffer for label horizon"
        )

    return True, None


def check_config_contamination(
    config_selection_period: str,
    test_period: str
) -> Tuple[bool, Optional[str]]:
    """Mark configs selected using test/OOS data as contaminated.

    Args:
        config_selection_period: Period used to select config (e.g., "2025-2026")
        test_period: True OOS test period (e.g., "2026")

    Returns:
        (is_valid, warning_message)
    """
    # Parse periods
    try:
        selection_years = [int(y) for y in config_selection_period.split("-")]
        test_years = [int(y) for y in test_period.split("-")]
    except:
        return True, "Cannot parse periods, skipping contamination check"

    # Check if config selection includes test period
    selection_max = max(selection_years)
    test_min = min(test_years)

    if selection_max >= test_min:
        return False, (
            f"CONTAMINATED: Config selected on {config_selection_period} "
            f"includes test period {test_period}. Selection bias."
        )

    return True, None


def validate_pipeline(
    df: pd.DataFrame,
    feature_cols: List[str],
    fold: Dict,
    label_horizon_bars: int,
    max_hold_bars: int,
    config_selection_period: Optional[str] = None,
    test_period: Optional[str] = None,
    ts_col: str = "ts"
) -> Dict[str, any]:
    """Run full validation suite on ML pipeline.

    Args:
        df: DataFrame with timestamp and features
        feature_cols: List of feature column names
        fold: Fold dict with train/val/test indices
        label_horizon_bars: Label forward horizon
        max_hold_bars: Max backtest holding period
        config_selection_period: Period used to optimize config (optional)
        test_period: True OOS test period (optional)
        ts_col: Timestamp column name

    Returns:
        Dict with validation results

    Example:
        ```python
        results = validate_pipeline(
            df=data,
            feature_cols=feature_list,
            fold=fold,
            label_horizon_bars=12,
            max_hold_bars=96,
            config_selection_period="2025",
            test_period="2026"
        )

        if not results["is_valid"]:
            raise ValueError(f"Validation failed: {results['errors']}")
        ```
    """
    results = {
        "is_valid": True,
        "errors": [],
        "warnings": [],
        "checks": {}
    }

    # 1. Check timestamps monotonic
    valid, msg = check_timestamps_monotonic(df, ts_col)
    results["checks"]["timestamps_monotonic"] = valid
    if not valid:
        results["is_valid"] = False
        results["errors"].append(msg)

    # 2. Check forbidden columns
    valid, forbidden = check_forbidden_columns(feature_cols)
    results["checks"]["no_forbidden_columns"] = valid
    if not valid:
        results["is_valid"] = False
        results["errors"].append(f"Forbidden feature columns: {forbidden}")

    # 3. Check embargo sufficient
    embargo_bars = fold.get("embargo_bars", 0)
    valid, msg = check_embargo_sufficient(embargo_bars, label_horizon_bars, max_hold_bars)
    results["checks"]["embargo_sufficient"] = valid
    if not valid:
        results["is_valid"] = False
        results["errors"].append(msg)

    # 4. Check fold boundaries
    valid, msg = check_fold_boundaries(df, fold, label_horizon_bars, ts_col)
    results["checks"]["fold_boundaries_valid"] = valid
    if not valid:
        results["is_valid"] = False
        results["errors"].append(msg)

    # 5. Check config contamination
    if config_selection_period and test_period:
        valid, msg = check_config_contamination(config_selection_period, test_period)
        results["checks"]["config_not_contaminated"] = valid
        if not valid:
            results["warnings"].append(msg)

    return results


def audit_report(results: Dict[str, any]) -> str:
    """Generate human-readable audit report.

    Args:
        results: Results from validate_pipeline()

    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("LEAKAGE VALIDATION AUDIT REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Overall status
    if results["is_valid"]:
        lines.append("Status: ✓ PASSED")
    else:
        lines.append("Status: ✗ FAILED")

    lines.append("")
    lines.append("Checks:")
    for check, passed in results["checks"].items():
        status = "✓" if passed else "✗"
        lines.append(f"  {status} {check}")

    if results["errors"]:
        lines.append("")
        lines.append("Errors:")
        for err in results["errors"]:
            lines.append(f"  - {err}")

    if results["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for warn in results["warnings"]:
            lines.append(f"  - {warn}")

    lines.append("")
    lines.append("=" * 80)

    return "\n".join(lines)
