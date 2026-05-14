"""Tests for conflict oracle."""
from __future__ import annotations

import pytest

from dominion_agent.conflicts import check_conflicts
from dominion_agent.locks import acquire_lock
from dominion_agent.sessions import start_session
from dominion_agent.store import AgentStore
from dominion_agent.tasks import create_task


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "conflicts.db"))


def _sess(store) -> str:
    return start_session("agent-1", "test", store=store).session_id


# ---------------------------------------------------------------------------
# Active lock triggers conflict
# ---------------------------------------------------------------------------

def test_active_write_lock_detected(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/locked.py", sess, mode="write", store=store)
    report = check_conflicts(files=["src/locked.py"], store=store)
    assert report.status in ("warn", "fail")
    assert any(c.type == "active_write_lock" for c in report.conflicts)


def test_active_read_lock_no_conflict(tmp_path):
    store = _store(tmp_path)
    sess = _sess(store)
    acquire_lock("src/readable.py", sess, mode="read", store=store)
    report = check_conflicts(files=["src/readable.py"], store=store)
    # Read locks don't trigger conflict_check (read+read is OK)
    conflict_types = [c.type for c in report.conflicts]
    assert "active_write_lock" not in conflict_types


# ---------------------------------------------------------------------------
# Secret path request
# ---------------------------------------------------------------------------

def test_secret_path_conflict(tmp_path):
    store = _store(tmp_path)
    report = check_conflicts(files=["secrets/mt5.env"], store=store)
    assert report.status == "fail"
    assert any(c.type == "secret_path_request" for c in report.conflicts)


# ---------------------------------------------------------------------------
# Shared interface file
# ---------------------------------------------------------------------------

def test_shared_interface_file(tmp_path):
    store = _store(tmp_path)
    report = check_conflicts(files=["scripts/dominion_cli.py"], store=store)
    assert any(c.type == "shared_interface_file" for c in report.conflicts)


# ---------------------------------------------------------------------------
# Clean files — no conflicts
# ---------------------------------------------------------------------------

def test_no_conflicts_clean(tmp_path):
    store = _store(tmp_path)
    report = check_conflicts(files=["some/random/new_file.py"], store=store)
    assert report.status == "pass"
    assert len(report.conflicts) == 0
    assert report.recommended_action == "proceed"


# ---------------------------------------------------------------------------
# Task scope overlap
# ---------------------------------------------------------------------------

def test_overlapping_task_scope(tmp_path):
    store = _store(tmp_path)
    t1 = create_task(
        title="Task A",
        kind="bugfix",
        scope={"files": ["src/shared_module.py"]},
        store=store,
    )
    t2 = create_task(
        title="Task B",
        kind="feature",
        scope={"files": ["src/shared_module.py"]},
        store=store,
    )
    report = check_conflicts(task_id=t2.task_id, store=store)
    assert any(c.type == "overlapping_task_scope" for c in report.conflicts)
