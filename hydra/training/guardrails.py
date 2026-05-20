"""Training guardrails - check gates before allowing HYDRA training.

Implements Agent 2 mission: Do NOT train until Agent 1 sets training_allowed=true.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from hydra.config import ROOT


@dataclass
class GateVerdictResult:
    """Result of gate verdict check."""

    training_allowed: bool
    reason: str
    gates_passed: list[str]
    gates_failed: list[str]
    matrix_rows: int
    matrix_cols: int
    date_range: str
    verdict_path: Optional[str]


class TrainingGuardrails:
    """Check training gates before allowing HYDRA execution."""

    def __init__(
        self,
        gate_verdict_path: Optional[Path] = None,
        min_rows: int = 1000,
        min_cols: int = 100,
        max_missing_pct: float = 50.0,
        min_label_rate: float = 0.30,
    ):
        """Initialize guardrails.

        Args:
            gate_verdict_path: Path to Agent 1's gate verdict file
            min_rows: Minimum required rows
            min_cols: Minimum required columns
            max_missing_pct: Maximum allowed missing data %
            min_label_rate: Minimum required label rate
        """
        if gate_verdict_path is None:
            # Default location for Agent 1 gate verdict
            self.gate_verdict_path = ROOT / "data" / "training_gate_verdict.json"
        else:
            self.gate_verdict_path = Path(gate_verdict_path)

        self.min_rows = min_rows
        self.min_cols = min_cols
        self.max_missing_pct = max_missing_pct
        self.min_label_rate = min_label_rate

    def check_gate_verdict(self) -> GateVerdictResult:
        """Check Agent 1's gate verdict file.

        Returns:
            GateVerdictResult with training_allowed decision
        """
        if not self.gate_verdict_path.exists():
            return GateVerdictResult(
                training_allowed=False,
                reason="Gate verdict file not found (Agent 1 not complete)",
                gates_passed=[],
                gates_failed=["gate_verdict_missing"],
                matrix_rows=0,
                matrix_cols=0,
                date_range="unknown",
                verdict_path=str(self.gate_verdict_path),
            )

        try:
            with open(self.gate_verdict_path) as f:
                verdict = json.load(f)
        except Exception as e:
            return GateVerdictResult(
                training_allowed=False,
                reason=f"Failed to parse gate verdict: {e}",
                gates_passed=[],
                gates_failed=["gate_verdict_parse_error"],
                matrix_rows=0,
                matrix_cols=0,
                date_range="unknown",
                verdict_path=str(self.gate_verdict_path),
            )

        # Extract verdict fields
        training_allowed = verdict.get("training_allowed", False)
        reason = verdict.get("reason", "No reason provided")
        gates_passed = verdict.get("gates_passed", [])
        gates_failed = verdict.get("gates_failed", [])
        matrix_rows = verdict.get("matrix_rows", 0)
        matrix_cols = verdict.get("matrix_cols", 0)
        date_range = verdict.get("date_range", "unknown")

        return GateVerdictResult(
            training_allowed=training_allowed,
            reason=reason,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            matrix_rows=matrix_rows,
            matrix_cols=matrix_cols,
            date_range=date_range,
            verdict_path=str(self.gate_verdict_path),
        )

    def check_data_quality(
        self,
        df: pd.DataFrame,
        labels: Optional[np.ndarray] = None,
    ) -> GateVerdictResult:
        """Check data quality gates (fallback if no verdict file).

        Args:
            df: Feature matrix DataFrame
            labels: Optional labels array

        Returns:
            GateVerdictResult with quality checks
        """
        gates_passed = []
        gates_failed = []

        # Check 1: Minimum rows
        if len(df) >= self.min_rows:
            gates_passed.append("min_rows")
        else:
            gates_failed.append(f"min_rows (need {self.min_rows}, got {len(df)})")

        # Check 2: Minimum columns
        n_cols = len(df.columns)
        if n_cols >= self.min_cols:
            gates_passed.append("min_cols")
        else:
            gates_failed.append(f"min_cols (need {self.min_cols}, got {n_cols})")

        # Check 3: Missing data
        if len(df) > 0 and n_cols > 0:
            total_cells = len(df) * n_cols
            missing_cells = df.isna().sum().sum()
            missing_pct = (missing_cells / total_cells) * 100

            if missing_pct <= self.max_missing_pct:
                gates_passed.append("missing_data")
            else:
                gates_failed.append(
                    f"missing_data (max {self.max_missing_pct}%, got {missing_pct:.1f}%)"
                )

        # Check 4: Label rate (if labels provided)
        if labels is not None:
            valid_labels = np.isfinite(labels).sum()
            label_rate = valid_labels / len(labels) if len(labels) > 0 else 0.0

            if label_rate >= self.min_label_rate:
                gates_passed.append("label_rate")
            else:
                gates_failed.append(
                    f"label_rate (min {self.min_label_rate:.1%}, got {label_rate:.1%})"
                )

        # Check 5: No all-NaN columns
        if len(df) > 0:
            all_nan_cols = df.isna().all().sum()
            if all_nan_cols == 0:
                gates_passed.append("no_all_nan_cols")
            else:
                gates_failed.append(f"no_all_nan_cols ({all_nan_cols} all-NaN columns found)")

        # Check 6: No duplicate columns
        if len(df.columns) == len(set(df.columns)):
            gates_passed.append("no_duplicate_cols")
        else:
            gates_failed.append("no_duplicate_cols (duplicate column names found)")

        # Date range
        if "timestamp" in df.columns:
            try:
                timestamps = pd.to_datetime(df["timestamp"])
                date_range = f"{timestamps.min()} to {timestamps.max()}"
            except Exception:
                date_range = "unknown"
        else:
            date_range = "unknown (no timestamp column)"

        # Training allowed if all gates passed
        training_allowed = len(gates_failed) == 0

        if training_allowed:
            reason = "All quality gates passed"
        else:
            reason = f"Gates failed: {', '.join(gates_failed)}"

        return GateVerdictResult(
            training_allowed=training_allowed,
            reason=reason,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            matrix_rows=len(df),
            matrix_cols=n_cols,
            date_range=date_range,
            verdict_path=None,
        )

    def write_blocked_report(
        self,
        verdict: GateVerdictResult,
        output_path: Optional[Path] = None,
    ) -> None:
        """Write training-blocked report (Agent 2 mission requirement).

        Args:
            verdict: Gate verdict result
            output_path: Where to write report (default: reports/training_blocked_YYYYMMDD.md)
        """
        if output_path is None:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = ROOT / "reports" / f"training_blocked_{timestamp}.md"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        report = f"""# HYDRA TRAINING BLOCKED

