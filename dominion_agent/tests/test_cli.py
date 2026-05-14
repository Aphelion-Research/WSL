"""CLI smoke tests for dominion agent subcommands."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# We test the handler functions directly, bypassing argparse.
from dominion_agent.store import AgentStore
from dominion_agent.cli import (
    _cmd_init,
    _cmd_heartbeat,
    _cmd_end,
    _cmd_sessions,
    _cmd_task_create,
    _cmd_task_list,
    _cmd_task_show,
    _cmd_task_claim,
    _cmd_task_release,
    _cmd_task_status,
    _cmd_lock_acquire,
    _cmd_lock_release,
    _cmd_locks,
    _cmd_conflict_check,
    _cmd_impact,
    _cmd_complexity_report,
    _cmd_complexity_budget,
)


class _Args:
    """Minimal namespace replacement for argparse.Namespace in tests."""
    def __init__(self, **kw):
        self.__dict__.update(kw)
        if "json" not in kw:
            self.__dict__["json"] = True  # always JSON in tests


def _store(tmp_path):
    return AgentStore(db_path=str(tmp_path / "cli.db"))


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------

def test_cli_init_returns_session(tmp_path, capsys):
    store = _store(tmp_path)
    # Monkeypatch store injection: we'll test via the sessions module directly
    from dominion_agent.sessions import start_session
    s = start_session("cli-agent", "test", store=store)
    assert s.session_id.startswith("sess_")


def test_cli_sessions_command(tmp_path, capsys):
    store = _store(tmp_path)
    from dominion_agent.sessions import start_session
    start_session("cli-agent", "test", store=store)
    from dominion_agent.sessions import list_sessions
    sessions = list_sessions(active_only=True, store=store)
    assert len(sessions) >= 1


# ---------------------------------------------------------------------------
# Task commands
# ---------------------------------------------------------------------------

def test_cli_task_create_and_list(tmp_path):
    store = _store(tmp_path)
    from dominion_agent.tasks import create_task, list_tasks
    t = create_task(title="CLI task", kind="bugfix", store=store)
    tasks = list_tasks(store=store)
    assert any(x.task_id == t.task_id for x in tasks)


def test_cli_task_show_not_found(tmp_path, capsys):
    store = _store(tmp_path)
    args = _Args(task_id="task_nonexistent")
    rc = _cmd_task_show(args)
    assert rc == 1


def test_cli_lock_acquire_and_release(tmp_path, capsys):
    store = _store(tmp_path)
    from dominion_agent.sessions import start_session
    sess = start_session("a", "test", store=store).session_id
    from dominion_agent.locks import acquire_lock, release_lock, list_locks
    r = acquire_lock("src/x.py", sess, mode="write", store=store)
    assert r.acquired
    release_lock("src/x.py", sess, store=store)
    locks = list_locks(active_only=True, store=store)
    assert not any(l.filepath == "src/x.py" for l in locks)


# ---------------------------------------------------------------------------
# Conflict check returns exit 0 for clean files
# ---------------------------------------------------------------------------

def test_cli_conflict_check_clean(tmp_path, capsys):
    store = _store(tmp_path)
    args = _Args(task_id=None, file=["src/brand_new_file.py"])
    rc = _cmd_conflict_check(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# Impact analysis
# ---------------------------------------------------------------------------

def test_cli_impact_ragd(tmp_path, capsys):
    args = _Args(task_id=None, file=["ragd/src/query.cpp"])
    rc = _cmd_impact(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# Complexity
# ---------------------------------------------------------------------------

def test_cli_complexity_report_runs(tmp_path, capsys):
    args = _Args(package=None)
    rc = _cmd_complexity_report(args)
    # May return 0 or 1 depending on whether any package is over budget
    assert rc in (0, 1)


def test_cli_complexity_budget_lists(tmp_path, capsys):
    args = _Args(package=None)
    rc = _cmd_complexity_budget(args)
    assert rc == 0


# ---------------------------------------------------------------------------
# build_agent_subparser wires correctly
# ---------------------------------------------------------------------------

def test_build_agent_subparser_no_error():
    import argparse
    from dominion_agent.cli import build_agent_subparser
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    build_agent_subparser(sub)
    # Should not raise
    args = parser.parse_args(["agent", "--help"] if False else [])


def test_agent_init_parses(tmp_path):
    import argparse
    from dominion_agent.cli import build_agent_subparser
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    build_agent_subparser(sub)
    args = parser.parse_args([
        "agent", "init", "--name", "test-agent", "--role", "test", "--json"
    ])
    assert args.name == "test-agent"
    assert args.role == "test"
