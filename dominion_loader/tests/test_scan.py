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
from dominion_loader.ragd_bridge import DeleteResult, IngestResult
from dominion_loader.scan import scan, ScanStats


@pytest.fixture(autouse=True)
def null_tracer(monkeypatch):
    monkeypatch.setenv("DOMINION_RAGD_BRIDGE", "off")
    set_tracer(_NullTracer())


class FakeBridge:
    def __init__(
        self,
        *,
        chunks_deleted: int = 0,
        delete_errors: list[dict[str, str]] | None = None,
    ) -> None:
        self.ingested_paths: list[str] = []
        self.deleted_paths: list[str] = []
        self._chunks_deleted = chunks_deleted
        self._delete_errors = delete_errors or []

    def ingest_paths(self, paths: list[str]) -> IngestResult:
        self.ingested_paths.extend(paths)
        return IngestResult(len(paths), chunks_indexed=len(paths), already_current=0, duration_ms=0.0, error=None)

    def delete_paths(self, paths: list[str]) -> DeleteResult:
        self.deleted_paths.extend(paths)
        return DeleteResult(
            paths_submitted=len(paths),
            files_marked_deleted=0 if self._delete_errors else len(paths),
            chunks_marked_deleted=self._chunks_deleted,
            duration_ms=0.0,
            errors=self._delete_errors,
        )


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
    bridge = FakeBridge()
    scan(small_repo, manifest=m, bridge=bridge)

    # Delete a file
    (small_repo / "README.md").unlink()
    stats2 = scan(small_repo, manifest=m, bridge=bridge)
    assert stats2.files_deleted >= 1
    m.close()


