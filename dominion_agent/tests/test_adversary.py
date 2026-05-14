"""Tests for adversarial review."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pytest

from dominion_agent.adversary import run_adversarial_review
from dominion_agent.sessions import start_session
from dominion_agent.store import AgentStore
from dominion_agent.tasks import create_task, update_task_status, update_task_evidence
from dominion_agent.claims import claim_task


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "adversary.db"))


def _bare_task(store, **kw):
    return create_task(
        title=kw.get("title", "Plain task"),
        kind=kw.get("kind", "bugfix"),
        scope=kw.get("scope", {}),
        validation=kw.get("validation", {}),
        store=store,
    )


# ---------------------------------------------------------------------------
# Missing validation detected
# ---------------------------------------------------------------------------

def test_missing_validation_found(tmp_path):
    store = _store(tmp_path)
    task = _bare_task(store, validation={})
    report = run_adversarial_review(task.task_id, store=store)
    types = [f.type for f in report.findings]
    assert "missing_validation" in types


# ---------------------------------------------------------------------------
# Missing evidence detected
# ---------------------------------------------------------------------------

def test_missing_evidence_detected(tmp_path):
    store = _store(tmp_path)
    task = _bare_task(store)
    report = run_adversarial_review(task.task_id, store=store)
    types = [f.type for f in report.findings]
    assert "missing_validation" in types or "missing_report" in types


# ---------------------------------------------------------------------------
# Forbidden trading token caught
# ---------------------------------------------------------------------------

def test_forbidden_token_in_scope_file(tmp_path, tmp_path_factory):
    store = _store(tmp_path)
    # Create a temp file with forbidden token
    evil_file = tmp_path / "evil_code.py"
    evil_file.write_text("def trade():\n    " + "order" + "_send(1)\n", encoding="utf-8")
    task = create_task(
        title="Evil task",
        kind="feature",
        scope={"files": [str(evil_file)]},
        validation={"commands": ["echo ok"]},
        store=store,
    )
    report = run_adversarial_review(task.task_id, store=store)
    sev_critical = [f for f in report.findings if f.severity == "critical"]
    assert any("order" + "_send" in f.message or "trading" in f.type.lower()
               for f in sev_critical)


# ---------------------------------------------------------------------------
# Task not found → blocked verdict
# ---------------------------------------------------------------------------

def test_task_not_found_gives_blocked(tmp_path):
    store = _store(tmp_path)
    report = run_adversarial_review("task_nonexistent", store=store)
    assert report.verdict == "blocked"
    assert report.score == 0.0


# ---------------------------------------------------------------------------
# Clean task → accept verdict
# ---------------------------------------------------------------------------

def test_clean_task_accepts(tmp_path):
    store = _store(tmp_path)
    sess = start_session("reviewer", "review", store=store).session_id

    # Create a task with report file
    report_path = tmp_path / "report.md"
    report_path.write_text("# Report\n\nAll passing.\n", encoding="utf-8")

    task = create_task(
        title="Clean feature",
        kind="feature",
        scope={"files": ["src/new_module.py"]},
        validation={"commands": ["python -m pytest -q"]},
        store=store,
    )
    claim_task(task.task_id, sess, store=store)
    update_task_evidence(
        task.task_id,
        {"report": str(report_path), "commands": [{"command": "pytest", "output": "3 passed"}]},
        store=store,
    )
    report = run_adversarial_review(task.task_id, store=store)
    # With claim, evidence, report file, and pytest in commands:
    assert report.verdict in ("accept", "needs_changes")
    assert report.score > 0.0


# ---------------------------------------------------------------------------
# Score range
# ---------------------------------------------------------------------------

def test_score_is_between_0_and_1(tmp_path):
    store = _store(tmp_path)
    task = _bare_task(store)
    report = run_adversarial_review(task.task_id, store=store)
    assert 0.0 <= report.score <= 1.0


def test_review_id_starts_with_rev(tmp_path):
    store = _store(tmp_path)
    task = _bare_task(store)
    report = run_adversarial_review(task.task_id, store=store)
    assert report.review_id.startswith("rev_")
