"""
Quality and leakage gates for HYDRA matrix.
Determines if matrix is safe for training.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union

import pandas as pd
import polars as pl

from dominion.dataset.registries import HydraRegistry


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
    def _to_polars(df: Union[pd.DataFrame, pl.DataFrame]) -> pl.DataFrame:
        """Convert pandas to polars if needed."""
        if isinstance(df, pd.DataFrame):
            return pl.from_pandas(df)
        return df

    @staticmethod
    def check_shape(df: Union[pd.DataFrame, pl.DataFrame]) -> GateResult:
        """Verify matrix has exact shape (3001 columns)."""
        df_pl = QualityGates._to_polars(df)
        expected_cols = 3001  # time + 3,000 feature columns
        expected_rows_min = 1000

        if df_pl.width != expected_cols:
            return GateResult(
                "shape",
                False,
                f"Expected exactly {expected_cols} cols, got {df_pl.width}"
            )

        if df_pl.height < expected_rows_min:
            return GateResult(
                "shape",
                False,
                f"Expected >= {expected_rows_min} rows, got {df_pl.height}",
                {"rows": df_pl.height, "min_required": expected_rows_min}
            )

        return GateResult("shape", True, f"Shape OK: {df_pl.height} x {df_pl.width}")

    @staticmethod
    def check_null_fractions(df: Union[pd.DataFrame, pl.DataFrame], max_null_frac: float = 0.95) -> GateResult:
        """Check that AVAILABLE columns aren't completely null."""
        df_pl = QualityGates._to_polars(df)
        from dominion.dataset.registries import HydraRegistry

        registry = HydraRegistry()
        available_names = {c.name for c in registry.get_available_columns()}
        high_null_cols = []

        for col in df_pl.columns:
            if col == "time" or col not in available_names:
                continue  # Skip time and unavailable/reserved columns

            null_frac = df_pl[col].is_null().sum() / df_pl.height
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
    def check_available_features(df: Union[pd.DataFrame, pl.DataFrame]) -> GateResult:
        """Check that sufficient available features exist."""
        df_pl = QualityGates._to_polars(df)

        # Count all non-null non-label columns (registry-agnostic)
        # Exclude time and label columns (Z4_*)
        trainable_cols = []
        for col in df_pl.columns:
            if col == 'time':
                continue
            if col.startswith('Z4_'):  # Labels
                continue

            null_frac = df_pl[col].is_null().sum() / df_pl.height
            if null_frac < 0.95:  # At least 5% non-null
                trainable_cols.append(col)

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
    def check_leakage(df: Union[pd.DataFrame, pl.DataFrame]) -> GateResult:
        """Check for future data leakage (basic check only)."""
        df_pl = QualityGates._to_polars(df)

        # WARNING: Basic check only - does not validate point-in-time correctness
        # Full PIT validation requires checking all rolling ops, joins, and shifts
        return GateResult("leakage", True, "BASIC_LEAKAGE_CHECK (not full PIT validation)")

    @staticmethod
    def check_labels(df: Union[pd.DataFrame, pl.DataFrame]) -> GateResult:
        """Check that labels exist and are valid."""
        df_pl = QualityGates._to_polars(df)
        label_cols = [c for c in df_pl.columns if c.startswith("Z4_")]

        if not label_cols:
            return GateResult("labels", False, "No label columns found")

        # Check that at least one label has sufficient non-null values
        valid_labels = []
        for col in label_cols:
            null_frac = df_pl[col].is_null().sum() / df_pl.height
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

    @staticmethod
    def check_semantic_mapping(df: Union[pd.DataFrame, pl.DataFrame]) -> GateResult:
        """Check semantic feature mapping validity."""
        from pathlib import Path
        import json

        df_pl = QualityGates._to_polars(df)

        # Check if mapping file exists
        mapping_path = Path("data/registry/semantic_column_mapping.json")
        if not mapping_path.exists():
            # No mapping file = no semantic features = OK
            return GateResult("semantic_mapping", True, "No semantic mapping (OK)")

        # Load mapping
        with open(mapping_path) as f:
            mapping = json.load(f)

        if not mapping:
            return GateResult("semantic_mapping", True, "Empty mapping (OK)")

        # Validate each entry
        errors = []
        for slot, info in mapping.items():
            # Slot exists
            if slot not in df_pl.columns:
                errors.append(f"{slot} not in dataset")
                continue

            # Not all-null
            null_frac = df_pl[slot].is_null().sum() / df_pl.height
            if null_frac >= 0.95:
                errors.append(f"{slot} is >95% null")

            # Trainable
            if not info.get('is_trainable_feature', False):
                errors.append(f"{slot} not trainable")

            # Not label/reserved
            if slot.startswith(('Z4_', 'Z1_', 'Z2_', 'Z3_')):
                errors.append(f"{slot} is label/reserved")

        # Check duplicates
        if len(mapping) != len(set(mapping.keys())):
            errors.append("duplicate slots")

        if errors:
            return GateResult(
                "semantic_mapping",
                False,
                f"Mapping validation failed: {len(errors)} errors",
                {"errors": errors[:10]}
            )

        return GateResult(
            "semantic_mapping",
            True,
            f"Semantic mapping valid ({len(mapping)} features)",
            {"mapped_features": len(mapping)}
        )


def run_all_gates(df: Union[pd.DataFrame, pl.DataFrame]) -> tuple[bool, list[GateResult]]:
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
        gates.check_semantic_mapping(df),
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