**Date:** {pd.Timestamp.now()}
**Status:** Training NOT allowed
**Blocker:** {verdict.reason}

---

## Matrix Status

- **Rows:** {verdict.matrix_rows:,}
- **Columns:** {verdict.matrix_cols:,}
- **Date Range:** {verdict.date_range}
- **Verdict File:** {verdict.verdict_path or 'N/A (quality check fallback)'}

---

## Gates Status

### Passed ({len(verdict.gates_passed)})

{chr(10).join(f"- {gate}" for gate in verdict.gates_passed) if verdict.gates_passed else "- None"}

### Failed ({len(verdict.gates_failed)})

{chr(10).join(f"- {gate}" for gate in verdict.gates_failed) if verdict.gates_failed else "- None"}

---

## Next Steps

To unblock training:

1. **If Agent 1 verdict missing:** Wait for Agent 1 to complete matrix build and quality gates
2. **If quality gates failed:** Review failed gates above and fix data quality issues
3. **If leakage detected:** Fix point-in-time violations in feature pipeline
4. **If insufficient data:** Extend date range or reduce minimum requirements

**Action:** Fix blockers listed above, then re-run training guardrails check.

---

## Guardrail Config

- **Min rows:** {self.min_rows:,}
- **Min columns:** {self.min_cols:,}
- **Max missing %:** {self.max_missing_pct:.1f}%
- **Min label rate:** {self.min_label_rate:.1%}

---

*Generated by Agent 2 (HYDRA Training Engineer)*
"""

        with open(output_path, "w") as f:
            f.write(report)

        print(f"Training-blocked report written to: {output_path}")


def check_training_allowed(
    df: Optional[pd.DataFrame] = None,
    labels: Optional[np.ndarray] = None,
    gate_verdict_path: Optional[Path] = None,
) -> tuple[bool, GateVerdictResult]:
    """Quick check if training is allowed.

    Returns:
        (training_allowed, verdict_result)
    """
    guardrails = TrainingGuardrails(gate_verdict_path=gate_verdict_path)

    # First check Agent 1's gate verdict
    verdict = guardrails.check_gate_verdict()

    if verdict.training_allowed:
        return True, verdict

    # Fallback: check data quality if DataFrame provided
    if df is not None:
        verdict = guardrails.check_data_quality(df, labels)

    return verdict.training_allowed, verdict


def exclude_non_features(
    df: pd.DataFrame,
    label_col_pattern: str = "label",
    quality_col_pattern: str = "quality",
    reserved_cols: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Exclude label/quality/reserved columns from feature matrix (Agent 2 mission).

    Args:
        df: Full DataFrame
        label_col_pattern: Pattern to identify label columns
        quality_col_pattern: Pattern to identify quality columns
        reserved_cols: Additional reserved column names

    Returns:
        Feature-only DataFrame
    """
    if reserved_cols is None:
        reserved_cols = ["timestamp", "date", "datetime", "id", "index"]

    exclude_cols = set()

    # Pattern-based exclusions
    for col in df.columns:
        col_lower = col.lower()
        if label_col_pattern in col_lower:
            exclude_cols.add(col)
        if quality_col_pattern in col_lower:
            exclude_cols.add(col)

    # Reserved columns
    for col in reserved_cols:
        if col in df.columns:
            exclude_cols.add(col)

    # Keep only feature columns
    feature_cols = [col for col in df.columns if col not in exclude_cols]

    print(f"Excluded {len(exclude_cols)} non-feature columns: {sorted(exclude_cols)[:10]}...")
    print(f"Retained {len(feature_cols)} feature columns")

    return df[feature_cols]
