"""Tests for dominion_loader.ignore — table-driven rule coverage."""
from __future__ import annotations

import tempfile
import json
from pathlib import Path

import pytest

from dominion_loader.ignore import Ignore, _BUILTIN_DIR_DENY, export_policy, policy_hash


# ---------------------------------------------------------------------------
# Table-driven ignore rule tests
# ---------------------------------------------------------------------------
MUST_IGNORE = [
    "secrets/mt5.env",
    "secrets/api_key.txt",
    ".git/config",
    ".git/HEAD",
    ".venv/lib/python3.13/site.py",
    "node_modules/lodash/index.js",
    "__pycache__/foo.cpython-313.pyc",
    "build/libfoo.so",
    "vendor/googletest/gtest.h",
    "data/raw/mt5/ticks.csv",
    "data/normalized/mt5/xauusd.parquet",
    "backups/20260511/file.txt",
    "models/active/llama.gguf",
    "apps/mt5/drive_c/Program Files/MT5.exe",
    "file.duckdb",
    "research.db",
    "manifest.sqlite3",
    "model.gguf",
    "model.bin",
    ".gitignore_swp",
    "images/logo.png",
    "archive.tar.gz",
    "dist/package.whl",
    "src/__pycache__/module.pyc",
    ".cache/pip/foo.whl",
    ".mypy_cache/foo.json",
]

MUST_NOT_IGNORE = [
    "dominion_loader/ignore.py",
    "ragd/src/indexer.cpp",
    "research_os/cli.py",
    "scripts/dominion_cli.py",
    "docs/AGENTS.md",
    "README.md",
    "PROGRESS.md",
    "ragd/CMakeLists.txt",
    "research/sources.yaml",
    ".dominionignore",
]


@pytest.fixture
def ignore() -> Ignore:
    return Ignore()


@pytest.mark.parametrize("rel_path", MUST_IGNORE)
def test_must_ignore(ignore: Ignore, rel_path: str) -> None:
    """Built-in deny rules must reject these paths."""
    assert ignore.match(Path(rel_path)), f"Expected {rel_path!r} to be ignored"


@pytest.mark.parametrize("rel_path", MUST_NOT_IGNORE)
def test_must_not_ignore(ignore: Ignore, rel_path: str) -> None:
    """These paths must NOT be ignored."""
    assert not ignore.match(Path(rel_path)), f"Expected {rel_path!r} to NOT be ignored"


def test_secrets_rule_immutable() -> None:
    """secrets/ must always appear in built-in rules even if user tries to remove it."""
    rules = Ignore.builtin_rules()
    assert rules["secrets_always_ignored"] is True
    assert "secrets" in rules["dir_deny"]


def test_secrets_not_overridable(tmp_path: Path) -> None:
    """A .dominionignore cannot remove the secrets/ rule."""
    # Create a .dominionignore that tries to whitelist secrets
    dominionignore = tmp_path / ".dominionignore"
    dominionignore.write_text("# allow secrets\n!secrets\n")

    ignore = Ignore(dominionignore_path=dominionignore)
    assert ignore.match(Path("secrets/mt5.env"))


def test_user_dominionignore_pattern(tmp_path: Path) -> None:
    """User-supplied .dominionignore patterns are respected for non-builtin paths."""
    dominionignore = tmp_path / ".dominionignore"
    dominionignore.write_text("runs/*\nreports/archive*\n")

    ignore = Ignore(dominionignore_path=dominionignore)
    assert ignore.match(Path("runs/paper/session.json"))
    assert ignore.match(Path("reports/archive_old.md"))
    assert not ignore.match(Path("dominion_loader/scan.py"))


def test_size_limit() -> None:
    """Files over max_bytes should be filtered."""
    ignore = Ignore(max_bytes=1024)
    assert ignore.match_size(2048)
    assert not ignore.match_size(512)


def test_builtin_rules_export() -> None:
    """builtin_rules() returns a dict with expected keys."""
    rules = Ignore.builtin_rules()
    assert "dir_deny" in rules
    assert "path_deny" in rules
    assert "ext_deny" in rules
    assert "secrets_always_ignored" in rules
    # Sanity: secrets in dir_deny
    assert "secrets" in rules["dir_deny"]
    # Sanity: at least 10 dir rules
    assert len(rules["dir_deny"]) >= 10


def test_policy_hash_stable_for_same_rules() -> None:
    first = policy_hash()
    second = policy_hash()
    assert first == second
    assert len(first) == 64


def test_export_policy_matches_builtin_rules() -> None:
    assert export_policy() == Ignore.builtin_rules()


def test_generated_policy_config_matches_export() -> None:
    config_path = Path(__file__).parents[2] / "config" / "dominion_ignore_policy.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["policy"] == export_policy()
    assert data["policy_hash"] == policy_hash()
