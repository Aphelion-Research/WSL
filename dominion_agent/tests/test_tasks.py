"""Tests for task CRUD and status transitions."""
from __future__ import annotations

import pytest

from dominion_agent.store import AgentStore
from dominion_agent.tasks import (
    create_task,
    get_task,
    list_tasks,
    update_task_status,
    update_task_evidence,
)
from dominion_agent.types import TASK_TRANSITIONS


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "tasks.db"))


# ---------------------------------------------------------------------------
# create_task
# ---------------------------------------------------------------------------

def test_create_task_basic(tmp_path):
    t = create_task(
        title="Fix bug",
        kind="bugfix",
        store=_store(tmp_path),
    )
    assert t.task_id.startswith("task_")
    assert t.status == "open"
    assert t.title == "Fix bug"


def test_create_task_with_scope(tmp_path):
    t = create_task(
        title="Add feature",
        kind="feature",
        scope={"files": ["src/foo.py", "tests/test_foo.py"]},
        store=_store(tmp_path),
    )
    assert "src/foo.py" in t.scope.get("files", [])


def test_create_task_invalid_kind(tmp_path):
    with pytest.raises(ValueError, match="kind"):
        create_task(title="X", kind="invalid", store=_store(tmp_path))


def test_create_task_forbidden_title(tmp_path):
    with pytest.raises(ValueError, match="forbidden"):
        create_task(
            title="Execute " + "order" + "_send trade",
            kind="ops",
            store=_store(tmp_path),
        )


def test_create_task_empty_title(tmp_path):
    with pytest.raises(ValueError):
        create_task(title="", kind="bugfix", store=_store(tmp_path))


# ---------------------------------------------------------------------------
# get_task
# ---------------------------------------------------------------------------

def test_get_task_exists(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="test", store=store)
    fetched = get_task(t.task_id, store=store)
    assert fetched is not None
    assert fetched.task_id == t.task_id


def test_get_task_not_found(tmp_path):
    result = get_task("task_nonexistent", store=_store(tmp_path))
    assert result is None


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------

def test_list_tasks_by_status(tmp_path):
    store = _store(tmp_path)
    t1 = create_task(title="T1", kind="bugfix", store=store)
    t2 = create_task(title="T2", kind="feature", store=store)
    open_tasks = list_tasks(status="open", store=store)
    ids = [t.task_id for t in open_tasks]
    assert t1.task_id in ids
    assert t2.task_id in ids


def test_list_tasks_all(tmp_path):
    store = _store(tmp_path)
    create_task(title="T1", kind="test", store=store)
    create_task(title="T2", kind="test", store=store)
    all_tasks = list_tasks(store=store)
    assert len(all_tasks) >= 2


# ---------------------------------------------------------------------------
# update_task_status — transitions
# ---------------------------------------------------------------------------

def test_status_transition_valid(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="bugfix", store=store)
    assert t.status == "open"
    t2 = update_task_status(t.task_id, "claimed", store=store)
    assert t2.status == "claimed"


def test_status_transition_invalid(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="bugfix", store=store)
    with pytest.raises(ValueError, match="transition"):
        update_task_status(t.task_id, "done", store=store)  # open → done not allowed


def test_status_force_skips_transition(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="bugfix", store=store)
    t2 = update_task_status(t.task_id, "done", force=True, store=store)
    assert t2.status == "done"


def test_done_requires_evidence(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="bugfix", store=store)
    update_task_status(t.task_id, "claimed", store=store)
    update_task_status(t.task_id, "in_progress", store=store)
    update_task_status(t.task_id, "review", store=store)
    with pytest.raises(ValueError, match="evidence"):
        update_task_status(t.task_id, "done", store=store)


def test_done_with_evidence_succeeds(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="bugfix", store=store)
    update_task_status(t.task_id, "claimed", store=store)
    update_task_status(t.task_id, "in_progress", store=store)
    update_task_status(t.task_id, "review", store=store)
    t_done = update_task_status(
        t.task_id, "done",
        evidence={"commands": [{"command": "pytest", "output": "5 passed"}]},
        store=store,
    )
    assert t_done.status == "done"


# ---------------------------------------------------------------------------
# update_task_evidence
# ---------------------------------------------------------------------------

def test_update_evidence(tmp_path):
    store = _store(tmp_path)
    t = create_task(title="T", kind="test", store=store)
    t2 = update_task_evidence(t.task_id, {"report": "reports/foo.md"}, store=store)
    assert t2.evidence.get("report") == "reports/foo.md"
