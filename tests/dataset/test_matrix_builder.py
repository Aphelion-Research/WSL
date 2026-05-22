"""Test HYDRA matrix builder."""
import pytest
import polars as pl

from dominion.dataset.registries import HYDRA_REGISTRY
from dominion.matrix.builder import MatrixBuilder
from dominion.quality.gates import run_all_gates, print_gate_report


def test_registry_exact_3000():
    """Verify registry has exactly 3,000 columns."""
    assert len(HYDRA_REGISTRY.columns) == 3000
    assert len(HYDRA_REGISTRY.column_names) == 3000


def test_registry_summary():
    """Check registry summary."""
    summary = HYDRA_REGISTRY.summary()
    assert summary["total_columns"] == 3000
    assert summary["available"] > 0
    assert summary["unavailable"] > 0
    assert summary["reserved"] == 50  # Z1, Z2, Z3


def test_build_small_matrix():
    """Build a small matrix for testing."""
    builder = MatrixBuilder()

    matrix = builder.build(
        h1_data_path="/home/Martin/Dominion/data/mt5_history/XAUUSD_H1.parquet",
        output_path=None,
        max_rows=500
    )

    # Check shape
    assert matrix.width == 3001  # 3,000 + time
    assert matrix.height == 500

    # Check time column
    assert "time" in matrix.columns
    assert matrix["time"].dtype == pl.Datetime

    # Check Block A
    assert "A_open" in matrix.columns
    assert "A_close" in matrix.columns
    assert matrix["A_close"].dtype == pl.Float32

    # Check Block C (rolling features)
    assert "C_0000" in matrix.columns

    # Check Block D (technical)
    assert "D_0000" in matrix.columns

    # Check Block G (time features)
    assert "G_0000" in matrix.columns

    # Check Block Z4 (labels)
    assert "Z4_0000" in matrix.columns


def test_quality_gates(monkeypatch, tmp_path):
    """Test quality gates on small matrix."""
    builder = MatrixBuilder()

    matrix = builder.build(
        h1_data_path="/home/Martin/Dominion/data/mt5_history/XAUUSD_H1.parquet",
        output_path=None,
        max_rows=1000
    )

    # Isolate the H1 smoke matrix from the repo-level M5 semantic mapping file.
    monkeypatch.chdir(tmp_path)

    training_allowed, results = run_all_gates(matrix)

    print_gate_report(results)

    # Should pass shape gate
    shape_gate = [r for r in results if r.gate_name == "shape"][0]
    assert shape_gate.passed

    # Should have labels
    label_gate = [r for r in results if r.gate_name == "labels"][0]
    assert label_gate.passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
