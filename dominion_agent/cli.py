"""CLI entry point for `dominion agent ...` subcommands.

Wire into scripts/dominion_cli.py:

    from dominion_agent.cli import build_agent_subparser
    build_agent_subparser(sub)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(data: object, json_mode: bool) -> None:
    if json_mode:
        print(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    print(f"{k}:")
                    print(json.dumps(v, indent=4, default=str))
                else:
                    print(f"  {k}: {v}")
        elif isinstance(data, list):
            for item in data:
                print(json.dumps(item, indent=2, default=str))
        else:
            print(data)


def _error(msg: str, json_mode: bool = False) -> int:
    if json_mode:
        print(json.dumps({"error": msg}), file=sys.stderr)
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def _scope_files(args: argparse.Namespace) -> list[str]:
    files: list[str] = []
    if hasattr(args, "scope_file") and args.scope_file:
        files = list(args.scope_file)
    return files


def _read_json_file(path: str) -> object:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Handler functions
# ---------------------------------------------------------------------------

def _cmd_init(args: argparse.Namespace) -> int:
    from dominion_agent.sessions import start_session
    from dominion_agent.reports import session_to_dict
    meta: dict = {}
    if hasattr(args, "meta") and args.meta:
        meta = json.loads(args.meta)
    s = start_session(
        agent_name=args.name,
        role=args.role,
        metadata=meta,
        parent_session_id=getattr(args, "parent", None) or "",
    )
    _out(session_to_dict(s), getattr(args, "json", False))
    return 0


def _cmd_heartbeat(args: argparse.Namespace) -> int:
    from dominion_agent.sessions import heartbeat
    heartbeat(args.session_id)
    _out({"ok": True, "session_id": args.session_id}, getattr(args, "json", False))
    return 0


def _cmd_end(args: argparse.Namespace) -> int:
    from dominion_agent.sessions import end_session
    from dominion_agent.reports import session_to_dict
    summary = getattr(args, "summary", "") or ""
    s = end_session(
        args.session_id,
        status=getattr(args, "status", "completed") or "completed",
        summary=summary,
    )
    _out(session_to_dict(s), getattr(args, "json", False))
    return 0


def _cmd_sessions(args: argparse.Namespace) -> int:
    from dominion_agent.sessions import list_sessions
    from dominion_agent.reports import session_to_dict
    active_only = getattr(args, "active", False)
    stale_only = getattr(args, "stale", False)
    sessions = list_sessions(active_only=active_only, stale_only=stale_only)
    _out([session_to_dict(s) for s in sessions], getattr(args, "json", False))
    return 0


def _cmd_session_abandon(args: argparse.Namespace) -> int:
    from dominion_agent.sessions import abandon_session
    from dominion_agent.reports import session_to_dict
    reason = getattr(args, "reason", "") or ""
    s = abandon_session(args.session_id, reason=reason)
    _out(session_to_dict(s), getattr(args, "json", False))
    return 0


def _cmd_task_create(args: argparse.Namespace) -> int:
    from dominion_agent.tasks import create_task
    from dominion_agent.reports import task_to_dict
    scope_files = _scope_files(args)
    validation_cmds: list[str] = getattr(args, "validation", None) or []
    acceptance: list[str] = getattr(args, "acceptance", None) or []
    tags: list[str] = getattr(args, "tags", None) or []

    scope = {"files": scope_files}
    if hasattr(args, "scope_package") and args.scope_package:
        scope["packages"] = list(args.scope_package)

    task = create_task(
        title=args.title,
        description=getattr(args, "description", "") or "",
        kind=args.kind,
        priority=getattr(args, "priority", 3) or 3,
        scope=scope,
        validation={"commands": validation_cmds},
        acceptance={"criteria": acceptance},
        risk={"level": getattr(args, "risk", "medium") or "medium"},
        tags=tags,
        parent_task_id=getattr(args, "parent", "") or "",
    )
    _out(task_to_dict(task), getattr(args, "json", False))
    return 0


def _cmd_task_list(args: argparse.Namespace) -> int:
    from dominion_agent.tasks import list_tasks
    from dominion_agent.reports import task_to_dict
    status = getattr(args, "status", None)
    limit = getattr(args, "limit", 50) or 50
    tasks = list_tasks(status=status, limit=limit)
    _out([task_to_dict(t) for t in tasks], getattr(args, "json", False))
    return 0


def _cmd_task_show(args: argparse.Namespace) -> int:
    from dominion_agent.tasks import get_task
    from dominion_agent.reports import task_to_dict
    task = get_task(args.task_id)
    if task is None:
        return _error(f"task not found: {args.task_id}", getattr(args, "json", False))
    _out(task_to_dict(task), getattr(args, "json", False))
    return 0


def _cmd_task_claim(args: argparse.Namespace) -> int:
    from dominion_agent.claims import claim_task
    from dominion_agent.reports import claim_to_dict
    result = claim_task(
        args.task_id,
        args.session_id,
        collaborative=getattr(args, "collaborative", False),
    )
    _out(claim_to_dict(result), getattr(args, "json", False))
    return 0


def _cmd_task_release(args: argparse.Namespace) -> int:
    from dominion_agent.claims import release_task
    note = getattr(args, "note", "") or ""
    release_task(args.task_id, args.session_id, note=note)
    _out({"ok": True, "task_id": args.task_id}, getattr(args, "json", False))
    return 0


def _cmd_task_status(args: argparse.Namespace) -> int:
    from dominion_agent.tasks import update_task_status, update_task_evidence
    from dominion_agent.reports import task_to_dict
    evidence: dict = {}
    if hasattr(args, "evidence_file") and args.evidence_file:
        evidence = json.loads(Path(args.evidence_file).read_text(encoding="utf-8"))
    elif hasattr(args, "evidence") and args.evidence:
        evidence = json.loads(args.evidence)

    force = getattr(args, "force", False)
    task = update_task_status(
        args.task_id,
        new_status=args.status,
        evidence=evidence or None,
        force=force,
    )
    _out(task_to_dict(task), getattr(args, "json", False))
    return 0


def _cmd_lock_acquire(args: argparse.Namespace) -> int:
    from dominion_agent.locks import acquire_lock
    from dominion_agent.reports import lock_to_dict
    result = acquire_lock(
        filepath=args.file,
        session_id=args.session_id,
        task_id=getattr(args, "task_id", "") or "",
        mode=getattr(args, "mode", "write") or "write",
        expires_in_seconds=getattr(args, "expires", 3600) or 3600,
        note=getattr(args, "note", "") or "",
    )
    if not result.acquired:
        print(
            json.dumps({"acquired": False, "conflict": result.conflict_reason}),
            file=sys.stderr,
        )
        return 2
    # Fetch full lock to return
    from dominion_agent.locks import list_locks
    locks = list_locks(active_only=True)
    lock = next((l for l in locks if l.lock_id == result.lock_id), None)
    _out(
        {"acquired": True, "lock_id": result.lock_id} if lock is None else lock_to_dict(lock),
        getattr(args, "json", False),
    )
    return 0


def _cmd_lock_release(args: argparse.Namespace) -> int:
    from dominion_agent.locks import release_lock
    force = getattr(args, "force", False)
    release_lock(args.file, args.session_id, force=force)
    _out({"ok": True, "filepath": args.file}, getattr(args, "json", False))
    return 0


def _cmd_lock_reap(args: argparse.Namespace) -> int:
    from dominion_agent.locks import reap_expired_locks
    n = reap_expired_locks()
    _out({"reaped": n}, getattr(args, "json", False))
    return 0


def _cmd_locks(args: argparse.Namespace) -> int:
    from dominion_agent.locks import list_locks
    from dominion_agent.reports import lock_to_dict
    active_only = not getattr(args, "all", False)
    locks = list_locks(active_only=active_only)
    _out([lock_to_dict(l) for l in locks], getattr(args, "json", False))
    return 0


def _cmd_conflict_check(args: argparse.Namespace) -> int:
    from dominion_agent.conflicts import check_conflicts
    task_id = getattr(args, "task_id", None)
    files: list[str] = getattr(args, "file", None) or []
    report = check_conflicts(task_id=task_id, files=files)
    _out(report.to_dict(), getattr(args, "json", False))
    return 0 if report.status == "pass" else 1


def _cmd_impact(args: argparse.Namespace) -> int:
    from dominion_agent.impact import analyze_impact
    task_id = getattr(args, "task_id", None)
    files: list[str] = getattr(args, "file", None) or []
    report = analyze_impact(files=files, task_id=task_id)
    _out(report.to_dict(), getattr(args, "json", False))
    return 0


def _cmd_prompt(args: argparse.Namespace) -> int:
    from dominion_agent.prompt_compiler import compile_prompt
    from dominion_agent.reports import compilation_to_dict
    output_path = getattr(args, "out", None)
    target = getattr(args, "for_agent", "codex") or "codex"
    result = compile_prompt(
        args.task_id,
        target_agent=target,
        output_path=output_path,
    )
    if output_path:
        print(f"Prompt written to: {output_path}")
    d = compilation_to_dict(result)
    if not getattr(args, "no_prompt", False):
        d["prompt_text"] = result.prompt_text
    _out(d, getattr(args, "json", False))
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    from dominion_agent.adversary import run_adversarial_review
    report = run_adversarial_review(
        args.task_id,
        strict=getattr(args, "strict", False),
    )
    _out(report.to_dict(), getattr(args, "json", False))
    # Non-zero if not accepted
    return 0 if report.verdict == "accept" else 1


def _cmd_architecture_refresh(args: argparse.Namespace) -> int:
    from dominion_agent.architecture import refresh_architecture
    result = refresh_architecture()
    _out(result, getattr(args, "json", False))
    return 0


def _cmd_architecture_show(args: argparse.Namespace) -> int:
    from dominion_agent.architecture import show_architecture
    content = show_architecture()
    if content is None:
        return _error(
            "LIVING_ARCHITECTURE.md not found. Run: dominion agent architecture refresh",
            getattr(args, "json", False),
        )
    if getattr(args, "json", False):
        _out({"content": content}, True)
    else:
        print(content)
    return 0


def _cmd_complexity_report(args: argparse.Namespace) -> int:
    from dominion_agent.complexity import all_packages_report, complexity_report
    from dominion_agent.reports import complexity_report_to_dict
    pkg = getattr(args, "package", None)
    if pkg:
        r = complexity_report(pkg)
        _out(complexity_report_to_dict(r), getattr(args, "json", False))
        return 1 if r.over_budget else 0
    else:
        reports = all_packages_report()
        _out([complexity_report_to_dict(r) for r in reports], getattr(args, "json", False))
        return 1 if any(r.over_budget for r in reports) else 0


def _cmd_complexity_budget(args: argparse.Namespace) -> int:
    from dominion_agent.complexity import COMPLEXITY_BUDGETS, complexity_report
    from dominion_agent.reports import complexity_report_to_dict
    pkg = getattr(args, "package", None)
    if pkg:
        r = complexity_report(pkg)
        _out(complexity_report_to_dict(r), getattr(args, "json", False))
        return 1 if r.over_budget else 0
    # Print all budgets
    _out(COMPLEXITY_BUDGETS, getattr(args, "json", False))
    return 0


def _cmd_sync_ragd(args: argparse.Namespace) -> int:
    from dominion_agent.api import sync_ragd
    result = sync_ragd()
    _out(result, getattr(args, "json", False))
    return 0 if result["ok"] else 1


def _cmd_dashboard(args: argparse.Namespace) -> int:
    from dominion_agent.dashboard import build_dashboard, format_dashboard_human
    d = build_dashboard()
    if getattr(args, "json", False):
        _out(d, True)
    else:
        print(format_dashboard_human(d))
    return 0


def _cmd_next(args: argparse.Namespace) -> int:
    from dominion_agent.dashboard import build_next
    result = build_next()
    json_mode = getattr(args, "json", False)
    if json_mode:
        _out(result, True)
    else:
        print(f"Priority {result['priority']} [{result['category']}]  {result['item']}")
        print(f"Command: {result['command']}")
        all_items = result.get("all_items", [])
        if len(all_items) > 1:
            print(f"\nAll {len(all_items)} items:")
            for item in all_items:
                print(f"  [{item['priority']}] {item['item']}")
    return 0


# ---------------------------------------------------------------------------
# Parser builder
# ---------------------------------------------------------------------------

def build_agent_subparser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Attach the `agent` subcommand tree to the top-level parser."""

    agent_p = sub.add_parser("agent", help="Dominion Agent OS — session/task/lock/review control")
    agent_sub = agent_p.add_subparsers(dest="agent_command", metavar="COMMAND")

    # -- init ----------------------------------------------------------------
    p_init = agent_sub.add_parser("init", help="Start a new agent session")
    p_init.add_argument("--name", required=True, help="Agent name")
    p_init.add_argument("--role", required=True,
                        choices=["foundation", "retrieval", "truth", "orchestrator",
                                 "review", "docs", "test", "operator", "unknown"])
    p_init.add_argument("--meta", help="JSON metadata string")
    p_init.add_argument("--parent", help="Parent session ID")
    p_init.add_argument("--json", action="store_true")
    p_init.set_defaults(agent_func=_cmd_init)

    # -- heartbeat -----------------------------------------------------------
    p_hb = agent_sub.add_parser("heartbeat", help="Ping a session to keep it alive")
    p_hb.add_argument("session_id")
    p_hb.add_argument("--json", action="store_true")
    p_hb.set_defaults(agent_func=_cmd_heartbeat)

    # -- end -----------------------------------------------------------------
    p_end = agent_sub.add_parser("end", help="End a session")
    p_end.add_argument("session_id")
    p_end.add_argument("--status", default="completed",
                       choices=["completed", "failed", "abandoned"])
    p_end.add_argument("--summary", default="")
    p_end.add_argument("--json", action="store_true")
    p_end.set_defaults(agent_func=_cmd_end)

    # -- sessions ------------------------------------------------------------
    p_sessions = agent_sub.add_parser("sessions", help="List sessions")
    p_sessions.add_argument("--active", action="store_true", help="Only active sessions")
    p_sessions.add_argument("--stale", action="store_true", help="Only stale sessions")
    p_sessions.add_argument("--json", action="store_true")
    p_sessions.set_defaults(agent_func=_cmd_sessions)

    # -- session (sub-sub) ---------------------------------------------------
    p_session = agent_sub.add_parser("session", help="Session operations")
    session_sub = p_session.add_subparsers(dest="session_command", metavar="OP")

    p_abandon = session_sub.add_parser("abandon", help="Abandon a session")
    p_abandon.add_argument("session_id")
    p_abandon.add_argument("--reason", default="")
    p_abandon.add_argument("--json", action="store_true")
    p_abandon.set_defaults(agent_func=_cmd_session_abandon)

    # -- task (sub-sub) ------------------------------------------------------
    p_task = agent_sub.add_parser("task", help="Task management")
    task_sub = p_task.add_subparsers(dest="task_command", metavar="OP")

    # task create
    p_tc = task_sub.add_parser("create", help="Create a task")
    p_tc.add_argument("--title", required=True)
    p_tc.add_argument("--kind", required=True,
                      choices=["bugfix", "feature", "audit", "docs", "test",
                               "refactor", "research", "ops", "review"])
    p_tc.add_argument("--description", default="")
    p_tc.add_argument("--priority", type=int, default=3, choices=[1, 2, 3, 4, 5])
    p_tc.add_argument("--scope-file", dest="scope_file", action="append", metavar="FILE")
    p_tc.add_argument("--scope-package", dest="scope_package", action="append", metavar="PKG")
    p_tc.add_argument("--validation", action="append", metavar="CMD",
                      help="Validation command (repeat for multiple)")
    p_tc.add_argument("--acceptance", action="append", metavar="CRITERION")
    p_tc.add_argument("--risk", default="medium", choices=["low", "medium", "high", "critical"])
    p_tc.add_argument("--tags", action="append", metavar="TAG")
    p_tc.add_argument("--parent", help="Parent task ID")
    p_tc.add_argument("--json", action="store_true")
    p_tc.set_defaults(agent_func=_cmd_task_create)

    # task list
    p_tl = task_sub.add_parser("list", help="List tasks")
    p_tl.add_argument("--status",
                      choices=["open", "claimed", "in_progress", "review",
                               "done", "blocked", "cancelled"])
    p_tl.add_argument("--limit", type=int, default=50)
    p_tl.add_argument("--json", action="store_true")
    p_tl.set_defaults(agent_func=_cmd_task_list)

    # task show
    p_ts = task_sub.add_parser("show", help="Show a task")
    p_ts.add_argument("task_id")
    p_ts.add_argument("--json", action="store_true")
    p_ts.set_defaults(agent_func=_cmd_task_show)

    # task claim
    p_tcl = task_sub.add_parser("claim", help="Claim a task for a session")
    p_tcl.add_argument("task_id")
    p_tcl.add_argument("--session", dest="session_id", required=True)
    p_tcl.add_argument("--collaborative", action="store_true")
    p_tcl.add_argument("--json", action="store_true")
    p_tcl.set_defaults(agent_func=_cmd_task_claim)

    # task release
    p_trl = task_sub.add_parser("release", help="Release a task claim")
    p_trl.add_argument("task_id")
    p_trl.add_argument("--session", dest="session_id", required=True)
    p_trl.add_argument("--note", default="")
    p_trl.add_argument("--json", action="store_true")
    p_trl.set_defaults(agent_func=_cmd_task_release)

    # task status
    p_tst = task_sub.add_parser("status", help="Update task status")
    p_tst.add_argument("task_id")
    p_tst.add_argument("--status", required=True,
                       choices=["open", "claimed", "in_progress", "review",
                                "done", "blocked", "cancelled"])
    p_tst.add_argument("--evidence-file", dest="evidence_file",
                       help="Path to JSON evidence file")
    p_tst.add_argument("--evidence", help="JSON evidence string")
    p_tst.add_argument("--force", action="store_true",
                       help="Skip transition validation")
    p_tst.add_argument("--json", action="store_true")
    p_tst.set_defaults(agent_func=_cmd_task_status)

    # -- lock (sub-sub) ------------------------------------------------------
    p_lock = agent_sub.add_parser("lock", help="File lock operations")
    lock_sub = p_lock.add_subparsers(dest="lock_command", metavar="OP")

    p_la = lock_sub.add_parser("acquire", help="Acquire a file lock")
    p_la.add_argument("file")
    p_la.add_argument("--session", dest="session_id", required=True)
    p_la.add_argument("--task", dest="task_id", default="")
    p_la.add_argument("--mode", default="write",
                      choices=["read", "write", "review", "exclusive"])
    p_la.add_argument("--expires", type=int, default=3600, metavar="SECONDS")
    p_la.add_argument("--note", default="")
    p_la.add_argument("--json", action="store_true")
    p_la.set_defaults(agent_func=_cmd_lock_acquire)

    p_lr = lock_sub.add_parser("release", help="Release a file lock")
    p_lr.add_argument("file")
    p_lr.add_argument("--session", dest="session_id", required=True)
    p_lr.add_argument("--force", action="store_true")
    p_lr.add_argument("--json", action="store_true")
    p_lr.set_defaults(agent_func=_cmd_lock_release)

    p_reap = lock_sub.add_parser("reap", help="Reap all expired locks (expires_at < now)")
    p_reap.add_argument("--json", action="store_true")
    p_reap.set_defaults(agent_func=_cmd_lock_reap)

    # -- locks ---------------------------------------------------------------
    p_locks = agent_sub.add_parser("locks", help="List all file locks")
    p_locks.add_argument("--all", action="store_true", help="Include released locks")
    p_locks.add_argument("--json", action="store_true")
    p_locks.set_defaults(agent_func=_cmd_locks)

    # -- conflict check ------------------------------------------------------
    p_conflict = agent_sub.add_parser("conflict", help="Conflict detection")
    conflict_sub = p_conflict.add_subparsers(dest="conflict_command", metavar="OP")

    p_cc = conflict_sub.add_parser("check", help="Check for conflicts")
    p_cc.add_argument("--task", dest="task_id", help="Task ID to check scope for")
    p_cc.add_argument("--file", action="append", metavar="FILE",
                      help="File(s) to check (repeat for multiple)")
    p_cc.add_argument("--json", action="store_true")
    p_cc.set_defaults(agent_func=_cmd_conflict_check)

    # -- impact --------------------------------------------------------------
    p_impact = agent_sub.add_parser("impact", help="Analyze change impact")
    p_impact.add_argument("--task", dest="task_id")
    p_impact.add_argument("--file", action="append", metavar="FILE")
    p_impact.add_argument("--json", action="store_true")
    p_impact.set_defaults(agent_func=_cmd_impact)

    # -- prompt --------------------------------------------------------------
    p_prompt = agent_sub.add_parser("prompt", help="Compile a task prompt")
    p_prompt.add_argument("task_id")
    p_prompt.add_argument("--for", dest="for_agent", default="codex")
    p_prompt.add_argument("--out", help="Write prompt to this file")
    p_prompt.add_argument("--no-prompt", action="store_true",
                          help="Omit prompt_text from output (just metadata)")
    p_prompt.add_argument("--json", action="store_true")
    p_prompt.set_defaults(agent_func=_cmd_prompt)

    # -- review --------------------------------------------------------------
    p_review = agent_sub.add_parser("review", help="Adversarial task review")
    p_review.add_argument("task_id")
    p_review.add_argument("--adversarial", action="store_true", dest="strict")
    p_review.add_argument("--json", action="store_true")
    p_review.set_defaults(agent_func=_cmd_review)

    # -- architecture --------------------------------------------------------
    p_arch = agent_sub.add_parser("architecture", help="Living architecture doc")
    arch_sub = p_arch.add_subparsers(dest="arch_command", metavar="OP")

    p_ar = arch_sub.add_parser("refresh", help="Rebuild LIVING_ARCHITECTURE.md")
    p_ar.add_argument("--json", action="store_true")
    p_ar.set_defaults(agent_func=_cmd_architecture_refresh)

    p_as = arch_sub.add_parser("show", help="Print LIVING_ARCHITECTURE.md")
    p_as.add_argument("--json", action="store_true")
    p_as.set_defaults(agent_func=_cmd_architecture_show)

    # -- complexity ----------------------------------------------------------
    p_compl = agent_sub.add_parser("complexity", help="Complexity budget tracking")
    compl_sub = p_compl.add_subparsers(dest="compl_command", metavar="OP")

    p_cr = compl_sub.add_parser("report", help="Complexity report")
    p_cr.add_argument("--package", help="Single package to report on")
    p_cr.add_argument("--json", action="store_true")
    p_cr.set_defaults(agent_func=_cmd_complexity_report)

    p_cb = compl_sub.add_parser("budget", help="Show complexity budgets")
    p_cb.add_argument("--package")
    p_cb.add_argument("--json", action="store_true")
    p_cb.set_defaults(agent_func=_cmd_complexity_budget)

    # -- sync-ragd -----------------------------------------------------------
    p_sync = agent_sub.add_parser("sync-ragd", help="Check RAGD health and record event")
    p_sync.add_argument("--json", action="store_true")
    p_sync.set_defaults(agent_func=_cmd_sync_ragd)

    # -- dashboard -----------------------------------------------------------
    p_dash = agent_sub.add_parser("dashboard", help="Cockpit dashboard — full system snapshot")
    p_dash.add_argument("--json", action="store_true")
    p_dash.set_defaults(agent_func=_cmd_dashboard)

    # -- next ----------------------------------------------------------------
    p_next = agent_sub.add_parser("next", help="Next recommended action")
    p_next.add_argument("--json", action="store_true")
    p_next.set_defaults(agent_func=_cmd_next)

    agent_p.set_defaults(agent_func=_default_agent_help(agent_p), func=cmd_agent)


def _default_agent_help(parser: argparse.ArgumentParser):
    def _handler(args: argparse.Namespace) -> int:
        parser.print_help()
        return 0
    return _handler


def cmd_agent(args: argparse.Namespace) -> int:
    """Top-level dispatcher for `dominion agent ...`."""
    func = getattr(args, "agent_func", None)
    if func is None:
        # No subcommand given — find the agent parser and print its help
        return 0
    try:
        return func(args) or 0
    except ValueError as e:
        return _error(str(e), getattr(args, "json", False))
    except Exception as e:
        return _error(f"unexpected error: {e}", getattr(args, "json", False))
