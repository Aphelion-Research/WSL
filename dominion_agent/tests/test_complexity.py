"""Tests for complexity budget tracking."""
from __future__ import annotations

from pathlib import Path

import pytest

from dominion_agent.complexity import (
    COMPLEXITY_BUDGETS,
    _scan_package,
    _compute_score,
    complexity_report,
    all_packages_report,
)
from dominion_agent.types import ComplexityMetrics


# ---------------------------------------------------------------------------
# _scan_package
# ---------------------------------------------------------------------------

def test_scan_empty_dir(tmp_path):
    metrics = _scan_package(tmp_path)
    assert metrics.file_count == 0
    assert metrics.public_symbol_count == 0


def test_scan_counts_files(tmp_path):
    (tmp_path / "a.py").write_text("def foo(): pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def bar(): pass\ndef _priv(): pass\n", encoding="utf-8")
    metrics = _scan_package(tmp_path)
    assert metrics.file_count == 2
    assert metrics.public_symbol_count == 2  # foo + bar (not _priv)


def test_scan_counts_todos(tmp_path):
    (tmp_path / "x.py").write_text(
        "# TODO: fix this\n# FIXME: also this\ndef f(): pass\n",
        encoding="utf-8",
    )
    metrics = _scan_package(tmp_path)
    assert metrics.todo_count >= 2


def test_scan_counts_temp_adapters(tmp_path):
    (tmp_path / "x.py").write_text(
        "# TEMP_ADAPTER: remove when done\ndef f(): pass\n",
        encoding="utf-8",
    )
    metrics = _scan_package(tmp_path)
    assert metrics.temp_adapter_count >= 1


def test_scan_counts_broad_excepts(tmp_path):
    (tmp_path / "x.py").write_text(
        "try:\n    pass\nexcept Exception:\n    pass\n",
        encoding="utf-8",
    )
    metrics = _scan_package(tmp_path)
    assert metrics.broad_except_count >= 1


def test_scan_skips_pycache(tmp_path):
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "cached.py").write_text("def evil(): pass\n", encoding="utf-8")
    (tmp_path / "real.py").write_text("def good(): pass\n", encoding="utf-8")
    metrics = _scan_package(tmp_path)
    assert metrics.file_count == 1  # only real.py


# ---------------------------------------------------------------------------
# _compute_score
# ---------------------------------------------------------------------------

def test_compute_score_zero_for_empty():
    m = ComplexityMetrics(
        file_count=0, public_symbol_count=0, cli_command_count=0,
        test_count=0, todo_count=0, temp_adapter_count=0,
        broad_except_count=0, untested_module_count=0,
        large_file_penalty=0.0, average_file_lines=0.0,
        largest_file_lines=0, test_to_source_ratio=0.0,
    )
    assert _compute_score(m) == 0.0


def test_tests_reduce_score():
    m_no_tests = ComplexityMetrics(
        file_count=5, public_symbol_count=10, cli_command_count=0,
        test_count=0, todo_count=0, temp_adapter_count=0,
        broad_except_count=0, untested_module_count=0,
        large_file_penalty=0.0, average_file_lines=50.0,
        largest_file_lines=100, test_to_source_ratio=0.0,
    )
    m_with_tests = ComplexityMetrics(
        file_count=5, public_symbol_count=10, cli_command_count=0,
        test_count=10, todo_count=0, temp_adapter_count=0,
        broad_except_count=0, untested_module_count=0,
        large_file_penalty=0.0, average_file_lines=50.0,
        largest_file_lines=100, test_to_source_ratio=1.0,
    )
    assert _compute_score(m_with_tests) < _compute_score(m_no_tests)


def test_temp_adapter_inflates_score():
    m_clean = ComplexityMetrics(
        file_count=5, public_symbol_count=5, cli_command_count=0,
        test_count=5, todo_count=0, temp_adapter_count=0,
        broad_except_count=0, untested_module_count=0,
        large_file_penalty=0.0, average_file_lines=50.0,
        largest_file_lines=100, test_to_source_ratio=1.0,
    )
    m_dirty = ComplexityMetrics(
        file_count=5, public_symbol_count=5, cli_command_count=0,
        test_count=5, todo_count=0, temp_adapter_count=3,
        broad_except_count=0, untested_module_count=0,
        large_file_penalty=0.0, average_file_lines=50.0,
        largest_file_lines=100, test_to_source_ratio=1.0,
    )
    assert _compute_score(m_dirty) > _compute_score(m_clean)


# ---------------------------------------------------------------------------
# complexity_report
# ---------------------------------------------------------------------------

def test_complexity_report_missing_package(tmp_path):
    r = complexity_report("nonexistent_pkg", root=str(tmp_path))
    assert r.score == 0.0
    assert r.warnings  # should have a warning about missing dir


def test_complexity_report_over_budget(tmp_path):
    pkg = tmp_path / "mypackage"
    pkg.mkdir()
    # Write many files with TODOs to inflate score past any budget
    for i in range(30):
        (pkg / f"mod_{i}.py").write_text(
            f"# TODO: fix\n# TODO: also\ndef func_{i}(): pass\n" * 5,
            encoding="utf-8",
        )
    r = complexity_report("mypackage", root=str(tmp_path))
    assert r.score > 0


def test_complexity_report_warns_temp_adapter(tmp_path):
    pkg = tmp_path / "mypkg2"
    pkg.mkdir()
    (pkg / "a.py").write_text("# TEMP_ADAPTER: cleanup needed\ndef f(): pass\n",
                               encoding="utf-8")
    r = complexity_report("mypkg2", root=str(tmp_path))
    assert any("TEMP_ADAPTER" in w for w in r.warnings)


# ---------------------------------------------------------------------------
# all_packages_report
# ---------------------------------------------------------------------------

def test_all_packages_report_returns_list(tmp_path):
    reports = all_packages_report(root=str(tmp_path))
    assert isinstance(reports, list)
    assert len(reports) == len(COMPLEXITY_BUDGETS)


def test_budgets_dict_not_empty():
    assert len(COMPLEXITY_BUDGETS) > 0
    assert "dominion_agent" in COMPLEXITY_BUDGETS
