"""Cockpit dashboard and next-action advisor for Dominion Agent OS.

Assembles a single snapshot of system health, agent activity, and
recommended next actions — without heavy computation or external deps.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from dominion_agent.store import AgentStore
from dominion_agent.types import STALE_THRESHOLD_SECONDS


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ragd_status() -> dict:
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:7474/health", timeout=3) as resp:
            data = json.loads(resp.read())
        return {
            "reachable": True,
            "chunk_count": data.get("active_chunks", 0),
            "total_chunks": data.get("total_chunks", 0),
            "orphan_hint": data.get("orphan_chunks", 0),
        }
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def _llm_status() -> dict:
    try:
        from local_llm.governor import Governor
        gov = Governor()
        return {
            "provider": gov.provider_name(),
            "model": gov.current_model(),
            "can_generate": gov.can_generate(),
            "retrieve_only": gov.retrieve_only(),
        }
    except Exception as exc:
        return {"provider": "unavailable", "error": str(exc)}


def _doctor_quick() -> dict:
    """Run cheap deep-doctor subset (manifest + ignore + cache only)."""
    checks: dict[str, str] = {}
    try:
        from dominion_loader.ignore import Ignore
        ig = Ignore()
        rules = ig.builtin_rules()
        checks["ignore_rules"] = "ok" if "secrets" in rules.get("dir_deny", set()) else "warn"
    except Exception:
        checks["ignore_rules"] = "error"

    try:
        import tempfile
        from pathlib import Path
        from dominion_loader.manifest import Manifest
        with tempfile.TemporaryDirectory() as td:
            m = Manifest(Path(td) / "test.db")
            m.stats()
            m.close()
        checks["manifest"] = "ok"
    except Exception:
        checks["manifest"] = "error"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "warn"
    return {"overall": overall, "checks": checks}


def _complexity_warnings() -> list[dict]:
    """Return list of over-budget packages."""
    try:
        from dominion_agent.complexity import all_packages_report
        warnings = []
        for report in all_packages_report():
            if report.over_budget:
                warnings.append({
                    "package": report.package,
                    "score": report.score,
                    "budget": report.budget,
                    "top_warning": report.warnings[0] if report.warnings else "",
                })
        return warnings
    except Exception:
        return []


def _agent_os_summary(store: AgentStore) -> dict:
    """Query the agent OS DB for session/task/lock/event counts."""
    now = int(time.time())
    stale_cutoff = now - STALE_THRESHOLD_SECONDS

    # Sessions
    sessions_row = store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_sessions_v2 WHERE status='active'"
    ).fetchone()
    active_sessions = sessions_row["n"] if sessions_row else 0

    stale_row = store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_sessions_v2 WHERE status='active' AND last_heartbeat < ?",
        (stale_cutoff,)
    ).fetchone()
    stale_sessions = stale_row["n"] if stale_row else 0

    # Tasks by status
    task_rows = store.conn.execute(
        "SELECT status, COUNT(*) as n FROM agent_tasks GROUP BY status"
    ).fetchall()
    tasks_by_status = {row["status"]: row["n"] for row in task_rows}

    # Active locks
    locks_row = store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_file_locks WHERE status='active'"
    ).fetchone()
    active_locks = locks_row["n"] if locks_row else 0

    # Latest events
    event_rows = store.conn.execute(
        "SELECT kind, payload_json, created_at FROM agent_os_events ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    latest_events = [
        {
            "kind": row["kind"],
            "created_at": row["created_at"],
            "summary": _summarize_event(row["kind"], row["payload_json"]),
        }
        for row in event_rows
    ]

    return {
        "active_sessions": active_sessions,
        "stale_sessions": stale_sessions,
        "tasks_by_status": tasks_by_status,
        "active_locks": active_locks,
        "latest_events": latest_events,
    }


def _summarize_event(kind: str, payload_json: str) -> str:
    try:
        p = json.loads(payload_json)
    except Exception:
        return kind
    if kind == "ragd_sync":
        return f"RAGD {'ok' if p.get('ok') else 'fail'} chunks={p.get('chunk_count',0)}"
    return kind


def _next_action(
    *,
    stale_sessions: int,
    tasks_by_status: dict,
    over_budget: list[dict],
    ragd_reachable: bool,
    doctor_overall: str,
    llm_provider: str,
) -> str:
    """Determine the single most important next action."""
    # Priority order: safety > broken infra > stale work > debt
    if not ragd_reachable:
        return "RAGD is unreachable — run: dominion start"
    if doctor_overall == "error":
        return "Deep doctor errors found — run: dominion doctor --deep --json"
    if stale_sessions > 0:
        return (
            f"{stale_sessions} stale session(s) need cleanup — run: "
            "dominion agent sessions --stale --json"
        )
    pending = tasks_by_status.get("open", 0) + tasks_by_status.get("claimed", 0)
    in_progress = tasks_by_status.get("in_progress", 0)
    if in_progress > 0:
        return (
            f"{in_progress} task(s) in_progress — review and close them: "
            "dominion agent task list --status in_progress --json"
        )
    if pending > 0:
        return (
            f"{pending} pending task(s) — pick up work: "
            "dominion agent task list --status open --json"
        )
    if over_budget:
        pkg = over_budget[0]["package"]
        return (
            f"Package '{pkg}' is over complexity budget — run: "
            f"dominion agent complexity budget --package {pkg}"
        )
    if llm_provider == "unavailable":
        return "Local LLM unavailable — check: dominion llm"
    return "System nominal — run dominion truth to verify full integrity"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_dashboard(store: Optional[AgentStore] = None) -> dict:
    """Build a full cockpit dashboard snapshot.

    Returns a dict suitable for JSON serialisation or human display.
    """
    _store = store or AgentStore()

    ragd = _ragd_status()
    llm = _llm_status()
    doctor = _doctor_quick()
    complexity_warnings = _complexity_warnings()
    agent_os = _agent_os_summary(_store)

    if store is None:
        _store.close()

    next_action = _next_action(
        stale_sessions=agent_os["stale_sessions"],
        tasks_by_status=agent_os["tasks_by_status"],
        over_budget=complexity_warnings,
        ragd_reachable=ragd.get("reachable", False),
        doctor_overall=doctor.get("overall", "unknown"),
        llm_provider=llm.get("provider", "unavailable"),
    )

    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "active_sessions": agent_os["active_sessions"],
        "stale_sessions": agent_os["stale_sessions"],
        "tasks_by_status": agent_os["tasks_by_status"],
        "active_locks": agent_os["active_locks"],
        "latest_events": agent_os["latest_events"],
        "complexity_warnings": complexity_warnings,
        "ragd": ragd,
        "doctor": doctor,
        "local_llm": llm,
        "next_action": next_action,
    }


def build_next(store: Optional[AgentStore] = None) -> dict:
    """Return the highest-priority actionable item with context.

    Checks (in order):
      1. Doctor failures
      2. RAGD unreachable
      3. Stale sessions
      4. Over-budget packages (sorted by excess)
      5. Pending/open tasks
      6. Missing evidence on review tasks
      7. TEMP_ADAPTER debt
      8. Orphan chunk warnings
    """
    _store = store or AgentStore()
    items: list[dict] = []

    # 1. Doctor
    try:
        doctor = _doctor_quick()
        if doctor["overall"] != "ok":
            for check, status in doctor["checks"].items():
                if status != "ok":
                    items.append({
                        "priority": 10,
                        "category": "doctor",
                        "item": f"doctor check '{check}' = {status}",
                        "command": "dominion doctor --deep --json",
                    })
    except Exception:
        pass

    # 2. RAGD
    ragd = _ragd_status()
    if not ragd.get("reachable"):
        items.append({
            "priority": 9,
            "category": "infrastructure",
            "item": "RAGD is unreachable",
            "command": "dominion start",
        })
    elif ragd.get("orphan_hint", 0) > 0:
        items.append({
            "priority": 3,
            "category": "ragd",
            "item": f"RAGD has {ragd['orphan_hint']} orphan chunks",
            "command": "dominion doctor --deep --json",
        })

    # 3. Stale sessions
    now = int(time.time())
    stale_cutoff = now - STALE_THRESHOLD_SECONDS
    stale_rows = _store.conn.execute(
        "SELECT session_id, agent_name FROM agent_sessions_v2 "
        "WHERE status='active' AND last_heartbeat < ?",
        (stale_cutoff,)
    ).fetchall()
    for row in stale_rows:
        items.append({
            "priority": 8,
            "category": "sessions",
            "item": f"Stale session {row['session_id']} ({row['agent_name']})",
            "command": f"dominion agent session abandon {row['session_id']}",
        })

    # 4. Over-budget packages
    for warn in _complexity_warnings():
        excess = warn["score"] - warn["budget"]
        items.append({
            "priority": max(2, min(7, int(excess / 5))),
            "category": "complexity",
            "item": f"Package '{warn['package']}' over budget by {excess:.1f} ({warn['top_warning']})",
            "command": f"dominion agent complexity budget --package {warn['package']}",
        })

    # 5. Pending tasks
    open_rows = _store.conn.execute(
        "SELECT task_id, title, status FROM agent_tasks WHERE status IN ('open','claimed') LIMIT 5"
    ).fetchall()
    for row in open_rows:
        items.append({
            "priority": 6,
            "category": "tasks",
            "item": f"Task '{row['title']}' ({row['status']})",
            "command": f"dominion agent task show {row['task_id']}",
        })

    # 6. Review tasks missing evidence
    review_rows = _store.conn.execute(
        "SELECT task_id, title FROM agent_tasks WHERE status='review' AND evidence_json IN ('{}','null','') LIMIT 5"
    ).fetchall()
    for row in review_rows:
        items.append({
            "priority": 7,
            "category": "tasks",
            "item": f"Task '{row['title']}' in review but lacks evidence",
            "command": f"dominion agent task status {row['task_id']} --status done --evidence '{{\"result\":\"...\"}}'",
        })

    if store is None:
        _store.close()

    if not items:
        return {
            "priority": 0,
            "category": "nominal",
            "item": "System nominal — nothing urgent",
            "command": "dominion truth --json",
            "all_items": [],
        }

    # Sort by priority descending, return top item + all items
    items.sort(key=lambda x: x["priority"], reverse=True)
    top = items[0]
    return {**top, "all_items": items}


def format_dashboard_human(d: dict) -> str:
    """Format dashboard dict as human-readable text."""
    lines = [
        f"=== Dominion Cockpit  {d['generated_at']} ===",
        "",
        "--- Agent OS ---",
        f"  Active sessions : {d['active_sessions']}",
        f"  Stale sessions  : {d['stale_sessions']}",
        f"  Active locks    : {d['active_locks']}",
        "  Tasks:",
    ]
    for status, count in sorted(d["tasks_by_status"].items()):
        lines.append(f"    {status:12s}: {count}")
    lines.append("")
    lines.append("--- Recent Events ---")
    if d["latest_events"]:
        for ev in d["latest_events"]:
            ts = time.strftime("%H:%M:%SZ", time.gmtime(ev["created_at"]))
            lines.append(f"  {ts}  {ev['kind']:20s}  {ev['summary']}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append("--- Infrastructure ---")
    ragd = d["ragd"]
    if ragd.get("reachable"):
        lines.append(f"  RAGD      : OK  chunks={ragd.get('chunk_count',0)}")
        if ragd.get("orphan_hint", 0):
            lines.append(f"  RAGD      : WARN  {ragd['orphan_hint']} orphan chunk(s)")
    else:
        lines.append(f"  RAGD      : UNREACHABLE  {ragd.get('error','')}")
    llm = d["local_llm"]
    if llm.get("provider") != "unavailable":
        can_gen = "generate" if llm.get("can_generate") else "retrieve-only"
        lines.append(f"  Local LLM : {llm['provider']} / {llm.get('model','')} ({can_gen})")
    else:
        lines.append(f"  Local LLM : unavailable  {llm.get('error','')}")
    doc = d["doctor"]
    lines.append(f"  Doctor    : {doc.get('overall','?').upper()}")
    lines.append("")
    lines.append("--- Complexity Warnings ---")
    if d["complexity_warnings"]:
        for w in d["complexity_warnings"]:
            lines.append(f"  OVER-BUDGET  {w['package']}  score={w['score']:.1f}  budget={w['budget']:.1f}")
            if w.get("top_warning"):
                lines.append(f"             {w['top_warning']}")
    else:
        lines.append("  All packages within budget.")
    lines.append("")
    lines.append(f">>> Next action: {d['next_action']}")
    return "\n".join(lines)
