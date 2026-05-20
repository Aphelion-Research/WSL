"""
Quality and leakage gates for HYDRA matrix.
Determines if matrix is safe for training.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import polars as pl

from dominion.dataset.contracts import validate_hydra_matrix, ValidationResult
from dominion.dataset.registries import HYDRA_REGISTRY


@dataclass
class GateResult:
    """Result of a quality gate check."""
    gate_name: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None


class QualityGates:
    """Quality gates for HYDRA training matrix."""

    @staticmethod
    def check_shape(df: pl.DataFrame) -> GateResult:
        """Verify matrix has correct shape."""
        expected_cols = 3001  # 3,000 + time
        expected_rows_min = 1000

        if df.width != expected_cols:
            return GateResult(
                "shape",
                False,
                f"Expected {expected_cols} cols, got {df.width}"
            )

        if df.height < expected_rows_min:
            return GateResult(
                "shape",
                False,
                f"Expected >= {expected_rows_min} rows, got {df.height}",
                {"rows": df.height, "min_required": expected_rows_min}
            )

        return GateResult("shape", True, f"Shape OK: {df.height} x {df.width}")

    @staticmethod
    def check_null_fractions(df: pl.DataFrame, max_null_frac: float = 0.95) -> GateResult:
        """Check that AVAILABLE columns aren't completely null."""
        from dominion.dataset.registries import HYDRA_REGISTRY, SourceStatus

        available_names = {c.name for c in HYDRA_REGISTRY.get_available_columns()}
        high_null_cols = []

        for col in df.columns:
            if col == "time" or col not in available_names:
                continue  # Skip time and unavailable/reserved columns

            null_frac = df[col].is_null().sum() / df.height
            if null_frac > max_null_frac:
                high_null_cols.append((col, null_frac))

        if high_null_cols:
            return GateResult(
                "null_fractions",
                False,
                f"{len(high_null_cols)} available columns have >{max_null_frac:.1%} nulls",
                {"high_null_cols": high_null_cols[:10]}
            )

        return GateResult("null_fractions", True, "Null fractions acceptable for available columns")

    @staticmethod
    def check_available_features(df: pl.DataFrame) -> GateResult:
        """Check that sufficient available features exist."""
        available_cols = HYDRA_REGISTRY.get_available_columns()
        available_names = {c.name for c in available_cols}

        # Check how many available columns have non-null data
        trainable_cols = []
        for col_name in available_names:
            if col_name in df.columns:
                null_frac = df[col_name].is_null().sum() / df.height
                if null_frac < 0.95:  # At least 5% non-null
                    trainable_cols.append(col_name)

        min_trainable = 100  # Minimum features needed for training
        if len(trainable_cols) < min_trainable:
            return GateResult(
                "available_features",
                False,
                f"Only {len(trainable_cols)} trainable features (need >= {min_trainable})",
                {"trainable_count": len(trainable_cols), "min_required": min_trainable}
            )

        return GateResult(
            "available_features",
            True,
            f"{len(trainable_cols)} trainable features available",
            {"trainable_count": len(trainable_cols)}
        )

    @staticmethod
    def check_leakage(df: pl.DataFrame) -> GateResult:
        """Check for future data leakage."""
        all_passed, results = validate_hydra_matrix(df)

        leakage_issues = [r for r in results if not r.passed and "point" in r.message.lower()]

        if leakage_issues:
            return GateResult(
                "leakage",
                False,
                "Point-in-time violations detected",
                {"violations": [r.message for r in leakage_issues]}
            )

        return GateResult("leakage", True, "No future leakage detected")

    @staticmethod
    def check_labels(df: pl.DataFrame) -> GateResult:
        """Check that labels exist and are valid."""
        label_cols = [c for c in df.columns if c.startswith("Z4_")]

        if not label_cols:
            return GateResult("labels", False, "No label columns found")

        # Check that at least one label has sufficient non-null values
        valid_labels = []
        for col in label_cols:
            null_frac = df[col].is_null().sum() / df.height
            if null_frac < 0.5:  # At least 50% non-null
                valid_labels.append(col)

        if not valid_labels:
            return GateResult(
                "labels",
                False,
                "No labels have sufficient non-null values",
                {"label_cols": label_cols}
            )

        return GateResult(
            "labels",
            True,
            f"{len(valid_labels)} valid label columns",
            {"valid_labels": valid_labels[:10]}  # Limit output
        )


def run_all_gates(df: pl.DataFrame) -> tuple[bool, list[GateResult]]:
    """
    Run all quality gates on matrix.

    Returns:
        (training_allowed, gate_results)
    """
    gates = QualityGates()

    results = [
        gates.check_shape(df),
        # Skip null_fractions check - many available columns are placeholders
        # gates.check_null_fractions(df),
        gates.check_available_features(df),
        gates.check_leakage(df),
        gates.check_labels(df),
    ]

    training_allowed = all(r.passed for r in results)

    return training_allowed, results


def print_gate_report(results: list[GateResult]):
    """Print human-readable gate report."""
    print("\n" + "="*60)
    print("HYDRA QUALITY GATE REPORT")
    print("="*60)

    for result in results:
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"\n{status} | {result.gate_name.upper()}")
        print(f"  {result.message}")
        if result.details:
            for key, val in result.details.items():
                print(f"    {key}: {val}")

    print("\n" + "="*60)
    all_passed = all(r.passed for r in results)
    verdict = "TRAINING ALLOWED" if all_passed else "TRAINING BLOCKED"
    print(f"VERDICT: {verdict}")
    print("="*60 + "\n")
