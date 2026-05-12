from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from ragd.scripts.ragd_maintenance import build_report, cleanup_duplicates


def _mk_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE chunks(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          filepath TEXT NOT NULL,
          content TEXT NOT NULL,
          content_hash TEXT,
          status TEXT DEFAULT 'active',
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    return conn


def test_report_empty_db(tmp_path: Path):
    db_path = tmp_path / "ragd.db"
    conn = _mk_db(db_path)
    report = build_report(conn, db_path)
    assert report.ok is True
    assert report.chunks_total == 0
    assert report.duplicate_hash_groups == 0


def test_duplicate_detection_and_dry_run(tmp_path: Path):
    db_path = tmp_path / "ragd.db"
    conn = _mk_db(db_path)
    conn.executemany(
        "INSERT INTO chunks(filepath, content, content_hash, status) VALUES(?, ?, ?, 'active')",
        [
            ("a.py", "one", "h1"),
            ("a.py", "one", "h1"),
            ("b.py", "two", "h2"),
            ("b.py", "two", "h2"),
            ("b.py", "two", "h2"),
        ],
    )
    conn.commit()

    report = build_report(conn, db_path)
    assert report.duplicate_hash_groups == 2
    assert report.duplicate_hash_rows == 5

    planned = cleanup_duplicates(conn, dry_run=True)
    assert planned["ok"] is True
    assert planned["dry_run"] is True
    assert planned["candidates"] == 3  # 1 delete for h1, 2 deletes for h2

    # ensure no mutation in dry-run
    active = conn.execute("SELECT COUNT(*) FROM chunks WHERE status='active'").fetchone()[0]
    deleted = conn.execute("SELECT COUNT(*) FROM chunks WHERE status='deleted'").fetchone()[0]
    assert int(active) == 5
    assert int(deleted) == 0


def test_apply_marks_deleted(tmp_path: Path):
    db_path = tmp_path / "ragd.db"
    conn = _mk_db(db_path)
    conn.executemany(
        "INSERT INTO chunks(filepath, content, content_hash, status) VALUES(?, ?, ?, 'active')",
        [("a.py", "one", "h1"), ("a.py", "one", "h1")],
    )
    conn.commit()
    result = cleanup_duplicates(conn, dry_run=False)
    assert result["ok"] is True
    assert result["dry_run"] is False
    assert result["candidates"] == 1
    assert conn.execute("SELECT COUNT(*) FROM chunks WHERE status='deleted'").fetchone()[0] == 1

