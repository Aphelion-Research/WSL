"""Task management for Dominion Agent OS."""
from __future__ import annotations

import json
import time
import uuid
from typing import Optional

from dominion_agent.safety import validate_task_payload
from dominion_agent.store import AgentStore
from dominion_agent.types import Task, VALID_TASK_KINDS, VALID_TASK_STATUSES, TASK_TRANSITIONS
from dominion_agent.validators import (
    require_nonempty,
    require_enum,
    require_priority,
    validate_task_transition,
)


def _new_task_id() -> str:
    return "task_" + uuid.uuid4().hex[:12]


def _row_to_task(row: object) -> Task:
    def _j(s: str, default: object) -> object:
        try:
            return json.loads(s or json.dumps(default))
        except Exception:
            return default

    return Task(
        task_id=row["task_id"],
        title=row["title"],
        description=row["description"] or "",
        kind=row["kind"],
        priority=row["priority"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        claimed_by_session=row["claimed_by_session"] or "",
        parent_task_id=row["parent_task_id"] or "",
        scope=_j(row["scope_json"], {}),
        validation=_j(row["validation_json"], {}),
        acceptance=_j(row["acceptance_json"], {}),
        risk=_j(row["risk_json"], {}),
        tags=_j(row["tags_json"], []),
        evidence=_j(row["evidence_json"], {}),
    )


def create_task(
    title: str,
    description: str = "",
    kind: str = "feature",
    priority: int = 5,
    scope: Optional[dict] = None,
    validation: Optional[dict] = None,
    acceptance: Optional[dict] = None,
    risk: Optional[dict] = None,
    tags: Optional[list] = None,
    *,
    store: Optional[AgentStore] = None,
) -> Task:
    """Create a new task. Runs safety validation before DB write."""
    require_nonempty(title, "title")
    require_enum(kind, VALID_TASK_KINDS, "kind")
    require_priority(priority)

    scope_files = (scope or {}).get("files", [])
    safety = validate_task_payload({
        "title": title,
        "description": description,
        "scope_files": scope_files,
    })
    if not safety.ok:
        raise ValueError("Task blocked by safety filter:\n" + "\n".join(safety.violations))

    _store = store or AgentStore()
    task_id = _new_task_id()
    now = int(time.time())

    _store.conn.execute(
        """INSERT INTO agent_tasks(
               task_id, title, description, kind, priority, status,
               created_at, updated_at, scope_json, validation_json,
               acceptance_json, risk_json, tags_json
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            task_id, title.strip(), description, kind, priority, "open",
            now, now,
            json.dumps(scope or {}),
            json.dumps(validation or {}),
            json.dumps(acceptance or {}),
            json.dumps(risk or {}),
            json.dumps(tags or []),
        ),
    )
    row = _store.conn.execute(
        "SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_task(row)


def get_task(task_id: str, *, store: Optional[AgentStore] = None) -> Optional[Task]:
    """Fetch a task by ID. Returns None if not found."""
    _store = store or AgentStore()
    row = _store.conn.execute(
        "SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_task(row) if row else None


def list_tasks(
    status: Optional[str] = None,
    limit: int = 50,
    *,
    store: Optional[AgentStore] = None,
) -> list[Task]:
    """List tasks, optionally filtered by status."""
    _store = store or AgentStore()
    if status:
        require_enum(status, VALID_TASK_STATUSES, "status")
        rows = _store.conn.execute(
            "SELECT * FROM agent_tasks WHERE status=? ORDER BY priority ASC, created_at ASC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = _store.conn.execute(
            "SELECT * FROM agent_tasks ORDER BY priority ASC, created_at ASC LIMIT ?",
            (limit,),
        ).fetchall()
    if store is None:
        _store.close()
    return [_row_to_task(r) for r in rows]


def update_task_status(
    task_id: str,
    new_status: str,
    evidence: Optional[dict] = None,
    *,
    store: Optional[AgentStore] = None,
    force: bool = False,
) -> Task:
    """Update task status, enforcing transition rules.

    Requires evidence when moving to 'done'.
    Use force=True to reopen terminal states.
    """
    require_enum(new_status, VALID_TASK_STATUSES, "status")
    _store = store or AgentStore()
    row = _store.conn.execute(
        "SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if row is None:
        if store is None:
            _store.close()
        raise ValueError(f"task not found: {task_id}")

    task = _row_to_task(row)
    current = task.status

    if not force and not validate_task_transition(current, new_status):
        if store is None:
            _store.close()
        raise ValueError(
            f"invalid transition: {current!r} → {new_status!r}. "
            f"Use force=True to override or --reopen flag."
        )

    # Require evidence to close a task (unless force=True)
    if new_status == "done" and not evidence and not task.evidence and not force:
        if store is None:
            _store.close()
        raise ValueError("evidence required to mark task done. Provide evidence dict.")

    now = int(time.time())
    evidence_json = json.dumps(evidence or task.evidence)

    _store.conn.execute(
        """UPDATE agent_tasks
              SET status=?, updated_at=?, evidence_json=?
           WHERE task_id=?""",
        (new_status, now, evidence_json, task_id),
    )
    row = _store.conn.execute(
        "SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if store is None:
        _store.close()
    return _row_to_task(row)


def update_task_evidence(
    task_id: str,
    evidence: dict,
    *,
    store: Optional[AgentStore] = None,
) -> Task:
    """Attach evidence to a task without changing its status."""
    _store = store or AgentStore()
    now = int(time.time())
    _store.conn.execute(
        "UPDATE agent_tasks SET evidence_json=?, updated_at=? WHERE task_id=?",
        (json.dumps(evidence), now, task_id),
    )
    row = _store.conn.execute(
        "SELECT * FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if row is None:
        if store is None:
            _store.close()
        raise ValueError(f"task not found: {task_id}")
    if store is None:
        _store.close()
    return _row_to_task(row)


def record_touch(
    session_id: str,
    task_id: str,
    filepath: str,
    action: str,
    *,
    store: Optional[AgentStore] = None,
    git_commit: str = "",
    note: str = "",
) -> None:
    """Record a file touch event."""
    _store = store or AgentStore()
    touch_id = "touch_" + uuid.uuid4().hex[:12]
    _store.conn.execute(
        """INSERT INTO agent_file_touches(
               touch_id, session_id, task_id, filepath, action,
               touched_at, git_commit, note
           ) VALUES(?,?,?,?,?,?,?,?)""",
        (touch_id, session_id, task_id, filepath, action,
         int(time.time()), git_commit, note),
    )
    if store is None:
        _store.close()
