"""Tests for dominion_loader.scan — end-to-end scan pipeline."""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dominion_loader.manifest import Manifest
from dominion_loader.ignore import Ignore
from dominion_loader.obs import _NullTracer, set_tracer
from dominion_loader.scan import scan, ScanStats


@pytest.fixture(autouse=True)
def null_tracer():
    set_tracer(_NullTracer())


@pytest.fixture
def small_repo(tmp_path: Path) -> Path:
    """Synthetic small repo: 5 indexable files + some ignored."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hello')\n")
    (tmp_path / "src" / "utils.py").write_text("def add(a, b): return a + b\n")
    (tmp_path / "README.md").write_text("# Test\n")
    (tmp_path / "config.yaml").write_text("key: value\n")
    (tmp_path / "script.sh").write_text("#!/bin/bash\necho hi\n")
    # Ignored
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("[core]\n")
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "key.txt").write_text("SECRET")
    return tmp_path


# ---------------------------------------------------------------------------
# Basic scan
# ---------------------------------------------------------------------------
def test_scan_dry_run_returns_stats(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    stats = scan(small_repo, dry_run=True, manifest=m)
    assert isinstance(stats, ScanStats)
    assert stats.files_seen >= 5
    m.close()


def test_scan_populates_manifest(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)
    active = list(m.list_active())
    assert len(active) >= 5
    m.close()


def test_scan_secrets_not_indexed(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)
    for entry in m.list_active():
        assert "secrets" not in entry.relative_path, f"Secrets leaked: {entry.relative_path}"
    m.close()


# ---------------------------------------------------------------------------
# Incremental scan (core invariant)
# ---------------------------------------------------------------------------
def test_rescan_with_no_changes_produces_zero_new_files(small_repo: Path, tmp_path: Path) -> None:
    """Second scan with no file changes → 0 new files."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)
    stats2 = scan(small_repo, manifest=m)
    assert stats2.files_new == 0, f"Expected 0 new files on rescan, got {stats2.files_new}"
    m.close()


def test_rescan_detects_changed_file(small_repo: Path, tmp_path: Path) -> None:
    """A modified file is detected on rescan."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)

    # Modify a file
    f = small_repo / "src" / "main.py"
    f.write_text("print('changed')\n")

    stats2 = scan(small_repo, manifest=m, force_full=True)
    assert stats2.files_changed >= 1
    m.close()


def test_rescan_detects_new_file(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)

    # Add a new file
    (small_repo / "newfile.py").write_text("x = 42\n")
    stats2 = scan(small_repo, manifest=m)
    assert stats2.files_new >= 1
    m.close()


def test_rescan_detects_deleted_file(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)

    # Delete a file
    (small_repo / "README.md").unlink()
    stats2 = scan(small_repo, manifest=m)
    assert stats2.files_deleted >= 1
    m.close()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------
def test_scan_idempotent_manifest_rows(small_repo: Path, tmp_path: Path) -> None:
    """Multiple scans on unchanged repo → same manifest row count."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    scan(small_repo, manifest=m)
    count1 = m.stats()["active"]
    scan(small_repo, manifest=m)
    count2 = m.stats()["active"]
    assert count1 == count2
    m.close()


# ---------------------------------------------------------------------------
# Binary file handling
# ---------------------------------------------------------------------------
def test_binary_files_not_indexed(tmp_path: Path) -> None:
    """Binary files are excluded from the manifest."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("x = 1\n")
    (repo / "binary.bin").write_bytes(b"\x00\x01\x02\x03" * 100)

    scan(repo, manifest=m)
    active_paths = {e.relative_path for e in m.list_active()}
    assert "main.py" in active_paths
    assert "binary.bin" not in active_paths
    m.close()


# ---------------------------------------------------------------------------
# Trace ID
# ---------------------------------------------------------------------------
def test_scan_returns_trace_id(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    stats = scan(small_repo, manifest=m, trace_id="test-trace-id")
    assert stats.trace_id == "test-trace-id"
    m.close()
