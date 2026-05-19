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
    # Use --offline to avoid depending on RAGD/domdata being live
    result = run_dominion("doctor", "--offline", "--json")
    assert result.returncode == 0, f"doctor --offline --json crashed:\n{result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, dict)
    # Required top-level fields
    assert "checks" in data
    assert "overall" in data


def test_doctor_checks_foundation_components() -> None:
    # Use --offline to test foundation checks without external dependencies
    result = run_dominion("doctor", "--offline", "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    checks = data.get("checks", {})
    # Foundation doctor must include at least these components
    required_checks = {"ignore_rules", "manifest", "cache", "ragd_bridge", "profiler"}
    for check in required_checks:
        assert check in checks, f"Missing doctor check: {check}"


def test_doctor_ignore_rules_always_passes() -> None:
    result = run_dominion("doctor", "--offline", "--json")
    data = json.loads(result.stdout)
    ignore_check = data["checks"].get("ignore_rules", {})
    assert ignore_check.get("status") == "ok", f"ignore_rules check failed: {ignore_check}"


# ---------------------------------------------------------------------------
# Exit semantics (Phase 1 fixes)
# ---------------------------------------------------------------------------

def test_doctor_json_exits_nonzero_on_fail() -> None:
    """doctor --json must exit 1 when overall is fail (not silently exit 0)."""
    result = run_dominion("doctor", "--offline", "--json")
    data = json.loads(result.stdout)
    overall = data.get("overall")
    # If overall is fail, exit must be non-zero
    if overall == "fail":
        assert result.returncode != 0, "doctor --json must exit nonzero on fail"
    # If overall is ok or warn, exit must be 0 (non-strict)
    elif overall in ("ok", "warn"):
        assert result.returncode == 0, f"doctor --json must exit 0 on {overall} (non-strict)"


def test_doctor_json_overall_field_present() -> None:
    """doctor --json must always include overall field with meaningful value."""
    result = run_dominion("doctor", "--offline", "--json")
    data = json.loads(result.stdout)
    assert data.get("overall") in ("ok", "warn", "fail"), f"unexpected overall: {data.get('overall')}"


def test_doctor_strict_exits_one_on_warn() -> None:
    """doctor --strict --json must exit 1 when overall is warn."""
    result_normal = run_dominion("doctor", "--offline", "--json")
    data = json.loads(result_normal.stdout)
    overall = data.get("overall")
    result_strict = run_dominion("doctor", "--offline", "--json", "--strict")
    if overall == "warn":
        assert result_strict.returncode == 1, "--strict must exit 1 when overall=warn"
    elif overall == "ok":
        assert result_strict.returncode == 0, "--strict must exit 0 when overall=ok"


def test_doctor_nonstrict_exits_zero_on_warn() -> None:
    """Without --strict, doctor exits 0 on warn (only fails on fail)."""
    result = run_dominion("doctor", "--offline", "--json")
    data = json.loads(result.stdout)
    if data.get("overall") == "warn":
        assert result.returncode == 0, "non-strict doctor must exit 0 on warn"


def test_doctor_overall_reflects_worst_check_status() -> None:
    """doctor --json overall must be the worst status across all checks."""
    result = run_dominion("doctor", "--offline", "--json")
    data = json.loads(result.stdout)
    checks = data.get("checks", {})
    statuses = {
        v.get("status", "ok") if isinstance(v, dict) and "status" in v else ("ok" if v else "fail")
        for v in checks.values()
    }
    if "fail" in statuses or "error" in statuses:
        assert data["overall"] == "fail", f"overall should be fail when checks have fail: {statuses}"
    elif "warn" in statuses:
        assert data["overall"] == "warn", f"overall should be warn when checks have warn: {statuses}"
    else:
        assert data["overall"] == "ok", f"overall should be ok: {statuses}"
