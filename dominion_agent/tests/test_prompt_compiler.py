"""Tests for the prompt compiler."""
from __future__ import annotations

import pytest

from dominion_agent.prompt_compiler import compile_prompt
from dominion_agent.sessions import start_session
from dominion_agent.store import AgentStore
from dominion_agent.tasks import create_task


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "prompt.db"))


def _task(store, **kwargs):
    return create_task(
        title=kwargs.get("title", "Fix the bug"),
        kind=kwargs.get("kind", "bugfix"),
        description=kwargs.get("description", "Description here"),
        scope=kwargs.get("scope", {"files": ["src/foo.py"]}),
        validation=kwargs.get("validation", {"commands": ["python -m pytest -q"]}),
        acceptance=kwargs.get("acceptance", {"criteria": ["tests pass"]}),
        store=store,
    )


# ---------------------------------------------------------------------------
# Required sections in prompt
# ---------------------------------------------------------------------------

def test_prompt_contains_task_id(tmp_path):
    store = _store(tmp_path)
    task = _task(store)
    result = compile_prompt(task.task_id, store=store)
    assert task.task_id in result.prompt_text


def test_prompt_contains_mission(tmp_path):
    store = _store(tmp_path)
    task = _task(store, title="Mission critical fix")
    result = compile_prompt(task.task_id, store=store)
    assert "Mission" in result.prompt_text
    assert "Mission critical fix" in result.prompt_text


def test_prompt_contains_safety_rules(tmp_path):
    store = _store(tmp_path)
    task = _task(store)
    result = compile_prompt(task.task_id, store=store)
    assert "Safety Rules" in result.prompt_text
    assert "order" + "_send" in result.prompt_text


def test_prompt_contains_done_criteria(tmp_path):
    store = _store(tmp_path)
    task = _task(store)
    result = compile_prompt(task.task_id, store=store)
    assert "Done Criteria" in result.prompt_text


def test_prompt_contains_validation_commands(tmp_path):
    store = _store(tmp_path)
    task = _task(store, validation={"commands": ["python -m pytest -q", "dominion doctor"]})
    result = compile_prompt(task.task_id, store=store)
    assert "pytest" in result.prompt_text


def test_prompt_contains_scope(tmp_path):
    store = _store(tmp_path)
    task = _task(store, scope={"files": ["src/targeted_file.py"]})
    result = compile_prompt(task.task_id, store=store)
    assert "targeted_file.py" in result.prompt_text


def test_prompt_contains_final_response_format(tmp_path):
    store = _store(tmp_path)
    task = _task(store)
    result = compile_prompt(task.task_id, store=store)
    assert "Final Response Format" in result.prompt_text


def test_prompt_hash_stable(tmp_path):
    store = _store(tmp_path)
    task = _task(store)
    r1 = compile_prompt(task.task_id, store=store)
    # Hash is deterministic based on prompt content
    import hashlib
    expected_hash = hashlib.sha256(r1.prompt_text.encode()).hexdigest()[:16]
    assert r1.prompt_hash == expected_hash


def test_prompt_refuses_missing_task(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(ValueError, match="not found"):
        compile_prompt("task_nonexistent", store=store)


def test_prompt_compilation_id_starts_with_comp(tmp_path):
    store = _store(tmp_path)
    task = _task(store)
    result = compile_prompt(task.task_id, store=store)
    assert result.compilation_id.startswith("comp_")


def test_prompt_redacts_secrets_scope(tmp_path):
    """If scope has secrets/ path, it should be redacted in the prompt."""
    store = _store(tmp_path)
    # Directly insert a task with secrets path in scope (bypass safety check in create_task)
    import json, uuid, time
    task_id = "task_" + uuid.uuid4().hex[:12]
    store.conn.execute(
        """INSERT INTO agent_tasks(task_id, title, description, kind, priority, status,
           created_at, updated_at, scope_json, validation_json, acceptance_json,
           risk_json, tags_json, evidence_json)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (task_id, "Secret scope task", "", "ops", 3, "open",
         int(time.time()), int(time.time()),
         json.dumps({"files": ["secrets/mt5.env"]}),
         json.dumps({"commands": []}),
         json.dumps({"criteria": []}),
         json.dumps({"level": "critical"}),
         json.dumps([]), json.dumps({}))
    )
    result = compile_prompt(task_id, store=store)
    # Scope section must use redacted placeholder, not raw secrets path
    assert "[REDACTED" in result.prompt_text
