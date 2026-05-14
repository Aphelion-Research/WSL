"""Tests for AgentStore and migrations."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from dominion_agent.store import AgentStore
from dominion_agent.migrations import apply_migrations


def _tmp_store() -> AgentStore:
    """Create an in-memory AgentStore for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    return AgentStore(db_path=path)


# ---------------------------------------------------------------------------
# DB Init
# ---------------------------------------------------------------------------

def test_store_creates_db_file(tmp_path):
    db_path = tmp_path / "test.db"
    store = AgentStore(db_path=str(db_path))
    assert db_path.exists()
    store.close()


def test_store_context_manager(tmp_path):
    db_path = tmp_path / "ctx.db"
    with AgentStore(db_path=str(db_path)) as store:
        assert store.conn is not None


def test_store_conn_is_row_factory(tmp_path):
    db_path = tmp_path / "row.db"
    store = AgentStore(db_path=str(db_path))
    row = store.conn.execute("SELECT 1 AS val").fetchone()
    assert row["val"] == 1
    store.close()


# ---------------------------------------------------------------------------
# Migrations idempotent
# ---------------------------------------------------------------------------

def test_migrations_idempotent(tmp_path):
    db_path = tmp_path / "mig.db"
    store1 = AgentStore(db_path=str(db_path))
    store1.close()
    # Re-opening must not raise
    store2 = AgentStore(db_path=str(db_path))
    row = store2.conn.execute(
        "SELECT COUNT(*) AS n FROM agent_os_migrations"
    ).fetchone()
    assert row["n"] >= 1  # at least migration 1 applied
    store2.close()


def test_all_tables_created(tmp_path):
    db_path = tmp_path / "all_tables.db"
    store = AgentStore(db_path=str(db_path))
    tables_row = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = {r["name"] for r in tables_row}
    expected = {
        "agent_os_migrations",
        "agent_sessions_v2",
        "agent_tasks",
        "agent_claims",
        "agent_file_locks",
        "agent_file_touches",
        "agent_reviews",
        "agent_prompt_compilations",
        "agent_complexity_snapshots",
        "agent_os_events",
    }
    assert expected.issubset(table_names), (
        f"Missing tables: {expected - table_names}"
    )
    store.close()


# ---------------------------------------------------------------------------
# JSON rejection (non-JSON payload should raise json.JSONDecodeError in layer above)
# ---------------------------------------------------------------------------

def test_store_does_not_accept_non_json_in_sessions(tmp_path):
    """AgentStore itself does not validate JSON — that's the layer above."""
    db_path = tmp_path / "nojson.db"
    store = AgentStore(db_path=str(db_path))
    # Direct insert of bad JSON is technically allowed at the SQLite level
    store.conn.execute(
        "INSERT INTO agent_sessions_v2(session_id, agent_name, role, started_at, metadata_json) "
        "VALUES('test_sess', 'agent', 'unknown', 1000, 'NOT JSON')"
    )
    row = store.conn.execute(
        "SELECT metadata_json FROM agent_sessions_v2 WHERE session_id='test_sess'"
    ).fetchone()
    assert row["metadata_json"] == "NOT JSON"
    store.close()
