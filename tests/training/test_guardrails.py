"""Test training guardrails."""
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from hydra.training.guardrails import (
    TrainingGuardrails,
    check_training_allowed,
    exclude_non_features,
)


def test_check_gate_verdict_missing():
    """Test behavior when gate verdict file missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gate_path = Path(tmpdir) / "nonexistent.json"

        guardrails = TrainingGuardrails(gate_verdict_path=gate_path)
        verdict = guardrails.check_gate_verdict()

        assert not verdict.training_allowed
        assert "not found" in verdict.reason.lower()
        assert "gate_verdict_missing" in verdict.gates_failed

        print(f"Correctly blocked when gate missing: {verdict.reason}")


def test_check_gate_verdict_pass():
    """Test behavior when gate verdict passes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gate_path = Path(tmpdir) / "gate.json"

        # Write passing verdict
        verdict_data = {
            "training_allowed": True,
            "reason": "All gates passed",
            "gates_passed": ["quality", "leakage", "stationarity"],
            "gates_failed": [],
            "matrix_rows": 5000,
            "matrix_cols": 3000,
            "date_range": "2021-01-01 to 2026-01-01",
        }

        with open(gate_path, "w") as f:
            json.dump(verdict_data, f)

        guardrails = TrainingGuardrails(gate_verdict_path=gate_path)
        verdict = guardrails.check_gate_verdict()

        assert verdict.training_allowed
        assert verdict.matrix_rows == 5000
        assert verdict.matrix_cols == 3000
        assert len(verdict.gates_passed) == 3
        assert len(verdict.gates_failed) == 0

        print(f"Gate verdict PASS: {verdict.reason}")


def test_check_gate_verdict_fail():
    """Test behavior when gate verdict fails."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gate_path = Path(tmpdir) / "gate.json"

        # Write failing verdict
        verdict_data = {
            "training_allowed": False,
            "reason": "Leakage detected in HMM features",
            "gates_passed": ["quality"],
            "gates_failed": ["leakage_check", "stationarity_check"],
            "matrix_rows": 5000,
            "matrix_cols": 3000,
            "date_range": "2021-01-01 to 2026-01-01",
        }

        with open(gate_path, "w") as f:
            json.dump(verdict_data, f)

        guardrails = TrainingGuardrails(gate_verdict_path=gate_path)
        verdict = guardrails.check_gate_verdict()

        assert not verdict.training_allowed
        assert "Leakage" in verdict.reason
        assert len(verdict.gates_failed) == 2

        print(f"Gate verdict FAIL: {verdict.reason}")


def test_check_data_quality_pass():
    """Test data quality checks pass."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=2000, freq="5min"),
        "feat_1": np.random.randn(2000),
        "feat_2": np.random.randn(2000),
        "feat_3": np.random.randn(2000),
    })

    labels = np.random.choice([0.0, 1.0, np.nan], size=2000, p=[0.3, 0.3, 0.4])

    guardrails = TrainingGuardrails(
        min_rows=1000,
        min_cols=2,
        max_missing_pct=50.0,
        min_label_rate=0.30,
    )

    verdict = guardrails.check_data_quality(df, labels)

    assert verdict.training_allowed
    assert len(verdict.gates_failed) == 0

    print(f"Data quality PASS: {verdict.gates_passed}")


def test_check_data_quality_fail():
    """Test data quality checks fail."""
    # Create bad data (too few rows, all NaN column, low label rate)
    df = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=100, freq="5min"),
        "feat_1": np.random.randn(100),
        "feat_2": [np.nan] * 100,  # All NaN column
    })

    labels = np.array([np.nan] * 90 + [1.0] * 10)  # Only 10% labeled

    guardrails = TrainingGuardrails(
        min_rows=1000,
        min_cols=2,
        max_missing_pct=10.0,
        min_label_rate=0.30,
    )

    verdict = guardrails.check_data_quality(df, labels)

    assert not verdict.training_allowed
    assert len(verdict.gates_failed) > 0

    print(f"Data quality FAIL: {verdict.gates_failed}")


def test_exclude_non_features():
    """Test non-feature column exclusion."""
    df = pd.DataFrame({
        "timestamp": pd.date_range("2020-01-01", periods=100, freq="5min"),
        "feat_price": np.random.randn(100),
        "feat_volume": np.random.randn(100),
        "label_target": np.random.choice([0, 1], 100),
        "label_forward_return": np.random.randn(100),
        "quality_score": np.random.rand(100),
        "quality_flag": np.random.choice([True, False], 100),
        "open": np.random.randn(100),
        "high": np.random.randn(100),
        "low": np.random.randn(100),
        "close": np.random.randn(100),
    })

    df_features = exclude_non_features(
        df,
        label_col_pattern="label",
        quality_col_pattern="quality",
        reserved_cols=["timestamp", "open", "high", "low", "close"],
    )

    # Should only retain feat_* columns
    assert "feat_price" in df_features.columns
    assert "feat_volume" in df_features.columns
    assert "label_target" not in df_features.columns
    assert "label_forward_return" not in df_features.columns
    assert "quality_score" not in df_features.columns
    assert "timestamp" not in df_features.columns
    assert "open" not in df_features.columns

    print(f"Excluded {len(df.columns) - len(df_features.columns)} non-feature columns")
    print(f"Retained: {df_features.columns.tolist()}")


def test_write_blocked_report():
    """Test blocked report generation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "blocked.md"

        guardrails = TrainingGuardrails()

        # Create mock verdict
        from hydra.training.guardrails import GateVerdictResult

        verdict = GateVerdictResult(
            training_allowed=False,
            reason="HMM leakage detected",
            gates_passed=["quality"],
            gates_failed=["leakage", "stationarity"],
            matrix_rows=5000,
            matrix_cols=3000,
            date_range="2021-01-01 to 2026-01-01",
            verdict_path="/path/to/gate.json",
        )

        guardrails.write_blocked_report(verdict, output_path)

        assert output_path.exists()

        with open(output_path) as f:
            content = f.read()

        assert "TRAINING BLOCKED" in content
        assert "HMM leakage" in content
        assert "quality" in content
        assert "leakage" in content

        print(f"Blocked report written to {output_path}")
        print(content[:500])


if __name__ == "__main__":
    test_check_gate_verdict_missing()
    test_check_gate_verdict_pass()
    test_check_gate_verdict_fail()
    test_check_data_quality_pass()
    test_check_data_quality_fail()
    test_exclude_non_features()
    test_write_blocked_report()
    print("\nAll guardrail tests passed!")
