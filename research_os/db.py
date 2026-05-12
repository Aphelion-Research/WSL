from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import DB_PATH
from .models import DocumentChunk, Source


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  base_url TEXT NOT NULL,
  trust TEXT NOT NULL,
  rate_limit_sec REAL DEFAULT 2.0,
  enabled INTEGER DEFAULT 1,
  adapter_preference TEXT DEFAULT 'requests',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS crawl_jobs(
  id INTEGER PRIMARY KEY,
  url TEXT NOT NULL,
  source_name TEXT NOT NULL,
  status TEXT NOT NULL,
  priority INTEGER DEFAULT 5,
  attempts INTEGER DEFAULT 0,
  last_error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(url, source_name)
);

CREATE TABLE IF NOT EXISTS documents(
  id INTEGER PRIMARY KEY,
  url TEXT UNIQUE NOT NULL,
  source_name TEXT NOT NULL,
  title TEXT,
  fetched_at TEXT,
  status_code INTEGER,
  content_hash TEXT,
  raw_path TEXT,
  markdown_path TEXT,
  text_length INTEGER,
  trust TEXT,
  metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS document_chunks(
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  source_name TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  heading TEXT,
  content TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  token_estimate INTEGER,
  summary TEXT,
  tags_json TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(document_id, chunk_index, content_hash),
  FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS research_notes(
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  content TEXT NOT NULL,
  source_url TEXT,
  tags_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_runs(
  id INTEGER PRIMARY KEY,
  started_at TEXT NOT NULL,
  ended_at TEXT,
  jobs_processed INTEGER DEFAULT 0,
  jobs_succeeded INTEGER DEFAULT 0,
  jobs_failed INTEGER DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS source_health(
  id INTEGER PRIMARY KEY,
  source_name TEXT NOT NULL,
  checked_at TEXT NOT NULL,
  status TEXT NOT NULL,
  latency_ms INTEGER,
  last_error TEXT
);
"""


def initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()


def _migrate(conn: sqlite3.Connection) -> None:
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(sources)")}
    if "adapter_preference" not in cols:
        conn.execute("ALTER TABLE sources ADD COLUMN adapter_preference TEXT DEFAULT 'requests'")


def upsert_source(conn: sqlite3.Connection, source: Source) -> None:
    conn.execute(
        """
        INSERT INTO sources(name, base_url, trust, rate_limit_sec, enabled, adapter_preference, created_at)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
          base_url=excluded.base_url,
          trust=excluded.trust,
          rate_limit_sec=excluded.rate_limit_sec,
          enabled=excluded.enabled,
          adapter_preference=excluded.adapter_preference
        """,
        (source.name, source.base_url, source.trust, source.rate_limit_sec, int(source.enabled), source.adapter_preference, utc_now()),
    )
    conn.commit()


def import_sources(conn: sqlite3.Connection, sources: list[Source]) -> None:
    for source in sources:
        upsert_source(conn, source)


def list_sources(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM sources ORDER BY name"))


def get_source(conn: sqlite3.Connection, name: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sources WHERE name = ?", (name,)).fetchone()


def add_job(conn: sqlite3.Connection, url: str, source_name: str, priority: int = 5) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO crawl_jobs(url, source_name, status, priority, created_at, updated_at)
        VALUES(?, ?, 'queued', ?, ?, ?)
        ON CONFLICT(url, source_name) DO UPDATE SET
          priority=excluded.priority,
          updated_at=excluded.updated_at
        """,
        (url, source_name, priority, now, now),
    )
    conn.commit()


def next_jobs(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT * FROM crawl_jobs
            WHERE status IN ('queued', 'retry')
            ORDER BY priority ASC, created_at ASC
            LIMIT ?
            """,
            (limit,),
        )
    )


def mark_job(conn: sqlite3.Connection, job_id: int, status: str, error: str | None = None) -> None:
    conn.execute(
        """
        UPDATE crawl_jobs
        SET status = ?, last_error = ?, attempts = attempts + 1, updated_at = ?
        WHERE id = ?
        """,
        (status, error, utc_now(), job_id),
    )
    conn.commit()


def create_run(conn: sqlite3.Connection) -> int:
    cur = conn.execute("INSERT INTO research_runs(started_at) VALUES(?)", (utc_now(),))
    conn.commit()
    return int(cur.lastrowid)


def finish_run(conn: sqlite3.Connection, run_id: int, processed: int, succeeded: int, failed: int, notes: str = "") -> None:
    conn.execute(
        """
        UPDATE research_runs
        SET ended_at = ?, jobs_processed = ?, jobs_succeeded = ?, jobs_failed = ?, notes = ?
        WHERE id = ?
        """,
        (utc_now(), processed, succeeded, failed, notes, run_id),
    )
    conn.commit()


def upsert_document(
    conn: sqlite3.Connection,
    *,
    url: str,
    source_name: str,
    title: str,
    fetched_at: str,
    status_code: int,
    content_hash: str,
    raw_path: str,
    markdown_path: str,
    text_length: int,
    trust: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    conn.execute(
        """
        INSERT INTO documents(url, source_name, title, fetched_at, status_code, content_hash, raw_path, markdown_path, text_length, trust, metadata_json)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
          source_name=excluded.source_name,
          title=excluded.title,
          fetched_at=excluded.fetched_at,
          status_code=excluded.status_code,
          content_hash=excluded.content_hash,
          raw_path=excluded.raw_path,
          markdown_path=excluded.markdown_path,
          text_length=excluded.text_length,
          trust=excluded.trust,
          metadata_json=excluded.metadata_json
        """,
        (
            url,
            source_name,
            title,
            fetched_at,
            status_code,
            content_hash,
            raw_path,
            markdown_path,
            text_length,
            trust,
            json.dumps(metadata or {}, sort_keys=True),
        ),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM documents WHERE url = ?", (url,)).fetchone()
    return int(row["id"])


def replace_chunks(conn: sqlite3.Connection, document_id: int, url: str, source_name: str, chunks: list[DocumentChunk]) -> None:
    conn.execute("DELETE FROM document_chunks WHERE document_id = ?", (document_id,))
    for chunk in chunks:
        conn.execute(
            """
            INSERT OR IGNORE INTO document_chunks(document_id, url, source_name, chunk_index, heading, content, content_hash, token_estimate, tags_json, created_at)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                url,
                source_name,
                chunk.chunk_index,
                chunk.heading,
                chunk.content,
                chunk.content_hash,
                chunk.token_estimate,
                "[]",
                utc_now(),
            ),
        )
    conn.commit()


def list_documents(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM documents ORDER BY fetched_at DESC LIMIT ?", (limit,)))


def get_document(conn: sqlite3.Connection, document_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()


def search_chunks(conn: sqlite3.Connection, text: str, limit: int = 10) -> list[sqlite3.Row]:
    like = f"%{text}%"
    return list(
        conn.execute(
            """
            SELECT dc.*, d.title
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE dc.content LIKE ? OR dc.heading LIKE ? OR d.title LIKE ?
            ORDER BY dc.document_id DESC, dc.chunk_index ASC
            LIMIT ?
            """,
            (like, like, like, limit),
        )
    )


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    names = ["sources", "crawl_jobs", "documents", "document_chunks", "research_runs"]
    return {name: int(conn.execute(f"SELECT COUNT(*) AS n FROM {name}").fetchone()["n"]) for name in names}
