"""Conflict oracle for Dominion Agent OS.

Predicts conflicts before an agent edits files.
Signals: active locks, task scope overlap, git dirty files, shared interface files,
migration collision, secret path requests.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from dominion_agent.safety import is_secret_path
from dominion_agent.store import AgentStore
from dominion_agent.types import ConflictItem, ConflictReport

# Files that are shared interfaces — touching them has higher risk
_SHARED_INTERFACE_FILES: frozenset[str] = frozenset({
    "dominion_loader/api.py",
    "dominion_loader/scan.py",
    "dominion_agent/api.py",
    "dominion_ai/api.py",
    "scripts/dominion_cli.py",
    "ragd/include/ragd/api.h",
    "ragd/src/http_api.cpp",
    "AGENTS.md",
    "docs/agents/SHARED_INTERFACE_CONTRACT.md",
    "pytest.ini",
})

# Migration path patterns — two migrations = critical conflict
_MIGRATION_PATTERNS: list[str] = [
    "ragd/sql/migrations/",
    "dominion_agent/migrations.py",
]

# Severity ranking for risk aggregation
_SEVERITY_RANK: dict[str, int] = {
    "info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4
}


def _get_dirty_files(repo_root: str = ".") -> set[str]:
    """Return set of files modified in git working tree."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5, check=False,
            cwd=repo_root,
        )
        dirty: set[str] = set()
        for line in result.stdout.splitlines():
            if len(line) >= 3:
                dirty.add(line[3:].strip())
        return dirty
    except Exception:
        return set()


def _get_task_scope_files(task_id: str, store: AgentStore) -> list[str]:
    """Get file list from a task's scope_json."""
    row = store.conn.execute(
        "SELECT scope_json FROM agent_tasks WHERE task_id=?", (task_id,)
    ).fetchone()
    if not row:
        return []
    try:
        scope = json.loads(row["scope_json"] or "{}")
        return scope.get("files", [])
    except Exception:
        return []


def check_conflicts(
    task_id: Optional[str] = None,
    files: Optional[list[str]] = None,
    *,
    store: Optional[AgentStore] = None,
    repo_root: str = ".",
) -> ConflictReport:
    """Check for conflicts given a task ID and/or explicit file list.

    Checks:
    1. Active write/exclusive locks on target files
    2. Overlapping task scope (two open tasks include same file)
    3. Dirty worktree files (git modified before claim)
    4. Shared interface files (elevated risk)
    5. Migration file collision
    6. Secret path requests
    """
    _store = store or AgentStore()
    conflicts: list[ConflictItem] = []

    # Resolve file list from task scope + explicit files
    target_files: set[str] = set(files or [])
    if task_id:
        target_files.update(_get_task_scope_files(task_id, _store))

    dirty = _get_dirty_files(repo_root)

    for filepath in sorted(target_files):
        # 1. Secret path check
        if is_secret_path(filepath):
            conflicts.append(ConflictItem(
                type="secret_path_request",
                filepath=filepath,
                owner_session="",
                severity="critical",
                remedy="Remove secrets path from task scope. Use synthetic fixture tests instead.",
                details=f"Secrets path {filepath!r} must never be in task scope.",
            ))
            continue

        # 2. Active lock check
        lock_rows = _store.conn.execute(
            "SELECT lock_id, session_id, mode FROM agent_file_locks "
            "WHERE filepath=? AND status='active'",
            (filepath,),
        ).fetchall()
        for lock_row in lock_rows:
            if lock_row["mode"] in ("write", "exclusive"):
                conflicts.append(ConflictItem(
                    type="active_write_lock",
                    filepath=filepath,
                    owner_session=lock_row["session_id"],
                    severity="high",
                    remedy="Wait for lock release, request handoff, or split task to avoid overlap.",
                    details=f"Active {lock_row['mode']!r} lock by {lock_row['session_id']!r}",
                ))

        # 3. Dirty worktree
        if filepath in dirty:
            conflicts.append(ConflictItem(
                type="dirty_worktree_file",
                filepath=filepath,
                owner_session="",
                severity="high",
                remedy="Commit or stash changes before starting new task on this file.",
                details=f"File {filepath!r} has uncommitted changes in working tree.",
            ))

        # 4. Shared interface file
        rel = filepath.lstrip("/")
        if rel in _SHARED_INTERFACE_FILES:
            conflicts.append(ConflictItem(
                type="shared_interface_file",
                filepath=filepath,
                owner_session="",
                severity="high",
                remedy="Coordinate with all consumers before editing this shared interface file.",
                details=f"{filepath!r} is a shared interface used by multiple packages.",
            ))

        # 5. Overlapping task scope (another open/claimed task includes this file)
        if task_id:
            overlap_rows = _store.conn.execute(
                """SELECT task_id, title FROM agent_tasks
                   WHERE status IN ('open','claimed','in_progress')
                     AND task_id != ?
                     AND scope_json LIKE ?""",
                (task_id, f"%{filepath}%"),
            ).fetchall()
            for ov in overlap_rows:
                conflicts.append(ConflictItem(
                    type="overlapping_task_scope",
                    filepath=filepath,
                    owner_session=ov["task_id"],
                    severity="medium",
                    remedy="Coordinate with the other task or split scope to avoid merge conflicts.",
                    details=f"Task {ov['task_id']!r} ({ov['title']!r}) also includes this file.",
                ))

    # 6. Migration collision: check if multiple tasks include migration paths
    migration_tasks: list[str] = []
    for mpat in _MIGRATION_PATTERNS:
        for f in target_files:
            if mpat in f:
                migration_tasks.append(f)
    if len(migration_tasks) >= 2:
        conflicts.append(ConflictItem(
            type="migration_collision",
            filepath=", ".join(migration_tasks[:2]),
            owner_session="",
            severity="critical",
            remedy="Only one migration should be added per task. Split into separate tasks.",
            details="Multiple migration files in same task scope creates schema conflict risk.",
        ))

    if store is None:
        _store.close()

    # Aggregate risk
    max_severity = max(
        (_SEVERITY_RANK.get(c.severity, 0) for c in conflicts),
        default=0,
    )
    severity_names = ["low", "medium", "high", "critical"]
    risk = severity_names[min(max_severity - 1, 3)] if max_severity > 0 else "low"

    if max_severity == 0:
        status = "pass"
        action = "proceed"
    elif max_severity == 1:
        status = "warn"
        action = "proceed"
    elif max_severity == 2:
        status = "warn"
        action = "split_task"
    elif max_severity == 3:
        status = "fail"
        action = "wait"
    else:
        status = "fail"
        action = "block"

    return ConflictReport(
        status=status,
        risk=risk,
        conflicts=conflicts,
        recommended_action=action,
    )
