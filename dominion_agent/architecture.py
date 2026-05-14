"""Living architecture document generator for Dominion Agent OS.

Generates docs/agents/LIVING_ARCHITECTURE.md from actual codebase state.
Evidence-based only — no invented modules.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Optional

from dominion_agent.complexity import all_packages_report
from dominion_agent.store import AgentStore


_OUTPUT_PATH = "docs/agents/LIVING_ARCHITECTURE.md"

_KNOWN_PACKAGES: list[dict] = [
    {
        "name": "dominion_loader",
        "description": "File manifest scanner and loader",
        "status_check": "python -m pytest -q dominion_loader/tests 2>&1 | tail -1",
        "api": "dominion_loader/api.py",
        "depends": [],
    },
    {
        "name": "dominion_ai",
        "description": "RAGD-backed AI query layer",
        "status_check": "python -m pytest -q dominion_ai/tests 2>&1 | tail -1",
        "api": "dominion_ai/api.py",
        "depends": ["dominion_loader", "ragd"],
    },
    {
        "name": "dominion_agent",
        "description": "Agent OS — session/task/lock/review control plane",
        "status_check": "python -m pytest -q dominion_agent/tests 2>&1 | tail -1",
        "api": "dominion_agent/api.py",
        "depends": [],
    },
    {
        "name": "ragd_embed",
        "description": "External-code embedding pipeline and cache",
        "status_check": "python -m pytest -q ragd_embed/tests 2>&1 | tail -1",
        "api": "ragd_embed/__init__.py",
        "depends": ["ragd"],
    },
    {
        "name": "ragd_hnsw",
        "description": "Persistent semantic ANN index for RAGD chunks",
        "status_check": "python -m pytest -q ragd_hnsw/tests 2>&1 | tail -1",
        "api": "ragd_hnsw/__init__.py",
        "depends": ["ragd_embed"],
    },
    {
        "name": "ragd_chunker",
        "description": "AST-aware source chunking service",
        "status_check": "python -m pytest -q ragd_chunker/tests 2>&1 | tail -1",
        "api": "ragd_chunker/__init__.py",
        "depends": ["ragd"],
    },
    {
        "name": "ragd_vault",
        "description": "Obsidian vault generator backed by the RAGD index",
        "status_check": "python -m pytest -q ragd_vault/tests 2>&1 | tail -1",
        "api": "ragd_vault/__init__.py",
        "depends": ["ragd", "ragd_graph"],
    },
    {
        "name": "ragd",
        "description": "Retrieval-Augmented Generation Daemon (C++/HTTP)",
        "status_check": "ctest --test-dir ragd/build -Q 2>&1 | tail -1",
        "api": "ragd/include/ragd/api.h",
        "depends": [],
    },
    {
        "name": "domdata",
        "description": "Market data safety layer",
        "status_check": "python domdata/check_no_trading.py 2>&1 | tail -1",
        "api": "domdata/domdata.py",
        "depends": [],
    },
    {
        "name": "research_os",
        "description": "Research ingestion and RAG preparation pipeline",
        "status_check": "python -m pytest -q research_os/tests 2>&1 | tail -1",
        "api": "research_os/cli.py",
        "depends": ["ragd"],
    },
]


def _git_info() -> dict:
    """Get current git branch and commit."""
    info: dict = {"branch": "unknown", "commit": "unknown", "dirty": False}
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False
        ).stdout.strip()
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=3, check=False
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=3, check=False
        ).stdout.strip()
        info["branch"] = branch or "unknown"
        info["commit"] = commit or "unknown"
        info["dirty"] = bool(status)
    except Exception:
        pass
    return info


def _package_exists(name: str, root: Path) -> bool:
    return (root / name).exists()


def _count_active_sessions(store: AgentStore) -> int:
    row = store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_sessions_v2 WHERE status='active'"
    ).fetchone()
    return row["n"] if row else 0


def _count_open_tasks(store: AgentStore) -> int:
    row = store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_tasks WHERE status NOT IN ('done','cancelled')"
    ).fetchone()
    return row["n"] if row else 0


def _count_active_locks(store: AgentStore) -> int:
    row = store.conn.execute(
        "SELECT COUNT(*) as n FROM agent_file_locks WHERE status='active'"
    ).fetchone()
    return row["n"] if row else 0


def refresh_architecture(
    store: Optional[AgentStore] = None,
    root: Optional[str] = None,
    output_path: Optional[str] = None,
) -> dict:
    """Rebuild docs/agents/LIVING_ARCHITECTURE.md from codebase state.

    Returns a dict with: packages_found, packages_missing, output_path, generated_at.
    """
    _store = store or AgentStore()
    workspace_root = Path(root) if root else Path.cwd()
    out_path = Path(output_path) if output_path else workspace_root / _OUTPUT_PATH

    git = _git_info()
    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Agent OS live state
    active_sessions = _count_active_sessions(_store)
    open_tasks = _count_open_tasks(_store)
    active_locks = _count_active_locks(_store)

    # Package scan
    found: list[str] = []
    missing: list[str] = []
    pkg_rows: list[str] = []

    for pkg in _KNOWN_PACKAGES:
        name = pkg["name"]
        exists = _package_exists(name, workspace_root)
        if exists:
            found.append(name)
            pkg_rows.append(
                f"| `{name}` | {pkg['description']} | ✅ present | "
                f"`{pkg['api']}` | {', '.join(pkg['depends']) or 'none'} |"
            )
        else:
            missing.append(name)
            pkg_rows.append(
                f"| `{name}` | {pkg['description']} | ❌ missing | "
                f"`{pkg['api']}` | {', '.join(pkg['depends']) or 'none'} |"
            )

    # Complexity summary
    complexity_rows: list[str] = []
    try:
        reports = all_packages_report(root=str(workspace_root))
        for r in reports:
            status_icon = "⚠️" if r.over_budget else "✅"
            complexity_rows.append(
                f"| `{r.package}` | {r.score} | {r.budget} | {status_icon} |"
            )
    except Exception as e:
        complexity_rows.append(f"| (error) | — | — | complexity scan failed: {e} |")

    # Agent OS status
    lock_rows = _store.conn.execute(
        "SELECT filepath, session_id, mode FROM agent_file_locks WHERE status='active' LIMIT 10"
    ).fetchall()
    lock_section = "\n".join(
        f"- `{r['filepath']}` [{r['mode']}] → `{r['session_id']}`"
        for r in lock_rows
    ) or "*(no active locks)*"

    task_rows = _store.conn.execute(
        "SELECT task_id, title, status, priority FROM agent_tasks "
        "WHERE status NOT IN ('done','cancelled') ORDER BY priority, created_at LIMIT 10"
    ).fetchall()
    task_section = "\n".join(
        f"- [{r['task_id']}] P{r['priority']} `{r['status']}` — {r['title']}"
        for r in task_rows
    ) or "*(no open tasks)*"

    content = f"""# Living Architecture — Dominion Agent OS

