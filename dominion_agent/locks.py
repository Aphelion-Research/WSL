"""File lock management for Dominion Agent OS.

Write lock: conflicts with read + write + review + exclusive
Read lock: conflicts with write + exclusive
Review lock: conflicts with write + exclusive
Exclusive lock: conflicts with everything
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from dominion_agent.safety import is_secret_path
from dominion_agent.store import AgentStore
from dominion_agent.types import FileLock, LockResult, VALID_LOCK_MODES
from dominion_agent.validators import require_enum


# Lock conflict matrix: (existing_mode, requested_mode) -> conflict
_CONFLICTS: dict[tuple[str, str], bool] = {
    ("read",      "read"):      False,
    ("read",      "write"):     True,
    ("read",      "review"):    False,
    ("read",      "exclusive"): True,
    ("write",     "read"):      True,
    ("write",     "write"):     True,
    ("write",     "review"):    True,
    ("write",     "exclusive"): True,
    ("review",    "read"):      False,
    ("review",    "write"):     True,
    ("review",    "review"):    False,
    ("review",    "exclusive"): True,
    ("exclusive", "read"):      True,
    ("exclusive", "write"):     True,
    ("exclusive", "review"):    True,
    ("exclusive", "exclusive"): True,
}


def _conflicts_with(existing_mode: str, requested_mode: str) -> bool:
    return _CONFLICTS.get((existing_mode, requested_mode), True)


def _new_lock_id() -> str:
    return "lock_" + uuid.uuid4().hex[:12]


def _row_to_lock(row: object) -> FileLock:
    return FileLock(
        lock_id=row["lock_id"],
        filepath=row["filepath"],
        session_id=row["session_id"],
        task_id=row["task_id"] or "",
        mode=row["mode"],
        status=row["status"],
        locked_at=row["locked_at"],
        released_at=row["released_at"],
        expires_at=row["expires_at"],
        note=row["note"] or "",
    )


def acquire_lock(
    filepath: str,
    session_id: str,
    task_id: str = "",
    mode: str = "write",
    *,
    expires_in_seconds: Optional[int] = None,
    note: str = "",
    store: Optional[AgentStore] = None,
) -> LockResult:
    """Attempt to acquire a file lock.

    Returns LockResult with acquired=True on success.
    Returns LockResult with acquired=False and conflict_reason on failure.

    Secret paths cannot be locked for write/exclusive access.
    """
    require_enum(mode, VALID_LOCK_MODES, "mode")

    # Safety: block any lock on secrets paths
    if is_secret_path(filepath):
        raise ValueError(
            f"SECURITY: cannot acquire lock on secret path {filepath!r}. "
            "Secrets paths must never be in task scope."
        )

    _store = store or AgentStore()
    lock_id = _new_lock_id()
    now = int(time.time())
    expires_at = now + expires_in_seconds if expires_in_seconds else None

    # BEGIN IMMEDIATE serializes concurrent lockers: only one can proceed past
    # this point at a time, preventing the SELECT-then-INSERT race condition.
    _store.conn.execute("BEGIN IMMEDIATE")
    try:
        # Check for conflicting active locks (skip expired ones).
        # Also detect parent/child path overlaps:
        #   - existing lock on "src/" blocks new lock on "src/a.py"   (? LIKE filepath||'/%')
        #   - existing lock on "src/a.py" blocks new lock on "src/"   (filepath LIKE ?||'/%')
        # rtrim(x, '/') strips trailing slashes before building the prefix pattern,
        # so "src/" and "src" both produce the pattern "src/%" correctly.
        existing_rows = _store.conn.execute(
            "SELECT lock_id, session_id, mode, filepath FROM agent_file_locks"
            " WHERE status='active'"
            " AND (expires_at IS NULL OR expires_at > ?)"
            " AND (filepath = ?"
            "  OR (? LIKE rtrim(filepath, '/') || '/%')"
            "  OR (filepath LIKE rtrim(?, '/') || '/%'))",
            (now, filepath, filepath, filepath),
        ).fetchall()

        for existing in existing_rows:
            # Same session, same mode, exact path — idempotent re-acquire
            if (
                existing["session_id"] == session_id
                and existing["mode"] == mode
                and existing["filepath"] == filepath
            ):
                _store.conn.execute("COMMIT")
                if store is None:
                    _store.close()
                return LockResult(
                    lock_id=existing["lock_id"],
                    filepath=filepath,
                    session_id=session_id,
                    acquired=True,
                    conflict_reason="",
                )
            if _conflicts_with(existing["mode"], mode):
                _store.conn.execute("ROLLBACK")
                if store is None:
                    _store.close()
                overlap = existing["filepath"]
                reason = (
                    f"path overlap: {overlap!r} already has active {existing['mode']!r} lock "
                    f"by session {existing['session_id']!r}"
                )
                return LockResult(
                    lock_id="",
                    filepath=filepath,
                    session_id=session_id,
                    acquired=False,
                    conflict_reason=reason,
                )

        _store.conn.execute(
            """INSERT INTO agent_file_locks(
                   lock_id, filepath, session_id, task_id, mode, status,
                   locked_at, expires_at, note
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (lock_id, filepath, session_id, task_id, mode, "active",
             now, expires_at, note),
        )
        _store.conn.execute("COMMIT")
    except Exception as exc:
        try:
            _store.conn.execute("ROLLBACK")
        except Exception:
            pass
        if store is None:
            _store.close()
        return LockResult(
            lock_id="",
            filepath=filepath,
            session_id=session_id,
            acquired=False,
            conflict_reason=f"DB error acquiring lock: {exc}",
        )

    if store is None:
        _store.close()
    return LockResult(
        lock_id=lock_id,
        filepath=filepath,
        session_id=session_id,
        acquired=True,
        conflict_reason="",
    )


