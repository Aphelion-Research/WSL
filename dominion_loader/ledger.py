"""Multi-agent memory ledger writer for dominion_loader (S05).

Schema:
  ledger_entries(id, session_id, kind, payload_json, content_hash UNIQUE, created_at)
  ledger_tags(entry_id, tag)

kind ∈ {decision, assumption, todo_link, ownership, blocked, interface, risk}

This module owns: schema migration, writer API, append idempotency.
Agent 2 owns: query/UX layer.

ASSUMPTION(agent-1): writes go to RAGD's database so Agent 2 can query via RAGD API.
Fallback: if RAGD DB unavailable, writes to ~/.dominion/ledger.db.

INTERFACE(agent-1): Ledger.append()  (Agent 2 builds query layer on top)
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

VALID_KINDS = frozenset({
    "decision", "assumption", "todo_link",
    "ownership", "blocked", "interface", "risk",
})

_LEDGER_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS ledger_entries(
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL DEFAULT '',
    kind         TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL UNIQUE,
    created_at   INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_ledger_kind
    ON ledger_entries(kind);

CREATE INDEX IF NOT EXISTS idx_ledger_session
    ON ledger_entries(session_id);

CREATE TABLE IF NOT EXISTS ledger_tags(
    entry_id INTEGER NOT NULL REFERENCES ledger_entries(id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    PRIMARY KEY(entry_id, tag)
);
"""


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: int
    session_id: str
    kind: str
    payload: dict
    content_hash: str
    created_at: int
    tags: list[str]


class Ledger:
    """Writer for the multi-agent memory ledger.

    Prefers writing to RAGD's database so Agent 2 can query it.
    Falls back to ~/.dominion/ledger.db if RAGD DB is unavailable.
    """

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            ragd_db = Path(os.environ.get("RAGD_DB", str(Path.home() / ".ragd" / "ragd.db")))
            if ragd_db.exists():
                db_path = ragd_db
            else:
                fallback = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
                fallback.mkdir(parents=True, exist_ok=True)
                db_path = fallback / "ledger.db"
        self._db_path = Path(db_path)
        self._conn = sqlite3.connect(str(self._db_path), isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        """Apply additive schema migration for ledger tables."""
        self._conn.executescript(_LEDGER_SCHEMA)

    def append(
        self,
        kind: str,
        payload: dict,
        *,
        session_id: str = "",
        tags: Optional[list[str]] = None,
    ) -> int:
        """Append a ledger entry. Idempotent on (session_id, kind, content_hash).

        Returns the entry id (new or existing).
        Raises ValueError for unknown kind.
        """
        if kind not in VALID_KINDS:
            raise ValueError(f"Unknown ledger kind '{kind}'. Valid: {sorted(VALID_KINDS)}")

        payload_json = json.dumps(payload, sort_keys=True)
        raw = f"{session_id}:{kind}:{payload_json}"
        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        now = int(time.time())

        # Check for existing entry with same hash
        existing = self._conn.execute(
            "SELECT id FROM ledger_entries WHERE content_hash=?",
            (content_hash,),
        ).fetchone()
        if existing:
            return int(existing[0])

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO ledger_entries(session_id, kind, payload_json, content_hash, created_at)
                VALUES(?,?,?,?,?)
                """,
                (session_id, kind, payload_json, content_hash, now),
            )
            entry_id = cursor.lastrowid
            for tag in (tags or []):
                self._conn.execute(
                    "INSERT OR IGNORE INTO ledger_tags(entry_id, tag) VALUES(?,?)",
                    (entry_id, tag),
                )
            self._conn.execute("COMMIT")
            return entry_id  # type: ignore[return-value]
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def query_kind(self, kind: str, *, limit: int = 100) -> list[LedgerEntry]:
        """Retrieve recent entries of a given kind."""
        rows = self._conn.execute(
            "SELECT * FROM ledger_entries WHERE kind=? ORDER BY id DESC LIMIT ?",
            (kind, limit),
        ).fetchall()
        results = []
        for row in rows:
            tags_rows = self._conn.execute(
                "SELECT tag FROM ledger_tags WHERE entry_id=?",
                (row["id"],),
            ).fetchall()
            results.append(LedgerEntry(
                entry_id=row["id"],
                session_id=row["session_id"],
                kind=row["kind"],
                payload=json.loads(row["payload_json"]),
                content_hash=row["content_hash"],
                created_at=row["created_at"],
                tags=[r["tag"] for r in tags_rows],
            ))
        return results

    def stats(self) -> dict[str, int]:
        """Return ledger entry counts by kind."""
        result: dict[str, int] = {"total": 0}
        for row in self._conn.execute(
            "SELECT kind, COUNT(*) AS n FROM ledger_entries GROUP BY kind"
        ):
            result[row["kind"]] = row["n"]
            result["total"] += row["n"]
        return result

    def close(self) -> None:
        self._conn.close()
