"""Claim management for Dominion Agent OS.

One active claim per task by default.
Only active sessions can claim.
"""
from __future__ import annotations

import time
import uuid
from typing import Optional

from dominion_agent.store import AgentStore
from dominion_agent.types import ClaimResult


def _new_claim_id() -> str:
    return "claim_" + uuid.uuid4().hex[:12]


def claim_task(
    task_id: str,
    session_id: str,
    *,
    collaborative: bool = False,
    store: Optional[AgentStore] = None,
) -> ClaimResult:
    """Claim a task for a session.

    Raises ValueError if:
    - session is not active
    - task already has an active claim (unless collaborative=True)
    - task is not in a claimable state
    """
    _store = store or AgentStore()

    # Verify session is active
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
            f"session {session_id!r} has status {session_row['status']!r}; "
            "only active/idle sessions can claim tasks"
        )

    # Verify task exists and is claimable
    task_row = _store.conn.execute(
        "SELECT status FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if task_row is None:
        if store is None:
            _store.close()
        raise ValueError(f"task not found: {task_id}")
    if task_row["status"] not in ("open", "claimed"):
        if store is None:
            _store.close()
        raise ValueError(
            f"task {task_id!r} has status {task_row['status']!r}; "
            "only open/claimed tasks can be claimed"
        )

    # Check for existing active claim
    existing = _store.conn.execute(
        "SELECT claim_id, session_id FROM agent_claims WHERE task_id=? AND status='active'",
        (task_id,),
    ).fetchone()
    if existing and not collaborative:
        if existing["session_id"] == session_id:
            # Already claimed by same session — idempotent
            row = _store.conn.execute(
                "SELECT * FROM agent_claims WHERE claim_id=?", (existing["claim_id"],)
            ).fetchone()
            if store is None:
                _store.close()
            return _row_to_claim(row)
        if store is None:
            _store.close()
        raise ValueError(
            f"task {task_id!r} already claimed by session {existing['session_id']!r}. "
            "Use --collaborative to allow multiple claimants."
        )

    claim_id = _new_claim_id()
    now = int(time.time())

    _store.conn.execute(
        """INSERT OR IGNORE INTO agent_claims(
               claim_id, task_id, session_id, status, claimed_at
           ) VALUES(?,?,?,?,?)""",
        (claim_id, task_id, session_id, "active", now),
    )

    # Update task status
    _store.conn.execute(
        "UPDATE agent_tasks SET status='claimed', claimed_by_session=?, updated_at=? WHERE task_id=?",
        (session_id, now, task_id),
    )

    row = _store.conn.execute(
        "SELECT * FROM agent_claims WHERE claim_id=?", (claim_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_claim(row)


def release_task(
    task_id: str,
    session_id: str,
    note: str = "",
    *,
    store: Optional[AgentStore] = None,
) -> None:
    """Release a task claim. Task reverts to 'open'."""
    _store = store or AgentStore()
    now = int(time.time())

    _store.conn.execute(
        """UPDATE agent_claims
              SET status='released', released_at=?, note=?
           WHERE task_id=? AND session_id=? AND status='active'""",
        (now, note, task_id, session_id),
    )

    # Check if any remaining active claims
    remaining = _store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_claims WHERE task_id=? AND status='active'",
        (task_id,),
    ).fetchone()
    if remaining["n"] == 0:
        _store.conn.execute(
            "UPDATE agent_tasks SET status='open', claimed_by_session='', updated_at=? WHERE task_id=?",
            (now, task_id),
        )
    if store is None:
        _store.close()


def list_claims(
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    active_only: bool = True,
    *,
    store: Optional[AgentStore] = None,
) -> list[ClaimResult]:
    """List claims, optionally filtered by task or session."""
    _store = store or AgentStore()
    conditions: list[str] = []
    params: list = []
    if task_id:
        conditions.append("task_id=?")
        params.append(task_id)
    if session_id:
        conditions.append("session_id=?")
        params.append(session_id)
    if active_only:
        conditions.append("status='active'")
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    rows = _store.conn.execute(
        f"SELECT * FROM agent_claims{where} ORDER BY claimed_at DESC",
        params,
    ).fetchall()
    if store is None:
        _store.close()
    return [_row_to_claim(r) for r in rows]


def _row_to_claim(row: object) -> ClaimResult:
    return ClaimResult(
        claim_id=row["claim_id"],
        task_id=row["task_id"],
        session_id=row["session_id"],
        status=row["status"],
        claimed_at=row["claimed_at"],
        released_at=row["released_at"],
        note=row["note"] or "",
    )
