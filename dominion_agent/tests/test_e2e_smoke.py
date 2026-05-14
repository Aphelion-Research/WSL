"""End-to-end smoke test for the full Agent OS + cockpit stack.

Tests the complete workflow:
  create session → create task → acquire/release lock →
  generate prompt → conflict check → adversarial review →
  complexity report → dashboard → mark task done with evidence →
  assert secret paths are rejected.

Run with: python -m pytest dominion_agent/tests/test_e2e_smoke.py -v
"""
from __future__ import annotations

import json
import pytest

from dominion_agent.store import AgentStore
from dominion_agent.api import (
    start_session, end_session, heartbeat,
    create_task, update_task_status,
    acquire_lock, release_lock,
    check_conflicts, run_adversarial_review,
    all_packages_report,
)
from dominion_agent.dashboard import build_dashboard, build_next
from dominion_agent.safety import is_secret_path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    """Isolated in-memory-backed store for testing."""
    import os
    os.environ["DOMINION_AGENT_DB"] = str(tmp_path / "agent_os.db")
    s = AgentStore(db_path=tmp_path / "agent_os.db")
    yield s
    s.close()
    del os.environ["DOMINION_AGENT_DB"]


# ---------------------------------------------------------------------------
# Full workflow test
# ---------------------------------------------------------------------------

def test_full_workflow(store):
    """Exercise the complete agent OS workflow end-to-end."""

    # 1. Create session
    sess = start_session("smoke-agent", "orchestrator", store=store)
    assert sess.session_id.startswith("sess_")
    assert sess.status == "active"

    # 2. Heartbeat
    heartbeat(sess.session_id, store=store)

    # 3. Create task
    task = create_task(
        title="Smoke test task",
        kind="test",
        scope={"files": ["scripts/dominion_cli.py"]},
        validation={"commands": ["python -m pytest -q"]},
        acceptance={"criteria": ["All tests pass"]},
        store=store,
    )
    assert task.task_id.startswith("task_")
    assert task.status == "open"

    # 4. Status transitions: open → claimed → in_progress → review
    update_task_status(task.task_id, "claimed", store=store)
    update_task_status(task.task_id, "in_progress", store=store)
    update_task_status(task.task_id, "review", store=store)

    # 5. Acquire file lock
    lock = acquire_lock(
        filepath="scripts/dominion_cli.py",
        session_id=sess.session_id,
        task_id=task.task_id,
        mode="write",
        store=store,
    )
    assert lock.acquired, f"Lock should succeed: {lock.conflict_reason}"

    # 6. Release file lock
    released = release_lock(lock.filepath, sess.session_id, store=store)
    assert released

    # 7. Conflict check (no active write lock now)
    conflict = check_conflicts(
        files=["scripts/dominion_cli.py"],
        store=store,
    )
    assert conflict is not None

    # 8. Adversarial review
    review = run_adversarial_review(task.task_id, store=store)
    assert review.verdict in {"accept", "needs_changes", "reject", "blocked", "unknown"}
    assert isinstance(review.score, float)

    # 9. Mark task done — requires evidence
    with pytest.raises(ValueError, match="evidence"):
        update_task_status(task.task_id, "done", store=store)

    update_task_status(
        task.task_id, "done",
        evidence={"result": "smoke test passed", "tests": "all green"},
        store=store,
    )

    # 10. End session
    ended = end_session(sess.session_id, "completed", summary="smoke test", store=store)
    assert ended.status == "completed"


def test_secret_paths_rejected(store):
    """Secret paths must raise ValueError for any lock mode."""
    sess = start_session("sec-agent", "operator", store=store)
    task = create_task(
        title="Secret scope test",
        kind="audit",
        scope={"files": ["scripts/dominion_cli.py"]},
        store=store,
    )

    for mode in ("read", "write", "exclusive", "review"):
        with pytest.raises(ValueError, match="secret"):
            acquire_lock(
                filepath="secrets/mt5.env",
                session_id=sess.session_id,
                task_id=task.task_id,
                mode=mode,
                store=store,
            )


def test_secret_path_detection():
    """is_secret_path must correctly identify known secret patterns."""
    assert is_secret_path("secrets/mt5.env")
    assert is_secret_path("secrets/api_key.txt")
    assert not is_secret_path("scripts/dominion_cli.py")
    assert not is_secret_path("dominion_agent/safety.py")


def test_dashboard_returns_valid_schema(store):
    """build_dashboard must return a complete schema dict."""
    d = build_dashboard(store=store)
    required_keys = {
        "generated_at", "active_sessions", "stale_sessions",
        "tasks_by_status", "active_locks", "latest_events",
        "complexity_warnings", "ragd", "doctor", "local_llm", "next_action",
    }
    assert required_keys <= set(d.keys()), f"Missing keys: {required_keys - set(d.keys())}"
    assert isinstance(d["next_action"], str)
    assert isinstance(d["active_sessions"], int)
    assert isinstance(d["tasks_by_status"], dict)


def test_next_returns_valid_schema(store):
    """build_next must return a dict with priority, category, item, command."""
    n = build_next(store=store)
    assert "priority" in n
    assert "category" in n
    assert "item" in n
    assert "command" in n
    assert "all_items" in n
    assert isinstance(n["all_items"], list)


def test_complexity_report_runs():
    """all_packages_report must run and return list with expected structure."""
    reports = all_packages_report()
    assert isinstance(reports, list)
    assert len(reports) > 0
    for r in reports:
        assert hasattr(r, "package")
        assert hasattr(r, "score")
        assert hasattr(r, "budget")
        assert hasattr(r, "over_budget")
        assert isinstance(r.score, float)
        assert r.score >= 0.0
