"""Agent session lifecycle for Dominion Agent OS."""
from __future__ import annotations

import json
import subprocess
import time
import uuid
from typing import Optional

from dominion_agent.store import AgentStore
from dominion_agent.types import Session, STALE_THRESHOLD_SECONDS
from dominion_agent.validators import require_enum, require_nonempty, validate_role, validate_session_status, VALID_SESSION_STATUSES, VALID_ROLES


def _new_session_id() -> str:
    return "sess_" + uuid.uuid4().hex[:12]


def _git_branch() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False
        )
        return result.stdout.strip() or ""
    except Exception:
        return ""


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False
        )
        return result.stdout.strip() or ""
    except Exception:
        return ""


def _row_to_session(row: object) -> Session:
    meta_raw = row["metadata_json"] or "{}"
    try:
        meta = json.loads(meta_raw)
    except Exception:
        meta = {}
    return Session(
        session_id=row["session_id"],
        agent_name=row["agent_name"],
        role=row["role"],
        status=row["status"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        last_heartbeat=row["last_heartbeat"],
        git_branch=row["git_branch"] or "",
        git_commit_start=row["git_commit_start"] or "",
        git_commit_end=row["git_commit_end"] or "",
        parent_session_id=row["parent_session_id"] or "",
        metadata=meta,
    )


def start_session(
    agent_name: str,
    role: str,
    metadata: Optional[dict] = None,
    *,
    store: Optional[AgentStore] = None,
    parent_session_id: str = "",
) -> Session:
    """Create a new active agent session."""
    require_nonempty(agent_name, "agent_name")
    if role not in VALID_ROLES:
        raise ValueError(f"invalid role {role!r}. Valid roles: {sorted(VALID_ROLES)}")
    _store = store or AgentStore()
    session_id = _new_session_id()
    now = int(time.time())
    branch = _git_branch()
    commit = _git_commit()
    meta_json = json.dumps(metadata or {})

    _store.conn.execute(
        """INSERT INTO agent_sessions_v2(
               session_id, agent_name, role, status, started_at, last_heartbeat,
               git_branch, git_commit_start, parent_session_id, metadata_json
           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (session_id, agent_name, role, "active", now, now, branch, commit,
         parent_session_id, meta_json),
    )
    row = _store.conn.execute(
        "SELECT * FROM agent_sessions_v2 WHERE session_id=?", (session_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_session(row)


def heartbeat(session_id: str, *, store: Optional[AgentStore] = None) -> None:
    """Update last_heartbeat for a session."""
    _store = store or AgentStore()
    cursor = _store.conn.execute(
        "UPDATE agent_sessions_v2 SET last_heartbeat=? WHERE session_id=?",
        (int(time.time()), session_id),
    )
    if cursor.rowcount == 0:
        if store is None:
            _store.close()
        raise ValueError(f"session not found: {session_id}")
    if store is None:
        _store.close()


def end_session(
    session_id: str,
    status: str,
    summary: str = "",
    *,
    store: Optional[AgentStore] = None,
) -> Session:
    """End a session with a terminal status."""
    require_enum(status, frozenset({"completed", "failed", "abandoned"}), "status")
    _store = store or AgentStore()
    existing = _store.conn.execute(
        "SELECT * FROM agent_sessions_v2 WHERE session_id=?", (session_id,)
    ).fetchone()
    if existing is None:
        if store is None:
            _store.close()
        raise ValueError(f"session not found: {session_id}")
    if existing["status"] not in ("active", "idle"):
        if store is None:
            _store.close()
        raise ValueError(f"session not endable from status {existing['status']!r}: {session_id}")
    now = int(time.time())
    commit = _git_commit()
    _store.conn.execute(
        """UPDATE agent_sessions_v2
              SET status=?, ended_at=?, git_commit_end=?,
                  metadata_json=json_patch(metadata_json, ?)
           WHERE session_id=?""",
        (status, now, commit, json.dumps({"summary": summary}), session_id),
    )
    row = _store.conn.execute(
        "SELECT * FROM agent_sessions_v2 WHERE session_id=?", (session_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"session not found: {session_id}")
    if store is None:
        _store.close()
    return _row_to_session(row)


def get_session(session_id: str, *, store: Optional[AgentStore] = None) -> Optional[Session]:
    """Fetch a session by ID. Returns None if not found."""
    _store = store or AgentStore()
    row = _store.conn.execute(
        "SELECT * FROM agent_sessions_v2 WHERE session_id=?", (session_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_session(row) if row else None


def list_sessions(
    active_only: bool = False,
    stale_only: bool = False,
    stale_minutes: int = 30,
    *,
    store: Optional[AgentStore] = None,
) -> list[Session]:
    """List sessions with optional filters."""
    _store = store or AgentStore()
    if active_only:
        rows = _store.conn.execute(
            "SELECT * FROM agent_sessions_v2 WHERE status='active' ORDER BY started_at DESC"
        ).fetchall()
    else:
        rows = _store.conn.execute(
            "SELECT * FROM agent_sessions_v2 ORDER BY started_at DESC LIMIT 200"
        ).fetchall()
    if store is None:
        _store.close()

    sessions = [_row_to_session(r) for r in rows]
    if stale_only:
        threshold = stale_minutes * 60
        sessions = [s for s in sessions if s.is_stale(threshold)]
    return sessions


def abandon_session(
    session_id: str,
    reason: str = "",
    *,
    store: Optional[AgentStore] = None,
) -> Session:
    """Force-abandon a session (for stale/orphaned sessions)."""
    _store = store or AgentStore()
    session_row = _store.conn.execute(
        "SELECT status FROM agent_sessions_v2 WHERE session_id=?", (session_id,)
    ).fetchone()
    if session_row is None:
        if store is None:
            _store.close()
        raise ValueError(f"session not found: {session_id}")
    if session_row["status"] not in ("active", "idle"):
        if store is None:
            _store.close()
        raise ValueError(
            f"session {session_id!r} is already in terminal state {existing['status']!r}; "
            "cannot abandon"
        )
    now = int(time.time())
    _store.conn.execute(
        """UPDATE agent_sessions_v2
              SET status='abandoned', ended_at=?,
                  metadata_json=json_patch(metadata_json, ?)
           WHERE session_id=?""",
        (now, json.dumps({"abandon_reason": reason}), session_id),
    )
    row = _store.conn.execute(
        "SELECT * FROM agent_sessions_v2 WHERE session_id=?", (session_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_session(row)
