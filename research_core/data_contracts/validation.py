"""Validation functions for data contracts."""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from .columns import FORBIDDEN_FEATURE_PATTERNS, REQUIRED_OHLCV_COLUMNS


class ValidationError(Exception):
    """Raised when data contract validation fails."""
    pass


def validate_timestamps(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate timestamp monotonicity and uniqueness.

    Args:
        df: DataFrame with DatetimeIndex

    Returns:
        Dict with validation results

    Raises:
        ValidationError: If critical violations found
    """
    results = {
        "monotonic": True,
        "duplicates": 0,
        "gaps": [],
        "errors": [],
    }

    if not isinstance(df.index, pd.DatetimeIndex):
        results["errors"].append("Index is not DatetimeIndex")
        results["monotonic"] = False
        raise ValidationError("Index must be DatetimeIndex")

    # Check monotonicity
    if not df.index.is_monotonic_increasing:
        results["monotonic"] = False
        results["errors"].append("Timestamps not monotonic increasing")
        raise ValidationError("Timestamps must be monotonic increasing")

    # Check duplicates
    duplicates = df.index.duplicated().sum()
    if duplicates > 0:
        results["duplicates"] = duplicates
        results["errors"].append(f"Found {duplicates} duplicate timestamps")
        raise ValidationError(f"Found {duplicates} duplicate timestamps")

    # Check for unusual gaps (optional warning, not error)
    time_diffs = df.index.to_series().diff()
    median_diff = time_diffs.median()
    large_gaps = time_diffs[time_diffs > median_diff * 10]
    if len(large_gaps) > 0:
        results["gaps"] = large_gaps.head(5).to_dict()

    return results


def check_forbidden_columns(df: pd.DataFrame, allow_label: bool = False) -> Dict[str, Any]:
    """Check for forbidden feature column patterns.

    Args:
        df: DataFrame with feature columns
        allow_label: If True, allow explicit 'label' column (for label-context only)

    Returns:
        Dict with found violations

    Raises:
        ValidationError: If forbidden patterns found
    """
    results = {
        "violations": [],
        "clean": True,
    }

    cols = [c.lower() for c in df.columns]

    for pattern in FORBIDDEN_FEATURE_PATTERNS:
        # Special case: allow 'label' if explicitly permitted
        if pattern == "label" and allow_label:
            continue

        matches = [c for c in cols if pattern in c]
        if matches:
            results["violations"].append({
                "pattern": pattern,
                "columns": matches,
            })
            results["clean"] = False

    if not results["clean"]:
        msg = "Found forbidden patterns in columns:\n"
        for v in results["violations"]:
            msg += f"  {v['pattern']}: {v['columns']}\n"
        raise ValidationError(msg)

    return results


def validate_ohlcv(df: pd.DataFrame) -> Dict[str, Any]:
    """Validate OHLCV DataFrame structure.

    Args:
        df: DataFrame with OHLCV data

    Returns:
        Dict with validation results

    Raises:
        ValidationError: If required columns missing
    """
    results = {
        "has_required": True,
        "missing": [],
        "errors": [],
    }

    cols_lower = [c.lower() for c in df.columns]

    for req in REQUIRED_OHLCV_COLUMNS:
        if req not in cols_lower:
            results["has_required"] = False
            results["missing"].append(req)

    if results["missing"]:
        msg = f"Missing required OHLCV columns: {results['missing']}"
        results["errors"].append(msg)
        raise ValidationError(msg)

    # Validate OHLC relationships (optional warnings)
    if "open" in cols_lower and "high" in cols_lower:
        violations = (df["high"] < df["open"]).sum()
        if violations > 0:
            results["errors"].append(f"Found {violations} bars where high < open")

    if "open" in cols_lower and "low" in cols_lower:
        violations = (df["low"] > df["open"]).sum()
        if violations > 0:
            results["errors"].append(f"Found {violations} bars where low > open")

    return results


def validate_features(
    df: pd.DataFrame,
    allow_label: bool = False,
    check_bfill: bool = False,
) -> Dict[str, Any]:
    """Comprehensive feature validation.

    Args:
        df: DataFrame with features
        allow_label: Allow 'label' column
        check_bfill: Check for potential bfill usage (experimental)

    Returns:
        Dict with all validation results

    Raises:
        ValidationError: If critical violations found
    """
    results = {}

    # Timestamp validation
    results["timestamps"] = validate_timestamps(df)

    # Forbidden column check
    results["columns"] = check_forbidden_columns(df, allow_label=allow_label)

    # Optional: detect potential bfill usage
    # This is heuristic — checks if NaN patterns suggest forward fill
    if check_bfill:
        results["bfill_warning"] = []
        for col in df.columns:
            if df[col].dtype in [np.float64, np.float32]:
                # Check if last N rows have fewer NaNs than first N rows
                # (could indicate bfill was used)
                head_nan = df[col].head(100).isna().sum()
                tail_nan = df[col].tail(100).isna().sum()
                if tail_nan < head_nan * 0.5 and head_nan > 10:
                    results["bfill_warning"].append(col)

    return results