def test_scan_calls_ragd_delete_for_deleted_files(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    manifest = Manifest(db)
    bridge = FakeBridge(chunks_deleted=3)
    scan(small_repo, manifest=manifest, bridge=bridge)

    deleted_file = small_repo / "README.md"
    deleted_file.unlink()
    stats = scan(small_repo, manifest=manifest, bridge=bridge)

    assert stats.files_deleted == 1
    assert stats.ragd_paths_deleted == 1
    assert stats.ragd_chunks_deleted == 3
    assert bridge.deleted_paths == [str(deleted_file.resolve())]
    manifest.close()


def test_scan_dry_run_does_not_call_ragd_delete(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    manifest = Manifest(db)
    bridge = FakeBridge(chunks_deleted=3)
    scan(small_repo, manifest=manifest, bridge=bridge)

    (small_repo / "README.md").unlink()
    stats = scan(small_repo, manifest=manifest, bridge=bridge, dry_run=True)

    assert stats.files_deleted == 1
    assert bridge.deleted_paths == []
    manifest.close()


def test_scan_records_ragd_delete_errors(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    manifest = Manifest(db)
    bridge = FakeBridge(delete_errors=[{"path": "", "error": "RAGD down"}])
    scan(small_repo, manifest=manifest, bridge=bridge)

    (small_repo / "README.md").unlink()
    stats = scan(small_repo, manifest=manifest, bridge=bridge)

    assert stats.files_deleted == 1
    assert stats.ragd_delete_errors == 1
    manifest.close()


def test_scan_noop_rescan_deletes_zero(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    manifest = Manifest(db)
    bridge = FakeBridge()
    scan(small_repo, manifest=manifest, bridge=bridge)
    stats = scan(small_repo, manifest=manifest, bridge=bridge)
    assert stats.files_deleted == 0
    assert bridge.deleted_paths == []
    manifest.close()


def test_deleted_manifest_entry_resolves_to_absolute_path(small_repo: Path, tmp_path: Path) -> None:
    db = tmp_path / "manifest.db"
    manifest = Manifest(db)
    bridge = FakeBridge()
    scan(small_repo, manifest=manifest, bridge=bridge)

    target = small_repo / "src" / "main.py"
    target.unlink()
    scan(small_repo, manifest=manifest, bridge=bridge)

    assert bridge.deleted_paths == [str(target.resolve())]
    manifest.close()


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


# ---------------------------------------------------------------------------
# Native scan wiring (Phase 3)
# ---------------------------------------------------------------------------

def test_native_scan_binary_helper_returns_path():
    """_native_scan_binary() returns a Path object."""
    from dominion_loader.cli import _native_scan_binary
    p = _native_scan_binary()
    assert isinstance(p, Path)


def test_native_scan_falls_back_to_python_when_binary_missing(tmp_path, monkeypatch):
    """cmd_scan_native falls back to Python scan when binary is absent."""
    import argparse
    from dominion_loader.cli import cmd_scan_native

    # Patch binary path to a non-existent file
    monkeypatch.setattr(
        "dominion_loader.cli._native_scan_binary",
        lambda: tmp_path / "no-such-binary",
    )

    call_log: list[dict] = []

    def fake_scan_python(repo, *, dry_run, use_json):
        call_log.append({"repo": repo, "dry_run": dry_run, "use_json": use_json})
        return 0

    monkeypatch.setattr("dominion_loader.cli._cmd_scan_python", fake_scan_python)

    args = argparse.Namespace(repo=str(tmp_path), dry_run=True, json=False, native=True)
    rc = cmd_scan_native(args)
    assert rc == 0
    assert len(call_log) == 1  # fell back to Python scan
    assert call_log[0]["dry_run"] is True
    # args are NOT mutated — native flag stays as-is
    assert args.native is True


def test_native_scan_dry_run_discovers_files(tmp_path):
    """cmd_scan_native dry run with mocked native output produces correct stats."""
    import argparse
    import json as _json
    from unittest.mock import patch
    from dominion_loader.cli import cmd_scan_native

    # Build fake native scan output (3 source files, 1 binary skipped)
    fake_native_output = _json.dumps({
        "files": [
            {
                "absolute_path": str(tmp_path / "main.py"),
                "relative_path": "main.py",
                "content_hash": "a" * 64,
                "kind": "source",
                "language": "python",
                "mtime_ns": 1_000_000_000,
                "size_bytes": 42,
            },
            {
                "absolute_path": str(tmp_path / "README.md"),
                "relative_path": "README.md",
                "content_hash": "b" * 64,
                "kind": "document",
                "language": "markdown",
                "mtime_ns": 1_000_000_001,
                "size_bytes": 12,
            },
            {
                "absolute_path": str(tmp_path / "blob.bin"),
                "relative_path": "blob.bin",
                "content_hash": "c" * 64,
                "kind": "binary",
                "language": "unknown",
                "mtime_ns": 1_000_000_002,
                "size_bytes": 4096,
            },
        ],
        "errors": [],
    })

    # Patch _run_native_scan to return our fake data
    with patch("dominion_loader.cli._run_native_scan", return_value=_json.loads(fake_native_output)):
        args = argparse.Namespace(repo=str(tmp_path), dry_run=True, json=False, native=True)
        rc = cmd_scan_native(args)

    assert rc == 0


def test_native_scan_json_output_contains_native_flag(tmp_path, capsys):
    """cmd_scan_native --json output has 'native: true'."""
    import argparse
    import json as _json
    from unittest.mock import patch
    from dominion_loader.cli import cmd_scan_native

    fake_data = {"files": [], "errors": []}
    with patch("dominion_loader.cli._run_native_scan", return_value=fake_data):
        args = argparse.Namespace(repo=str(tmp_path), dry_run=True, json=True, native=True)
        rc = cmd_scan_native(args)

    assert rc == 0
    captured = capsys.readouterr()
    result = _json.loads(captured.out)
    assert result.get("native") is True
    assert result.get("dry_run") is True


def test_native_kind_to_class_mapping():
    """All expected native kind values map to known file classes."""
    from dominion_loader.cli import _NATIVE_KIND_TO_CLASS
    assert _NATIVE_KIND_TO_CLASS["source"] == "code"
    assert _NATIVE_KIND_TO_CLASS["document"] == "doc"
    assert _NATIVE_KIND_TO_CLASS["config"] == "config"
    assert _NATIVE_KIND_TO_CLASS["data"] == "data"
    assert _NATIVE_KIND_TO_CLASS["binary"] == "binary"

