"""Tests for dominion_loader.bench — runner emits valid JSON, suite registration."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from dominion_loader.bench import (
    BenchResult,
    register_suite,
    run_suite,
    list_suites,
    _percentile,
)


# ---------------------------------------------------------------------------
# BenchResult
# ---------------------------------------------------------------------------
def test_bench_result_percentiles() -> None:
    r = BenchResult("test", [1.0, 2.0, 3.0, 4.0, 5.0], "seconds")
    assert r.p50 == 3.0
    assert r.p95 >= 4.0
    assert r.p99 >= 4.0


def test_bench_result_to_dict() -> None:
    r = BenchResult("test", [1.0, 2.0, 3.0], "seconds")
    d = r.to_dict()
    assert "p50" in d
    assert "p95" in d
    assert "p99" in d
    assert "mean" in d
    assert d["unit"] == "seconds"
    assert d["n"] == 3


def test_bench_result_empty_runs() -> None:
    r = BenchResult("empty", [], "s")
    d = r.to_dict()
    assert d["p50"] == 0.0


# ---------------------------------------------------------------------------
# Suite registration
# ---------------------------------------------------------------------------
def test_register_and_list_suite() -> None:
    def my_suite(runs: int) -> dict:
        return {"metric_a": BenchResult("metric_a", [0.1] * runs, "s")}

    register_suite("test_suite_xyz", my_suite)
    assert "test_suite_xyz" in list_suites()


def test_run_suite_emits_json(tmp_path: Path) -> None:
    """run_suite writes a valid JSON file."""
    def fast_suite(runs: int) -> dict:
        return {"t": BenchResult("t", [0.001 * (i + 1) for i in range(runs)], "s")}

    register_suite("fast_test_suite", fast_suite)
    result = run_suite("fast_test_suite", runs=2, out_dir=tmp_path)

    assert "suite" in result
    assert result["suite"] == "fast_test_suite"
    assert result["runs"] == 2
    assert "metrics" in result
    assert "t" in result["metrics"]

    # Written to disk
    files = list(tmp_path.glob("fast_test_suite-*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["suite"] == "fast_test_suite"


def test_run_unknown_suite_raises() -> None:
    with pytest.raises(KeyError):
        run_suite("nonexistent_suite_abc")


def test_percentile_helper() -> None:
    values = list(range(100))
    # Implementation: idx = min(int(len * p / 100), len-1)
    # For 100 values: p50 → idx=50 → sv[50]=50, p95 → idx=95 → sv[95]=95
    assert _percentile(values, 50) == 50
    assert _percentile(values, 95) == 95
    assert _percentile([], 50) == 0.0


# ---------------------------------------------------------------------------
# Foundation suite smoke test
# ---------------------------------------------------------------------------
def test_foundation_suite_registered() -> None:
    """Foundation suite is registered at import time."""
    assert "foundation" in list_suites()


def test_foundation_suite_produces_valid_schema(tmp_path: Path) -> None:
    """Run foundation suite with 1 run — should complete and return JSON."""
    result = run_suite("foundation", runs=1, out_dir=tmp_path)
    assert result["suite"] == "foundation"
    assert result["runs"] == 1
    metrics = result["metrics"]
    assert "cold_scan_s" in metrics
    assert "warm_scan_s" in metrics
    assert "files_per_sec" in metrics

    # Verify JSON schema
    for name, m in metrics.items():
        assert "p50" in m
        assert "p95" in m
        assert "n" in m
        assert "unit" in m
