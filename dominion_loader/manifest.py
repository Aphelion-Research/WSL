"""Durable manifest SQLite store for dominion_loader.

Stores per-file metadata: content_hash, mtime_ns, size, document_id,
file_class, language, indexed_at, ragd_ingested_at.

Design:
- Single file at ~/.dominion/manifest.db (WAL mode).
- Additive-only schema migrations (CREATE TABLE IF NOT EXISTS + guarded ALTER TABLE).
- Schema versioned via kv_store('schema_version').
- Manifest is rebuildable from a full scan; not a source of truth for chunk content.

INTERFACE(agent-1): Manifest class  (stable, consumed by Agent 2 via list_changed_since)
"""
from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

CURRENT_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS kv_store(
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_manifest(
    document_id     TEXT PRIMARY KEY,
    repo_root       TEXT NOT NULL,
    relative_path   TEXT NOT NULL,
    file_class      TEXT NOT NULL DEFAULT 'unknown',
    language        TEXT NOT NULL DEFAULT 'unknown',
    content_hash    TEXT NOT NULL DEFAULT '',
    mtime_ns        INTEGER NOT NULL DEFAULT 0,
    size            INTEGER NOT NULL DEFAULT 0,
    indexed_at      INTEGER NOT NULL DEFAULT 0,
    ragd_ingested   INTEGER NOT NULL DEFAULT 0,
    ragd_ingested_at INTEGER,
    status          TEXT NOT NULL DEFAULT 'active'
);

CREATE INDEX IF NOT EXISTS idx_manifest_repo_path
    ON file_manifest(repo_root, relative_path);

CREATE INDEX IF NOT EXISTS idx_manifest_status
    ON file_manifest(status);

CREATE INDEX IF NOT EXISTS idx_manifest_indexed_at
    ON file_manifest(indexed_at);

CREATE TABLE IF NOT EXISTS scan_runs(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id    TEXT NOT NULL,
    repo_root   TEXT NOT NULL,
    started_at  INTEGER NOT NULL,
    finished_at INTEGER,
    files_seen  INTEGER DEFAULT 0,
    files_new   INTEGER DEFAULT 0,
    files_changed INTEGER DEFAULT 0,
    files_deleted INTEGER DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'running'
);
"""

_MIGRATIONS_V1 = [
    # Add columns that might be missing from older schema versions
    ("file_manifest", "ragd_ingested", "INTEGER NOT NULL DEFAULT 0"),
    ("file_manifest", "ragd_ingested_at", "INTEGER"),
]


@dataclass(frozen=True)
class ManifestEntry:
    document_id: str
    repo_root: str
    relative_path: str
    file_class: str
    language: str
    content_hash: str
    mtime_ns: int
    size: int
    indexed_at: int
    ragd_ingested: int
    ragd_ingested_at: Optional[int]
    status: str


class Manifest:
    """Persistent file manifest backed by SQLite WAL.

    Thread-safety: each Manifest owns a single connection. Create one per thread.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            dominion_home = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
            dominion_home.mkdir(parents=True, exist_ok=True)
            db_path = dominion_home / "manifest.db"
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema setup
    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        self._conn.executescript(_SCHEMA_SQL)
        self._apply_migrations()
        version = self._conn.execute(
            "SELECT value FROM kv_store WHERE key='schema_version'"
        ).fetchone()
        if version is None:
            self._conn.execute(
                "INSERT OR REPLACE INTO kv_store(key, value) VALUES('schema_version', ?)",
                (str(CURRENT_SCHEMA_VERSION),),
            )
            self._conn.commit()

    def _apply_migrations(self) -> None:
        """Apply additive column migrations guarded by PRAGMA table_info."""
        for table, col, definition in _MIGRATIONS_V1:
            existing_cols = {
                row[1]
                for row in self._conn.execute(f"PRAGMA table_info({table})")
            }
            if col not in existing_cols:
                self._conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {col} {definition}"
                )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, document_id: str) -> Optional[ManifestEntry]:
        """Retrieve a manifest entry by document_id."""
        row = self._conn.execute(
            "SELECT * FROM file_manifest WHERE document_id=?",
            (document_id,),
        ).fetchone()
        return _row_to_entry(row) if row else None

    def upsert(self, entry: ManifestEntry) -> None:
        """Insert or replace a manifest entry atomically."""
        with self._transaction():
            self._conn.execute(
                """
                INSERT OR REPLACE INTO file_manifest(
                    document_id, repo_root, relative_path, file_class, language,
                    content_hash, mtime_ns, size, indexed_at, ragd_ingested,
                    ragd_ingested_at, status
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    entry.document_id, entry.repo_root, entry.relative_path,
                    entry.file_class, entry.language, entry.content_hash,
                    entry.mtime_ns, entry.size, entry.indexed_at,
                    entry.ragd_ingested, entry.ragd_ingested_at, entry.status,
                ),
            )

    def mark_deleted(self, document_id: str) -> None:
        """Mark a document as deleted (soft delete)."""
        with self._transaction():
            self._conn.execute(
                "UPDATE file_manifest SET status='deleted' WHERE document_id=?",
                (document_id,),
            )

    def list_changed_since(self, epoch: int) -> Iterator[ManifestEntry]:
        """Yield manifest entries modified since epoch (seconds since Unix epoch)."""
        cursor = self._conn.execute(
            "SELECT * FROM file_manifest WHERE indexed_at > ? AND status='active' ORDER BY indexed_at DESC",
            (epoch,),
        )
        for row in cursor:
            yield _row_to_entry(row)

    def list_active(self) -> Iterator[ManifestEntry]:
        """Yield all active manifest entries."""
        for row in self._conn.execute(
            "SELECT * FROM file_manifest WHERE status='active' ORDER BY relative_path"
        ):
            yield _row_to_entry(row)

    def list_all_document_ids(self, repo_root: str) -> set[str]:
        """Return all known document IDs for a given repo root."""
        rows = self._conn.execute(
            "SELECT document_id FROM file_manifest WHERE repo_root=?",
            (repo_root,),
        ).fetchall()
        return {row[0] for row in rows}

    def mark_ragd_ingested(self, document_id: str) -> None:
        """Mark a document as ingested into RAGD."""
        now = int(time.time())
        with self._transaction():
            self._conn.execute(
                "UPDATE file_manifest SET ragd_ingested=1, ragd_ingested_at=? WHERE document_id=?",
                (now, document_id),
            )

    def start_scan_run(self, trace_id: str, repo_root: str) -> int:
        """Record a scan run start; returns the run ID."""
        now = int(time.time())
        cursor = self._conn.execute(
            "INSERT INTO scan_runs(trace_id, repo_root, started_at, status) VALUES(?,?,?,'running')",
            (trace_id, repo_root, now),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    def finish_scan_run(
        self, run_id: int, *, files_seen: int, files_new: int,
        files_changed: int, files_deleted: int, status: str = "completed"
    ) -> None:
        now = int(time.time())
        self._conn.execute(
            """UPDATE scan_runs SET finished_at=?, files_seen=?, files_new=?,
               files_changed=?, files_deleted=?, status=? WHERE id=?""",
            (now, files_seen, files_new, files_changed, files_deleted, status, run_id),
        )
        self._conn.commit()

    def stats(self) -> dict[str, int]:
        """Return manifest statistics."""
        active = self._conn.execute(
            "SELECT COUNT(*) FROM file_manifest WHERE status='active'"
        ).fetchone()[0]
        deleted = self._conn.execute(
            "SELECT COUNT(*) FROM file_manifest WHERE status='deleted'"
        ).fetchone()[0]
        ingested = self._conn.execute(
            "SELECT COUNT(*) FROM file_manifest WHERE ragd_ingested=1 AND status='active'"
        ).fetchone()[0]
        return {"active": active, "deleted": deleted, "ragd_ingested": ingested}

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _transaction(self):
        """Context manager for an explicit transaction."""
        return _Transaction(self._conn)


class _Transaction:
    """Simple context manager for SQLite transactions."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def __enter__(self) -> "_Transaction":
        self._conn.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._conn.execute("COMMIT")
        else:
            self._conn.execute("ROLLBACK")
        return False


def _row_to_entry(row: sqlite3.Row) -> ManifestEntry:
    d = dict(row)
    return ManifestEntry(
        document_id=d["document_id"],
        repo_root=d["repo_root"],
        relative_path=d["relative_path"],
        file_class=d["file_class"],
        language=d["language"],
        content_hash=d["content_hash"],
        mtime_ns=d["mtime_ns"],
        size=d["size"],
        indexed_at=d["indexed_at"],
        ragd_ingested=d.get("ragd_ingested", 0),
        ragd_ingested_at=d.get("ragd_ingested_at"),
        status=d["status"],
    )
