"""Tests for file lock acquire/release and conflict matrix."""
from __future__ import annotations

import time

import pytest

from dominion_agent.locks import acquire_lock, release_lock, list_locks, stale_locks
from dominion_agent.sessions import start_session
from dominion_agent.store import AgentStore


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "locks.db"))


def _sess(store) -> str:
    s = start_session("agent-1", "test", store=store)
    return s.session_id


# ---------------------------------------------------------------------------
# Basic acquire / release
# ---------------------------------------------------------------------------

def test_acquire_write_lock(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    result = acquire_lock("src/foo.py", sess, mode="write", store=store)
    assert result.acquired is True
    assert result.lock_id.startswith("lock_")


def test_release_lock(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/foo.py", sess, mode="write", store=store)
    release_lock("src/foo.py", sess, store=store)
    locks = list_locks(active_only=True, store=store)
    assert not any(l.filepath == "src/foo.py" for l in locks)


def test_acquire_read_lock(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    result = acquire_lock("src/bar.py", sess, mode="read", store=store)
    assert result.acquired is True


# ---------------------------------------------------------------------------
# Conflict matrix
# ---------------------------------------------------------------------------

def test_write_write_conflict(tmp_path):
    store = _store(tmp_path)
    sess1_row = start_session("agent-1", "test", store=store)
    sess2_row = start_session("agent-2", "test", store=store)
    acquire_lock("src/conflict.py", sess1_row.session_id, mode="write", store=store)
    result = acquire_lock("src/conflict.py", sess2_row.session_id, mode="write", store=store)
    assert result.acquired is False
    assert result.conflict_reason != ""


def test_read_read_no_conflict(tmp_path):
    store = _store(tmp_path)
    sess1 = start_session("agent-1", "test", store=store).session_id
    sess2 = start_session("agent-2", "test", store=store).session_id
    acquire_lock("src/shared.py", sess1, mode="read", store=store)
    result = acquire_lock("src/shared.py", sess2, mode="read", store=store)
    assert result.acquired is True


def test_exclusive_blocks_all(tmp_path):
    store = _store(tmp_path)
    sess1 = start_session("agent-1", "test", store=store).session_id
    sess2 = start_session("agent-2", "test", store=store).session_id
    acquire_lock("src/exc.py", sess1, mode="exclusive", store=store)
    result = acquire_lock("src/exc.py", sess2, mode="read", store=store)
    assert result.acquired is False


def test_review_write_conflict(tmp_path):
    store = _store(tmp_path)
    sess1 = start_session("agent-1", "test", store=store).session_id
    sess2 = start_session("agent-2", "test", store=store).session_id
    acquire_lock("src/rev.py", sess1, mode="review", store=store)
    result = acquire_lock("src/rev.py", sess2, mode="write", store=store)
    assert result.acquired is False


def test_secret_path_blocked(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    with pytest.raises(ValueError, match="secret"):
        acquire_lock("secrets/mt5.env", sess, mode="read", store=store)


# ---------------------------------------------------------------------------
# Force release
# ---------------------------------------------------------------------------

def test_force_release(tmp_path):
    store = _store(tmp_path)
    sess1 = start_session("agent-1", "test", store=store).session_id
    sess2 = start_session("agent-2", "test", store=store).session_id
    acquire_lock("src/forced.py", sess1, mode="write", store=store)
    release_lock("src/forced.py", sess2, force=True, store=store)
    locks = list_locks(active_only=True, store=store)
    assert not any(l.filepath == "src/forced.py" for l in locks)


# ---------------------------------------------------------------------------
# Stale locks
# ---------------------------------------------------------------------------

def test_stale_locks_detected(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/stale.py", sess, mode="write", store=store)
    # Backdate the lock
    store.conn.execute(
        "UPDATE agent_file_locks SET locked_at=? WHERE filepath='src/stale.py'",
        (int(time.time()) - 3600,),
    )
    stale = stale_locks(stale_minutes=30, store=store)
    assert any(l.filepath == "src/stale.py" for l in stale)


# ---------------------------------------------------------------------------
# list_locks
# ---------------------------------------------------------------------------

def test_list_locks_active_only(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/a.py", sess, mode="write", store=store)
    release_lock("src/a.py", sess, store=store)
    active = list_locks(active_only=True, store=store)
    assert not any(l.filepath == "src/a.py" for l in active)
