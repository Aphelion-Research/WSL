"""Tests for dominion doctor foundation checks."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_dominion(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/dominion_cli.py", *args],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parents[2],  # Dominion root
    )


def test_doctor_runs_without_crash() -> None:
    result = run_dominion("doctor", "--offline")
    assert result.returncode == 0, f"doctor --offline crashed:\n{result.stderr}\n{result.stdout}"


def test_doctor_json_output_valid() -> None:
    result = run_dominion("doctor", "--json")
    assert result.returncode == 0, f"doctor --json crashed:\n{result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    # Required top-level fields
    assert "checks" in data
    assert "overall" in data


def test_doctor_checks_foundation_components() -> None:
    result = run_dominion("doctor", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    checks = data.get("checks", {})
    # Foundation doctor must include at least these components
    required_checks = {"ignore_rules", "manifest", "cache", "ragd_bridge", "profiler"}
    for check in required_checks:
        assert check in checks, f"Missing doctor check: {check}"


def test_doctor_ignore_rules_always_passes() -> None:
    result = run_dominion("doctor", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    ignore_check = data["checks"].get("ignore_rules", {})
    assert ignore_check.get("status") == "ok", f"ignore_rules check failed: {ignore_check}"
