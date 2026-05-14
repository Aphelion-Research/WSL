"""SQLite WAL store for Dominion Agent OS.

Each process/test creates its own AgentStore instance.
No global connection singleton.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional

_DEFAULT_HOME = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
_DEFAULT_DB = _DEFAULT_HOME / "agent_os.db"


class AgentStore:
    """SQLite WAL-backed store for Agent OS tables.

    Usage:
        store = AgentStore()          # default ~/.dominion/agent_os.db
        store = AgentStore("/tmp/x.db")  # custom path
        with AgentStore() as s: ...
    """

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        path = Path(db_path) if db_path else _DEFAULT_DB
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = path
        self._conn = sqlite3.connect(
            str(path),
            isolation_level=None,   # autocommit; use explicit BEGIN where needed
            check_same_thread=False,
        )
        self._conn.row_factory = sqlite3.Row
        from dominion_agent.migrations import apply_migrations
        apply_migrations(self._conn)

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    @property
    def db_path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self) -> "AgentStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
