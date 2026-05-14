"""Tests for impact analyzer."""
from __future__ import annotations

import pytest

from dominion_agent.impact import analyze_impact


# ---------------------------------------------------------------------------
# Package mapping
# ---------------------------------------------------------------------------

def test_ragd_files_require_cmake(tmp_path):
    report = analyze_impact(files=["ragd/src/http_api.cpp"])
    assert any("cmake" in cmd.lower() for cmd in report.required_commands)
    assert any("ctest" in cmd.lower() for cmd in report.required_commands)


def test_domdata_files_require_no_trading_check(tmp_path):
    report = analyze_impact(files=["domdata/domdata.py"])
    assert any("check_no_trading" in cmd for cmd in report.required_commands)


def test_dominion_loader_requires_pytest(tmp_path):
    report = analyze_impact(files=["dominion_loader/scan.py"])
    assert any("pytest" in cmd for cmd in report.required_commands)
    assert "dominion_loader" in report.affected_packages


def test_dominion_ai_files(tmp_path):
    report = analyze_impact(files=["dominion_ai/api.py"])
    assert "dominion_ai" in report.affected_packages


def test_empty_files_low_risk(tmp_path):
    report = analyze_impact(files=[])
    assert report.risk == "low"
    assert report.required_commands == []


def test_multiple_packages_merged(tmp_path):
    report = analyze_impact(files=["ragd/src/foo.cpp", "domdata/domdata.py"])
    assert "ragd" in report.affected_packages
    assert "domdata" in report.affected_packages
    # Should require both ragd and domdata validation
    cmds = " ".join(report.required_commands)
    assert "cmake" in cmds
    assert "check_no_trading" in cmds


def test_scripts_cli_impact(tmp_path):
    report = analyze_impact(files=["scripts/dominion_cli.py"])
    assert "scripts" in report.affected_packages


def test_ragd_risk_is_high(tmp_path):
    report = analyze_impact(files=["ragd/src/search.cpp"])
    assert report.risk in ("high", "critical")


def test_domdata_risk_is_critical(tmp_path):
    report = analyze_impact(files=["domdata/domdata.py"])
    assert report.risk == "critical"


def test_reasoning_populated(tmp_path):
    report = analyze_impact(files=["ragd/src/x.cpp"])
    assert len(report.reasoning) > 0
