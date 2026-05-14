"""Tests for session lifecycle."""
from __future__ import annotations

import tempfile
import time

import pytest

from dominion_agent.sessions import (
    start_session,
    heartbeat,
    end_session,
    get_session,
    list_sessions,
    abandon_session,
)
from dominion_agent.store import AgentStore
from dominion_agent.types import STALE_THRESHOLD_SECONDS


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "sessions.db"))


# ---------------------------------------------------------------------------
# start_session
# ---------------------------------------------------------------------------

def test_start_session_returns_session(tmp_path):
    s = start_session("agent-1", "orchestrator", store=_store(tmp_path))
    assert s.agent_name == "agent-1"
    assert s.role == "orchestrator"
    assert s.status == "active"
    assert s.session_id.startswith("sess_")


def test_start_session_invalid_role(tmp_path):
    with pytest.raises(ValueError, match="role"):
        start_session("agent-1", "invalid_role", store=_store(tmp_path))


def test_start_session_invalid_name(tmp_path):
    with pytest.raises(ValueError):
        start_session("", "orchestrator", store=_store(tmp_path))


def test_start_session_with_metadata(tmp_path):
    s = start_session("agent-1", "test", metadata={"env": "test"}, store=_store(tmp_path))
    assert s.metadata.get("env") == "test"


def test_start_session_persists(tmp_path):
    store = _store(tmp_path)
    s = start_session("agent-1", "orchestrator", store=store)
    fetched = get_session(s.session_id, store=store)
    assert fetched is not None
    assert fetched.session_id == s.session_id


# ---------------------------------------------------------------------------
# heartbeat
# ---------------------------------------------------------------------------

def test_heartbeat_updates_timestamp(tmp_path):
    store = _store(tmp_path)
    s = start_session("agent-1", "test", store=store)
    time.sleep(0.01)
    heartbeat(s.session_id, store=store)
    fetched = get_session(s.session_id, store=store)
    assert fetched.last_heartbeat >= s.started_at


def test_heartbeat_invalid_session(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        heartbeat("sess_nonexistent", store=_store(tmp_path))


# ---------------------------------------------------------------------------
# end_session
# ---------------------------------------------------------------------------

def test_end_session_completed(tmp_path):
    store = _store(tmp_path)
    s = start_session("agent-1", "test", store=store)
    ended = end_session(s.session_id, status="completed", summary="done", store=store)
    assert ended.status == "completed"
    assert ended.ended_at is not None


def test_end_session_already_ended(tmp_path):
    store = _store(tmp_path)
    s = start_session("agent-1", "test", store=store)
    end_session(s.session_id, status="completed", store=store)
    with pytest.raises(ValueError, match="not active"):
        end_session(s.session_id, status="completed", store=store)


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

def test_list_sessions_active_only(tmp_path):
    store = _store(tmp_path)
    s1 = start_session("agent-1", "test", store=store)
    s2 = start_session("agent-2", "test", store=store)
    end_session(s1.session_id, status="completed", store=store)
    active = list_sessions(active_only=True, store=store)
    ids = [s.session_id for s in active]
    assert s2.session_id in ids
    assert s1.session_id not in ids


def test_list_sessions_stale(tmp_path):
    store = _store(tmp_path)
    s = start_session("agent-stale", "test", store=store)
    # Manually backdate heartbeat
    store.conn.execute(
        "UPDATE agent_sessions_v2 SET last_heartbeat=? WHERE session_id=?",
        (int(time.time()) - STALE_THRESHOLD_SECONDS - 100, s.session_id),
    )
    stale = list_sessions(stale_only=True, store=store)
    assert any(x.session_id == s.session_id for x in stale)


# ---------------------------------------------------------------------------
# abandon_session
# ---------------------------------------------------------------------------

def test_abandon_session(tmp_path):
    store = _store(tmp_path)
    s = start_session("agent-1", "test", store=store)
    abandoned = abandon_session(s.session_id, reason="test abandon", store=store)
    assert abandoned.status == "abandoned"