def release_lock(
    filepath: str,
    session_id: str,
    *,
    store: Optional[AgentStore] = None,
    force: bool = False,
) -> bool:
    """Release an active lock. Returns True if released, False if not found.

    Requires owning session unless force=True.
    """
    _store = store or AgentStore()
    now = int(time.time())

    if force:
        n = _store.conn.execute(
            """UPDATE agent_file_locks
                  SET status='released', released_at=?
               WHERE filepath=? AND status='active'""",
            (now, filepath),
        ).rowcount
    else:
        n = _store.conn.execute(
            """UPDATE agent_file_locks
                  SET status='released', released_at=?
               WHERE filepath=? AND session_id=? AND status='active'""",
            (now, filepath, session_id),
        ).rowcount

    if store is None:
        _store.close()
    return n > 0


def list_locks(
    active_only: bool = True,
    *,
    store: Optional[AgentStore] = None,
) -> list[FileLock]:
    """List all file locks."""
    _store = store or AgentStore()
    if active_only:
        rows = _store.conn.execute(
            "SELECT * FROM agent_file_locks WHERE status='active' ORDER BY locked_at DESC"
        ).fetchall()
    else:
        rows = _store.conn.execute(
            "SELECT * FROM agent_file_locks ORDER BY locked_at DESC LIMIT 500"
        ).fetchall()
    if store is None:
        _store.close()
    return [_row_to_lock(r) for r in rows]


def stale_locks(
    stale_minutes: int = 60,
    *,
    store: Optional[AgentStore] = None,
) -> list[FileLock]:
    """Return active locks older than stale_minutes (for reporting)."""
    _store = store or AgentStore()
    cutoff = int(time.time()) - stale_minutes * 60
    rows = _store.conn.execute(
        "SELECT * FROM agent_file_locks WHERE status='active' AND locked_at < ?",
        (cutoff,),
    ).fetchall()
    if store is None:
        _store.close()
    return [_row_to_lock(r) for r in rows]


def reap_expired_locks(
    *,
    store: Optional[AgentStore] = None,
) -> int:
    """Mark all expired active locks as 'reaped'. Returns count reaped.

    A lock is expired if it has an expires_at value in the past.
    This is separate from stale_locks() which detects by age, not expires_at.
    """
    _store = store or AgentStore()
    now = int(time.time())
    n = _store.conn.execute(
        """UPDATE agent_file_locks
              SET status='reaped', released_at=?
           WHERE status='active'
             AND expires_at IS NOT NULL
             AND expires_at < ?""",
        (now, now),
    ).rowcount
    if store is None:
        _store.close()
    return n
