"""Tests for file lock acquire/release and conflict matrix."""
from __future__ import annotations

import time

import pytest

from dominion_agent.locks import acquire_lock, release_lock, list_locks, stale_locks, reap_expired_locks
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


# ---------------------------------------------------------------------------
# reap_expired_locks (Phase 4)
# ---------------------------------------------------------------------------

def test_reap_expired_locks_marks_reaped(tmp_path):
    """Locks whose expires_at is in the past are reaped."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/exp.py", sess, expires_in_seconds=60, store=store)
    # Backdate expires_at so it's already expired
    store.conn.execute(
        "UPDATE agent_file_locks SET expires_at=? WHERE filepath='src/exp.py'",
        (int(time.time()) - 10,),
    )
    n = reap_expired_locks(store=store)
    assert n == 1
    active = list_locks(active_only=True, store=store)
    assert not any(l.filepath == "src/exp.py" for l in active)


def test_reap_expired_locks_leaves_valid_locks(tmp_path):
    """Locks with future expires_at are NOT reaped."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/valid.py", sess, expires_in_seconds=3600, store=store)
    n = reap_expired_locks(store=store)
    assert n == 0
    active = list_locks(active_only=True, store=store)
    assert any(l.filepath == "src/valid.py" for l in active)


def test_reap_expired_locks_leaves_no_expiry_locks(tmp_path):
    """Locks without expires_at (perpetual) are NOT reaped."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/forever.py", sess, store=store)  # no expires_in_seconds
    n = reap_expired_locks(store=store)
    assert n == 0


def test_expired_lock_does_not_block_acquisition(tmp_path):
    """An expired active lock must not prevent a new acquisition."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/blocked.py", sess, expires_in_seconds=60, store=store)
    # Expire the lock manually
    store.conn.execute(
        "UPDATE agent_file_locks SET expires_at=? WHERE filepath='src/blocked.py'",
        (int(time.time()) - 10,),
    )
    # New session should be able to acquire
    sess2 = _sess(store)
    result = acquire_lock("src/blocked.py", sess2, mode="write", store=store)
    assert result.acquired is True, result.conflict_reason


def test_reap_returns_count_of_reaped(tmp_path):
    """reap_expired_locks returns correct count when multiple locks expire."""
    store = _store(tmp_path)
    sess = _sess(store)
    for i in range(3):
        acquire_lock(f"src/file{i}.py", sess, expires_in_seconds=60, mode="read", store=store)
    store.conn.execute(
        "UPDATE agent_file_locks SET expires_at=? WHERE status='active'",
        (int(time.time()) - 10,),
    )
    n = reap_expired_locks(store=store)
    assert n == 3


# ---------------------------------------------------------------------------
# Path-overlap detection (parent / child conflicts)
# ---------------------------------------------------------------------------

def test_parent_lock_blocks_child_write(tmp_path):
    """Write lock on parent directory blocks write on child file."""
    store = _store(tmp_path)
    sess = _sess(store)
    r = acquire_lock("src/", sess, mode="write", store=store)
    assert r.acquired

    sess2 = _sess(store)
    r2 = acquire_lock("src/a.py", sess2, mode="write", store=store)
    assert r2.acquired is False
    assert "src/" in r2.conflict_reason


def test_child_lock_blocks_parent_write(tmp_path):
    """Write lock on child file blocks write lock on parent directory."""
    store = _store(tmp_path)
    sess = _sess(store)
    r = acquire_lock("src/a.py", sess, mode="write", store=store)
    assert r.acquired

    sess2 = _sess(store)
    r2 = acquire_lock("src/", sess2, mode="write", store=store)
    assert r2.acquired is False
    assert "src/a.py" in r2.conflict_reason


def test_sibling_paths_do_not_conflict(tmp_path):
    """Write lock on src/a.py does NOT block write on src/b.py (siblings)."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/a.py", sess, mode="write", store=store)

    sess2 = _sess(store)
    r = acquire_lock("src/b.py", sess2, mode="write", store=store)
    assert r.acquired is True


def test_deep_parent_blocks_deep_child(tmp_path):
    """Lock on pkg/ blocks pkg/sub/module.py (nested child)."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("pkg/", sess, mode="write", store=store)

    sess2 = _sess(store)
    r = acquire_lock("pkg/sub/module.py", sess2, mode="write", store=store)
    assert r.acquired is False


def test_read_parent_does_not_block_read_child(tmp_path):
    """Read lock on parent does not block read lock on child (compatible modes)."""
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/", sess, mode="read", store=store)

    sess2 = _sess(store)
    r = acquire_lock("src/a.py", sess2, mode="read", store=store)
    assert r.acquired is True


def test_idempotent_exact_path_not_affected_by_overlap_check(tmp_path):
    """Same session, same mode, exact path is still idempotent after overlap fix."""
    store = _store(tmp_path)
    sess = _sess(store)
    r1 = acquire_lock("src/a.py", sess, mode="write", store=store)
    r2 = acquire_lock("src/a.py", sess, mode="write", store=store)
    assert r1.acquired and r2.acquired
    assert r1.lock_id == r2.lock_id
