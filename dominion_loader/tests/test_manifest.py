"""Tests for dominion_loader.manifest — schema, upsert, migration, crash recovery."""
from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from pathlib import Path

import pytest

from dominion_loader.manifest import Manifest, ManifestEntry, CURRENT_SCHEMA_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_entry(
    doc_id: str = "abc123",
    repo_root: str = "/repo",
    relative_path: str = "src/foo.py",
    content_hash: str = "deadbeef",
    mtime_ns: int = 1000000,
    size: int = 512,
) -> ManifestEntry:
    return ManifestEntry(
        document_id=doc_id,
        repo_root=repo_root,
        relative_path=relative_path,
        file_class="code",
        language="python",
        content_hash=content_hash,
        mtime_ns=mtime_ns,
        size=size,
        indexed_at=int(time.time()),
        ragd_ingested=0,
        ragd_ingested_at=None,
        status="active",
    )


@pytest.fixture
def manifest(tmp_path: Path) -> Manifest:
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    yield m
    m.close()


# ---------------------------------------------------------------------------
# Schema / migration tests
# ---------------------------------------------------------------------------
def test_schema_creates_tables(manifest: Manifest) -> None:
    """Manifest creates required tables on init."""
    tables = {
        row[0]
        for row in manifest._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "file_manifest" in tables
    assert "scan_runs" in tables
    assert "kv_store" in tables


def test_schema_version_recorded(manifest: Manifest) -> None:
    row = manifest._conn.execute(
        "SELECT value FROM kv_store WHERE key='schema_version'"
    ).fetchone()
    assert row is not None
    assert int(row[0]) == CURRENT_SCHEMA_VERSION


def test_migration_idempotent(tmp_path: Path) -> None:
    """Re-initializing the manifest does not fail or duplicate data."""
    db = tmp_path / "manifest.db"
    m1 = Manifest(db)
    m1.close()
    m2 = Manifest(db)  # Re-open same DB
    m2.close()


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------
def test_upsert_and_get(manifest: Manifest) -> None:
    entry = make_entry(doc_id="abc123", content_hash="hash1")
    manifest.upsert(entry)
    fetched = manifest.get("abc123")
    assert fetched is not None
    assert fetched.document_id == "abc123"
    assert fetched.content_hash == "hash1"
    assert fetched.status == "active"


def test_upsert_updates_existing(manifest: Manifest) -> None:
    entry = make_entry(doc_id="abc123", content_hash="old_hash")
    manifest.upsert(entry)
    updated = make_entry(doc_id="abc123", content_hash="new_hash")
    manifest.upsert(updated)
    fetched = manifest.get("abc123")
    assert fetched.content_hash == "new_hash"


def test_get_missing_returns_none(manifest: Manifest) -> None:
    assert manifest.get("nonexistent_id") is None


def test_mark_deleted(manifest: Manifest) -> None:
    entry = make_entry(doc_id="todelete")
    manifest.upsert(entry)
    manifest.mark_deleted("todelete")
    fetched = manifest.get("todelete")
    assert fetched is not None
    assert fetched.status == "deleted"


def test_list_active_excludes_deleted(manifest: Manifest) -> None:
    manifest.upsert(make_entry(doc_id="active1"))
    manifest.upsert(make_entry(doc_id="active2"))
    manifest.upsert(make_entry(doc_id="deleted1"))
    manifest.mark_deleted("deleted1")

    active_ids = {e.document_id for e in manifest.list_active()}
    assert "active1" in active_ids
    assert "active2" in active_ids
    assert "deleted1" not in active_ids


def test_list_changed_since(manifest: Manifest) -> None:
    old_time = int(time.time()) - 3600
    entry = ManifestEntry(
        document_id="recent",
        repo_root="/repo",
        relative_path="a.py",
        file_class="code",
        language="python",
        content_hash="hh",
        mtime_ns=0,
        size=0,
        indexed_at=int(time.time()),
        ragd_ingested=0,
        ragd_ingested_at=None,
        status="active",
    )
    manifest.upsert(entry)
    results = list(manifest.list_changed_since(old_time))
    assert any(e.document_id == "recent" for e in results)


def test_mark_ragd_ingested(manifest: Manifest) -> None:
    entry = make_entry(doc_id="ingest1")
    manifest.upsert(entry)
    manifest.mark_ragd_ingested("ingest1")
    fetched = manifest.get("ingest1")
    assert fetched.ragd_ingested == 1
    assert fetched.ragd_ingested_at is not None


def test_scan_run_lifecycle(manifest: Manifest) -> None:
    run_id = manifest.start_scan_run("trace123", "/repo")
    assert run_id is not None and run_id > 0
    manifest.finish_scan_run(run_id, files_seen=100, files_new=10, files_changed=5, files_deleted=2)


def test_stats(manifest: Manifest) -> None:
    manifest.upsert(make_entry(doc_id="s1"))
    manifest.upsert(make_entry(doc_id="s2"))
    manifest.upsert(make_entry(doc_id="s3"))
    manifest.mark_deleted("s3")
    stats = manifest.stats()
    assert stats["active"] == 2
    assert stats["deleted"] == 1


def test_crash_recovery(tmp_path: Path) -> None:
    """Manifest is readable after simulated crash (WAL mode)."""
    db = tmp_path / "manifest.db"
    m = Manifest(db)
    m.upsert(make_entry(doc_id="pre_crash"))
    # Close without explicit commit (WAL should handle this)
    m._conn.close()

    # Reopen — should not raise
    m2 = Manifest(db)
    fetched = m2.get("pre_crash")
    assert fetched is not None
    m2.close()
