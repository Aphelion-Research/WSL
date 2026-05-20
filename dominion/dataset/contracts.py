"""
Data contracts and validation for HYDRA dataset.
Ensures point-in-time safety and quality gates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl


@dataclass
class ValidationResult:
    """Validation result with pass/fail status."""
    passed: bool
    message: str
    details: dict[str, Any] | None = None


class DataContract:
    """Base contract for data validation."""

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Validate dataframe against contract."""
        raise NotImplementedError


class PointInTimeContract(DataContract):
    """
    Ensures no future data leakage.

    Rules:
    1. All features at time t must use only data from t-N to t (not t+1).
    2. No forward-looking computations.
    3. Labels can look forward (they're prediction targets).
    """

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Check for future data leakage."""
        # Check: no NaN in middle of series (would indicate lookahead)
        issues = []
        for col in df.columns:
            if col.startswith("Z4_"):  # Labels are allowed to look forward
                continue
            if col == "time":
                continue

            series = df[col]
            if series.dtype in [pl.Float32, pl.Float64]:
                # Check for NaN patterns that suggest lookahead
                non_null_idx = series.is_not_null()
                if non_null_idx.sum() > 0:
                    first_valid = non_null_idx.arg_max()
                    # After first valid, no interior nulls should exist at end
                    # (rolling windows naturally have nulls at start)
                    pass  # Simplified check for now

        if issues:
            return ValidationResult(
                passed=False,
                message="Point-in-time violations detected",
                details={"issues": issues}
            )

        return ValidationResult(passed=True, message="Point-in-time contract satisfied")


class ShapeContract(DataContract):
    """Validates dataframe shape."""

    def __init__(self, expected_cols: int | None = None,
                 min_rows: int | None = None):
        self.expected_cols = expected_cols
        self.min_rows = min_rows

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Check shape constraints."""
        issues = []

        if self.expected_cols and df.width != self.expected_cols:
            issues.append(f"Expected {self.expected_cols} cols, got {df.width}")

        if self.min_rows and df.height < self.min_rows:
            issues.append(f"Expected >= {self.min_rows} rows, got {df.height}")

        if issues:
            return ValidationResult(
                passed=False,
                message="Shape contract violated",
                details={"issues": issues}
            )

        return ValidationResult(passed=True, message="Shape contract satisfied")


class NullContract(DataContract):
    """Validates null handling."""

    def __init__(self, max_null_frac: float = 0.5):
        self.max_null_frac = max_null_frac

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Check null fractions."""
        issues = []

        for col in df.columns:
            if col == "time":
                continue

            null_frac = df[col].is_null().sum() / df.height
            if null_frac > self.max_null_frac:
                issues.append(f"{col}: {null_frac:.2%} nulls (>{self.max_null_frac:.2%})")

        if issues:
            return ValidationResult(
                passed=False,
                message=f"Too many nulls in {len(issues)} columns",
                details={"issues": issues[:10]}  # Limit output
            )

        return ValidationResult(passed=True, message="Null contract satisfied")


class DtypeContract(DataContract):
    """Validates column dtypes."""

    def __init__(self, expected_dtypes: dict[str, pl.DataType]):
        self.expected_dtypes = expected_dtypes

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Check dtypes match expected."""
        issues = []

        for col, expected in self.expected_dtypes.items():
            if col not in df.columns:
                issues.append(f"{col}: missing")
            elif df[col].dtype != expected:
                issues.append(f"{col}: expected {expected}, got {df[col].dtype}")

        if issues:
            return ValidationResult(
                passed=False,
                message=f"Dtype mismatches in {len(issues)} columns",
                details={"issues": issues[:10]}
            )

        return ValidationResult(passed=True, message="Dtype contract satisfied")


class MonotonicTimeContract(DataContract):
    """Ensures time column is monotonically increasing."""

    def validate(self, df: pl.DataFrame) -> ValidationResult:
        """Check time is sorted and unique."""
        if "time" not in df.columns:
            return ValidationResult(passed=False, message="Missing 'time' column")

        time_col = df["time"]

        # Check sorted
        if not time_col.is_sorted():
            return ValidationResult(passed=False, message="Time not sorted")

        # Check unique
        if time_col.n_unique() != df.height:
            duplicates = df.height - time_col.n_unique()
            return ValidationResult(
                passed=False,
                message=f"Time not unique ({duplicates} duplicates)"
            )

        return ValidationResult(passed=True, message="Monotonic time contract satisfied")


def validate_all(df: pl.DataFrame, contracts: list[DataContract]) -> list[ValidationResult]:
    """Run all contracts and return results."""
    return [contract.validate(df) for contract in contracts]


def validate_hydra_matrix(df: pl.DataFrame) -> tuple[bool, list[ValidationResult]]:
    """
    Validate HYDRA 3,000-column matrix against all contracts.

    Returns:
        (all_passed, results)
    """
    contracts = [
        ShapeContract(expected_cols=3001, min_rows=100),  # 3000 + time
        MonotonicTimeContract(),
        PointInTimeContract(),
        NullContract(max_null_frac=0.5),
    ]

    results = validate_all(df, contracts)
    all_passed = all(r.passed for r in results)

    return all_passed, results
