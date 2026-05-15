"""Public API facade for Dominion Agent OS.

All public entry points are here. Internal modules are implementation details.
"""
from __future__ import annotations

from typing import Optional

from dominion_agent.adversary import run_adversarial_review
from dominion_agent.architecture import refresh_architecture, show_architecture
from dominion_agent.claims import claim_task, release_task, list_claims
from dominion_agent.complexity import complexity_report, all_packages_report, COMPLEXITY_BUDGETS
from dominion_agent.conflicts import check_conflicts
from dominion_agent.impact import analyze_impact
from dominion_agent.locks import acquire_lock, release_lock, list_locks, stale_locks, reap_expired_locks
from dominion_agent.prompt_compiler import compile_prompt
from dominion_agent.sessions import (
    start_session,
    heartbeat,
    end_session,
    get_session,
    list_sessions,
    abandon_session,
)
from dominion_agent.store import AgentStore
from dominion_agent.tasks import (
    create_task,
    get_task,
    list_tasks,
    update_task_status,
    update_task_evidence,
    record_touch,
)
from dominion_agent.types import (
    ClaimResult,
    ComplexityMetrics,
    ComplexityReport,
    ConflictItem,
    ConflictReport,
    FileLock,
    ImpactReport,
    LockResult,
    PromptCompilation,
    ReviewFinding,
    ReviewReport,
    SafetyResult,
    Session,
    Task,
    TASK_TRANSITIONS,
    VALID_LOCK_MODES,
    VALID_REVIEW_VERDICTS,
    VALID_ROLES,
    VALID_SESSION_STATUSES,
    VALID_TASK_KINDS,
    VALID_TASK_STATUSES,
)


def sync_ragd(store: Optional[AgentStore] = None) -> dict:
    """Attempt RAGD health check and record event.

    Returns dict with: ok, chunk_count, status_url.
    """
    import time
    import uuid
    import json

    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:7474/health", timeout=3) as resp:
            data = json.loads(resp.read())
        ok = True
        chunk_count = data.get("active_chunks", 0)
        status = "healthy"
    except Exception as e:
        ok = False
        chunk_count = 0
        status = f"unreachable: {e}"

    event_id = "event_" + uuid.uuid4().hex[:12]
    _store = store or AgentStore()
    _store.conn.execute(
        """INSERT INTO agent_os_events(event_id, kind, payload_json, created_at)
           VALUES(?,?,?,?)""",
        (event_id, "ragd_sync",
         json.dumps({"ok": ok, "chunk_count": chunk_count, "status": status}),
         int(time.time())),
    )
    if store is None:
        _store.close()

    return {"ok": ok, "chunk_count": chunk_count, "status": status}


__all__ = [
    # Session lifecycle
    "start_session", "heartbeat", "end_session", "get_session",
    "list_sessions", "abandon_session",
    # Tasks
    "create_task", "get_task", "list_tasks", "update_task_status",
    "update_task_evidence", "record_touch",
    # Claims
    "claim_task", "release_task", "list_claims",
    # Locks
    "acquire_lock", "release_lock", "list_locks", "stale_locks", "reap_expired_locks",
    # Intelligence
    "check_conflicts", "analyze_impact",
    "compile_prompt", "run_adversarial_review",
    # Metrics
    "complexity_report", "all_packages_report", "COMPLEXITY_BUDGETS",
    # Architecture
    "refresh_architecture", "show_architecture",
    # Misc
    "sync_ragd",
    # Store
    "AgentStore",
    # Types
    "Session", "Task", "ClaimResult", "FileLock", "LockResult",
    "ConflictItem", "ConflictReport", "ImpactReport", "PromptCompilation",
    "ReviewFinding", "ReviewReport", "ComplexityMetrics", "ComplexityReport",
    "SafetyResult",
    # Constants
    "VALID_SESSION_STATUSES", "VALID_ROLES", "VALID_TASK_STATUSES",
    "VALID_TASK_KINDS", "VALID_LOCK_MODES", "VALID_REVIEW_VERDICTS",
    "TASK_TRANSITIONS",
]
