"""Tests for domdata/check_no_trading.py repo-wide forbidden-token scanner."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow import of check_no_trading from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "domdata"))

from check_no_trading import scan_repo, should_scan


# ---------------------------------------------------------------------------
# should_scan() path filtering
# ---------------------------------------------------------------------------

def test_should_scan_python_file(tmp_path):
    f = tmp_path / "analysis.py"
    f.write_text("x = 1\n")
    assert should_scan(f, tmp_path) is True


def test_should_scan_rejects_pycache(tmp_path):
    d = tmp_path / "__pycache__"
    d.mkdir()
    f = d / "analysis.cpython-311.pyc"
    f.write_bytes(b"")
    assert should_scan(f, tmp_path) is False


def test_should_scan_rejects_git(tmp_path):
    d = tmp_path / ".git"
    d.mkdir()
    f = d / "config"
    f.write_text("")
    assert should_scan(f, tmp_path) is False


def test_should_scan_rejects_build(tmp_path):
    d = tmp_path / "build"
    d.mkdir()
    f = d / "output.py"
    f.write_text("x=1\n")
    assert should_scan(f, tmp_path) is False


def test_should_scan_allowlisted_filename_shallow(tmp_path):
    """safety.py in top-level package is allowlisted."""
    pkg = tmp_path / "domdata_pkg"
    pkg.mkdir()
    f = pkg / "safety.py"
    f.write_text("")
    assert should_scan(f, tmp_path) is False


def test_should_scan_allowlisted_filename_deep_rejected(tmp_path):
    """safety.py deep in an unrelated tree is NOT allowlisted (path-aware)."""
    deep = tmp_path / "analysis" / "module" / "deep" / "nested"
    deep.mkdir(parents=True)
    f = deep / "safety.py"
    f.write_text("")
    # Depth > 3: should NOT be allowlisted
    assert should_scan(f, tmp_path) is True


def test_should_scan_allowlist_path_prefix(tmp_path):
    """Files under docs/ are allowlisted via allowlist_paths."""
    docs = tmp_path / "docs"
    docs.mkdir()
    f = docs / "SECURITY.md"
    f.write_text("order_send\n")
    assert should_scan(f, tmp_path) is False


def test_should_scan_scans_shell_files(tmp_path):
    f = tmp_path / "deploy.sh"
    f.write_text("echo hello\n")
    assert should_scan(f, tmp_path) is True


def test_should_scan_rejects_binary_suffix(tmp_path):
    f = tmp_path / "model.pkl"
    f.write_bytes(b"\x00\x01\x02")
    assert should_scan(f, tmp_path) is False


# ---------------------------------------------------------------------------
# scan_repo() — token detection
# ---------------------------------------------------------------------------

def test_scan_repo_clean(tmp_path):
    """Clean repo has no violations."""
    (tmp_path / "main.py").write_text("print('hello world')\n")
    (tmp_path / "utils.py").write_text("def add(a, b): return a + b\n")
    assert scan_repo(tmp_path) == []


def test_scan_repo_catches_token_in_python(tmp_path):
    """Forbidden token in plain Python file must be caught."""
    (tmp_path / "trader.py").write_text("result = order_send(request)\n")
    violations = scan_repo(tmp_path)
    assert len(violations) == 1
    assert "order_send" in violations[0]
    assert "trader.py" in violations[0]


def test_scan_repo_catches_token_outside_domdata(tmp_path):
    """Token in a module that is NOT domdata must be caught."""
    pkg = tmp_path / "dominion_ai"
    pkg.mkdir()
    (pkg / "planner.py").write_text("# BAD\nmt5.order_send(req)\n")
    violations = scan_repo(tmp_path)
    assert any("dominion_ai" in v and "order_send" in v for v in violations), violations


def test_scan_repo_catches_shell_token(tmp_path):
    """Forbidden token in a shell script must be caught."""
    (tmp_path / "run.sh").write_text("#!/bin/bash\necho execute_trade\n")
    violations = scan_repo(tmp_path)
    assert any("execute_trade" in v for v in violations), violations


def test_scan_repo_allowlisted_file_ignored(tmp_path):
    """Token in allowlisted safety.py is not reported."""
    pkg = tmp_path / "domdata_pkg"
    pkg.mkdir()
    f = pkg / "safety.py"
    f.write_text("BLOCKED_COMMANDS = {'order-send', 'order_send'}\n")
    violations = scan_repo(tmp_path)
    assert violations == []


def test_scan_repo_docs_dir_ignored(tmp_path):
    """Token in docs/ is not reported (allowlist_paths)."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "SECURITY.md").write_text("Do not call order_send.\n")
    assert scan_repo(tmp_path) == []


def test_scan_repo_cpp_file_scanned(tmp_path):
    """Forbidden token in C++ source must be caught."""
    src = tmp_path / "src"
    src.mkdir()
    (src / "adapter.cpp").write_text('void run() { execute_trade(); }\n')
    violations = scan_repo(tmp_path)
    assert any("execute_trade" in v for v in violations), violations


def test_scan_repo_config_json_allowlisted(tmp_path):
    """forbidden_tokens.json itself is allowlisted via allowlist_paths."""
    cfg = tmp_path / "config"
    cfg.mkdir()
    (cfg / "forbidden_tokens.json").write_text('{"groups":{"x":["order_send"]}}\n')
    # other clean file so repo isn't empty
    (tmp_path / "main.py").write_text("x = 1\n")
    assert scan_repo(tmp_path) == []


def test_scan_repo_multiple_tokens_one_report_per_file(tmp_path):
    """Multiple tokens in one file produce only one violation entry."""
    (tmp_path / "bad.py").write_text("order_send(x)\nOrderSend(y)\n")
    violations = scan_repo(tmp_path)
    files = [v.split(":")[0] for v in violations]
    assert files.count("bad.py") == 1
