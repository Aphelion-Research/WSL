from __future__ import annotations

import sqlite3

from ragd_vault.builder import build_vault
from ragd_vault.doctor import inspect_vault


def _db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE chunks(
            id INTEGER PRIMARY KEY,
            filepath TEXT,
            lang TEXT,
            chunk_type TEXT,
            symbol_name TEXT,
            qualified_name TEXT,
            parent_symbol TEXT,
            line_start INTEGER,
            line_end INTEGER,
            docstring TEXT,
            imports_json TEXT,
            calls_json TEXT,
            is_public INTEGER,
            content_hash TEXT,
            modified_at INTEGER,
            status TEXT
        )
        """
    )
    conn.execute("INSERT INTO chunks VALUES (1, '/home/Martin/Dominion/pkg/a.py', 'python', 'function', 'f', 'pkg.a.f', '', 1, 4, 'Do f.', '[\"os\"]', '[\"g\"]', 1, 'abc', 1, 'active')")
    conn.commit()
    conn.close()


def test_file_and_symbol_notes_are_valid(tmp_path):
    db = tmp_path / "ragd.db"
    vault = tmp_path / "vault"
    _db(db)
    result = build_vault(vault, ragd_db=db)
    assert result["files"] == 1
    assert (vault / "files" / "pkg" / "a.md").exists()
    assert list((vault / "symbols").rglob("*.md"))
    report = inspect_vault(vault)
    assert report.ok
    assert report.total_notes >= 4
