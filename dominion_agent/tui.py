"""TUI panels for Dominion Agent OS.

Rendered as string panels for dominion-ui. Each panel is self-contained.
"""
from __future__ import annotations

import time
from typing import Optional

from dominion_agent.store import AgentStore


_STALE_THRESHOLD = 30 * 60  # 30 min


def _ts(epoch: Optional[int]) -> str:
    if epoch is None:
        return "—"
    return time.strftime("%H:%M:%S", time.localtime(epoch))


def _status_icon(status: str) -> str:
    return {
        "active": "●", "idle": "○", "completed": "✓", "failed": "✗",
        "abandoned": "⚠", "open": "○", "claimed": "→", "in_progress": "▶",
        "review": "◉", "done": "✓", "blocked": "⊘", "cancelled": "✗",
    }.get(status, "?")


def _severity_icon(severity: str) -> str:
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "info": "⚪"}.get(severity, "?")


def _mode_icon(mode: str) -> str:
    return {"write": "✎", "read": "👁", "review": "◉", "exclusive": "🔒"}.get(mode, "?")


# ---------------------------------------------------------------------------
# Panel 1: Active Sessions
# ---------------------------------------------------------------------------

def _panel_sessions(store: AgentStore) -> str:
    rows = store.conn.execute(
        """SELECT session_id, agent_name, role, status, started_at, last_heartbeat
           FROM agent_sessions_v2
           WHERE status IN ('active','idle')
           ORDER BY started_at DESC LIMIT 10"""
    ).fetchall()
    if not rows:
        return "  (no active sessions)"
    now = int(time.time())
    lines: list[str] = []
    for r in rows:
        hb = r["last_heartbeat"] or r["started_at"] or 0
        stale = (now - hb) > _STALE_THRESHOLD
        stale_mark = " [STALE]" if stale else ""
        icon = _status_icon(r["status"])
        lines.append(
            f"  {icon} {r['session_id'][:16]}  {r['agent_name'][:20]:<20}  "
            f"{r['role']:<12}  hb={_ts(r['last_heartbeat'])}{stale_mark}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panel 2: Open Tasks
# ---------------------------------------------------------------------------

def _panel_tasks(store: AgentStore) -> str:
    rows = store.conn.execute(
        """SELECT task_id, title, status, priority, claimed_by_session
           FROM agent_tasks
           WHERE status NOT IN ('done','cancelled')
           ORDER BY priority ASC, created_at ASC LIMIT 15"""
    ).fetchall()
    if not rows:
        return "  (no open tasks)"
    lines: list[str] = []
    for r in rows:
        icon = _status_icon(r["status"])
        claim = f"→{r['claimed_by_session'][:12]}" if r["claimed_by_session"] else ""
        lines.append(
            f"  {icon} [{r['task_id'][:14]}]  P{r['priority']}  "
            f"{r['status']:<11}  {r['title'][:40]:<40}  {claim}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panel 3: Active File Locks
# ---------------------------------------------------------------------------

def _panel_locks(store: AgentStore) -> str:
    rows = store.conn.execute(
        """SELECT lock_id, filepath, session_id, mode, locked_at, expires_at
           FROM agent_file_locks
           WHERE status='active'
           ORDER BY locked_at ASC LIMIT 15"""
    ).fetchall()
    if not rows:
        return "  (no active locks)"
    now = int(time.time())
    lines: list[str] = []
    for r in rows:
        icon = _mode_icon(r["mode"])
        expires = r["expires_at"]
        if expires:
            remaining = max(0, expires - now)
            exp_str = f"  exp={remaining//60}m"
        else:
            exp_str = ""
        lines.append(
            f"  {icon} {r['filepath'][:45]:<45}  {r['session_id'][:16]}  "
            f"[{r['mode']}]{exp_str}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panel 4: Recent Conflicts
# ---------------------------------------------------------------------------

def _panel_conflicts(store: AgentStore) -> str:
    try:
        rows = store.conn.execute(
            """SELECT task_id, findings_json, created_at
               FROM agent_reviews
               ORDER BY created_at DESC LIMIT 5"""
        ).fetchall()
    except Exception:
        return "  (no conflict data)"
    if not rows:
        return "  (no recent reviews)"
    import json
    lines: list[str] = []
    for r in rows:
        try:
            findings = json.loads(r["findings_json"] or "[]")
            crits = sum(1 for f in findings if f.get("severity") in ("critical", "high"))
            if crits > 0:
                lines.append(
                    f"  ⚠ task={r['task_id'][:14]}  {crits} high/critical  "
                    f"at={_ts(r['created_at'])}"
                )
        except Exception:
            continue
    return "\n".join(lines) or "  (no critical findings)"


# ---------------------------------------------------------------------------
# Panel 5: Review Queue
# ---------------------------------------------------------------------------

def _panel_reviews(store: AgentStore) -> str:
    rows = store.conn.execute(
        """SELECT review_id, task_id, verdict, created_at, summary
           FROM agent_reviews
           ORDER BY created_at DESC LIMIT 8"""
    ).fetchall()
    if not rows:
        return "  (no reviews yet)"
    lines: list[str] = []
    for r in rows:
        v = r["verdict"] or "?"
        icon = {"accept": "✓", "needs_changes": "⚡", "reject": "✗", "blocked": "⊘"}.get(v, "?")
        lines.append(
            f"  {icon} [{r['review_id'][:14]}]  task={r['task_id'][:14]}  "
            f"{v:<14}  {(r['summary'] or '')[:40]}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Panel 6: Complexity
# ---------------------------------------------------------------------------

def _panel_complexity() -> str:
    try:
        from dominion_agent.complexity import all_packages_report
        reports = all_packages_report()
    except Exception as e:
        return f"  (complexity scan error: {e})"
    lines: list[str] = []
    for r in reports:
        icon = "⚠" if r.over_budget else "✓"
        lines.append(
            f"  {icon} {r.package:<20}  score={r.score:6.1f}  budget={r.budget}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Render all panels
# ---------------------------------------------------------------------------

def render_agent_panels(store: Optional[AgentStore] = None) -> str:
    """Render all Agent OS panels as a single string.

    Suitable for embedding in dominion-ui output.
    """
    _store = store or AgentStore()
    width = 80
    sep = "─" * width

    panels = [
        ("Agent OS — Active Sessions", _panel_sessions(_store)),
        ("Agent OS — Open Tasks", _panel_tasks(_store)),
        ("Agent OS — File Locks", _panel_locks(_store)),
        ("Agent OS — Recent Conflicts", _panel_conflicts(_store)),
        ("Agent OS — Review Queue", _panel_reviews(_store)),
        ("Agent OS — Complexity", _panel_complexity()),
    ]

    blocks: list[str] = []
    for title, content in panels:
        blocks.append(f"┌ {title} {'─' * max(0, width - len(title) - 4)}┐")
        for line in content.splitlines():
            blocks.append(line)
        blocks.append(f"└{sep}┘")

    if store is None:
        _store.close()

    return "\n".join(blocks)