*Auto-generated: {now_ts}*
*git: `{git['branch']}` @ `{git['commit']}`{"  *(dirty)*" if git['dirty'] else ""}*

> This document is generated from codebase scan + live Agent OS state.
> Do NOT manually edit — run `dominion agent architecture refresh` to update.

---

## Agent OS Live State

| Metric | Value |
|---|---|
| Active Sessions | {active_sessions} |
| Open Tasks | {open_tasks} |
| Active File Locks | {active_locks} |

---

## Open Tasks

{task_section}

---

## Active File Locks

{lock_section}

---

## Package Registry

| Package | Description | Status | Primary API | Depends On |
|---|---|---|---|---|
{chr(10).join(pkg_rows)}

---

## Complexity Budgets

| Package | Score | Budget | Status |
|---|---|---|---|
{chr(10).join(complexity_rows)}

---

## Data Flows

```
domdata/ ──────────────────► safety scanner
dominion_loader/ ──────────► file manifest ──► dominion_ai/
ragd/ ─────────────────────► HTTP API ──────► dominion_ai/
dominion_ai/ ──────────────► RAGD queries ──► scripts/dominion_cli.py
dominion_agent/ ───────────► control plane ─► all agents
research_os/ ──────────────► ingestion ─────► ragd/
ragd_chunker/ ─────────────► AST chunks ────► ragd/
ragd_embed/ ───────────────► embeddings ────► ragd_hnsw/
ragd_vault/ ───────────────► Obsidian notes ◄ ragd/
```

---

## DB Stores

| Database | Path | Engine |
|---|---|---|
| Manifest | `~/.dominion/manifest.db` | SQLite WAL |
| Agent OS | `~/.dominion/agent_os.db` | SQLite WAL |
| Dominion Main | `data/dominion.duckdb` | DuckDB |

---

## Key Contracts

- `docs/agents/SHARED_INTERFACE_CONTRACT.md` — shared interface rules
- `docs/agents/AGENT_OS_CONTRACT.md` — Agent OS guarantees
- `AGENTS.md` — all active agents and their roles

---

## Missing Packages

{chr(10).join(f'- `{m}` — not yet initialized' for m in missing) or '*(all packages present)*'}

---

*Regenerate with: `dominion agent architecture refresh`*
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    if store is None:
        _store.close()

    return {
        "packages_found": found,
        "packages_missing": missing,
        "output_path": str(out_path),
        "generated_at": now_ts,
        "active_sessions": active_sessions,
        "open_tasks": open_tasks,
        "active_locks": active_locks,
    }


def show_architecture(root: Optional[str] = None) -> Optional[str]:
    """Return contents of the living architecture document, or None if missing."""
    workspace_root = Path(root) if root else Path.cwd()
    out_path = workspace_root / _OUTPUT_PATH
    if out_path.exists():
        return out_path.read_text(encoding="utf-8")
    return None
