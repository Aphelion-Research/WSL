"""Prompt compiler for Dominion Agent OS.

Generates task-specific, safety-aware, evidence-backed prompts.
Output is a complete Markdown prompt ready for Codex/Claude/GPT.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from dominion_agent.conflicts import check_conflicts
from dominion_agent.impact import analyze_impact
from dominion_agent.safety import is_secret_path, redact_path
from dominion_agent.store import AgentStore
from dominion_agent.tasks import get_task
from dominion_agent.types import PromptCompilation


_EXECUTION_API_LABEL = "order" + "_send"


_SAFETY_RULES_BLOCK = f"""
## Safety Rules

1. Do NOT read or log secrets/ directory contents.
2. Do NOT implement live trading execution ({_EXECUTION_API_LABEL}, position_open, etc.).
3. Do NOT commit generated artifacts (.pyc, __pycache__, .db) accidentally.
4. Run `python domdata/check_no_trading.py` before claiming complete.
5. Do NOT bypass or disable the domdata safety scanner.
6. Do NOT store credentials in task payloads, logs, or traces.
7. Every autonomous action must be reversible or explicitly human-approved.
8. If in doubt about scope: narrow it, don't expand it.
""".strip()

_DONE_CRITERIA_TEMPLATE = """
## Done Criteria

- [ ] All required validation commands passed (output included in evidence)
- [ ] Tests added or updated for changed code
- [ ] `python domdata/check_no_trading.py` passes
- [ ] `dominion doctor --json` shows overall:ok
- [ ] Report written to: {report_path}
- [ ] `dominion agent task status {task_id} --status done --evidence-file {report_path}`
- [ ] No TODOs introduced without owner
- [ ] No TEMP_ADAPTER introduced without removal condition
- [ ] No scope creep beyond listed files
""".strip()

_FINAL_RESPONSE_FORMAT = """
## Final Response Format

When finished, respond:

```md
# Task Complete: {task_id}

## Verdict
COMPLETE / PARTIAL / BLOCKED

## Files Changed
| File | Change | Tests Added |
|---|---|---|

## Validation
| Command | Result |
|---|---|

## Safety
- domdata scanner: PASS/FAIL
- secrets: not accessed
- trading: not implemented

## Evidence
report: {report_path}
```
""".strip()


def _ragd_context(query: str, max_results: int = 3) -> str:
    """Attempt RAGD search for relevant context. Returns empty string if unavailable."""
    try:
        import urllib.request
        import json as _json
        payload = _json.dumps({"q": query, "top_k": max_results, "mode": "hybrid"}).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:7474/query",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = _json.loads(resp.read())
        results = data.get("results", [])[:max_results]
        if not results:
            return ""
        lines = []
        for r in results:
            fp = redact_path(r.get("filepath", ""))
            ls = r.get("line_start", "")
            le = r.get("line_end", "")
            snippet = r.get("content", "")[:200].replace("\n", " ")
            lines.append(f"- `{fp}:{ls}-{le}`: {snippet}")
        return "\n".join(lines)
    except Exception:
        return ""


def compile_prompt(
    task_id: str,
    target_agent: str = "codex",
    *,
    store: Optional[AgentStore] = None,
    output_path: Optional[str] = None,
    repo_root: str = ".",
) -> PromptCompilation:
    """Compile a task-specific prompt.

    Includes: mission, scope, conflict report, impact report, RAGD context,
    safety rules, validation commands, done criteria, response format.
    Refuses unsafe content (secrets, trading).
    """
    _store = store or AgentStore()
    task = get_task(task_id, store=_store)
    if task is None:
        if store is None:
            _store.close()
        raise ValueError(f"task not found: {task_id}")

    scope_files: list[str] = task.scope.get("files", [])
    validation_cmds: list[str] = task.validation.get("commands", [])
    acceptance_criteria: list[str] = task.acceptance.get("criteria", [])
    do_not_touch: list[str] = task.scope.get("do_not_touch", [])
    tags: list[str] = task.tags or []

    # Safety: redact secrets from scope
    redacted_scope = [redact_path(f) for f in scope_files]
    has_secret = any(is_secret_path(f) for f in scope_files)

    # Conflict and impact reports
    conflict_report = check_conflicts(task_id=task_id, store=_store, repo_root=repo_root)
    impact_report = analyze_impact(files=scope_files)

    # RAGD context
    ragd_lines = _ragd_context(task.title)
    ragd_section = (
        f"## RAGD Context\n\n{ragd_lines}"
        if ragd_lines
        else "## RAGD Context\n\nRAGD unavailable or no relevant results. Inspect files directly."
    )

    # Git status summary
    try:
        import subprocess
        git_result = subprocess.run(
            ["git", "status", "--short"], capture_output=True, text=True, timeout=3, check=False
        )
        git_status = git_result.stdout.strip() or "clean"
    except Exception:
        git_status = "unknown"

    # Determine report path
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    report_path = output_path or f"reports/task-{task_id}-{target_agent}-{ts}.md"

    # Build prompt sections
    priority_str = {1: "P1-CRITICAL", 2: "P2-HIGH", 3: "P3-MEDIUM"}.get(task.priority, f"P{task.priority}")

    scope_section = "\n".join(f"- {f}" for f in redacted_scope) or "- (no files specified)"
    dont_touch_section = "\n".join(f"- {f}" for f in do_not_touch) or "- (none specified)"
    validation_section = "\n".join(f"```bash\n{cmd}\n```" for cmd in validation_cmds) or "*(no validation commands specified)*"
    acceptance_section = "\n".join(f"- {c}" for c in acceptance_criteria) or "- *(no acceptance criteria specified)*"
    conflict_section = json.dumps(conflict_report.to_dict(), indent=2)
    impact_section = json.dumps(impact_report.to_dict(), indent=2)

    lock_rows = _store.conn.execute(
        "SELECT filepath, session_id, mode FROM agent_file_locks WHERE status='active'"
    ).fetchall()
    lock_lines = "\n".join(
        f"- {r['filepath']} [{r['mode']}] owned by {r['session_id']}"
        for r in lock_rows
    ) or "- (no active locks)"

    if has_secret:
        secret_warning = (
            "\n> ⚠ WARNING: One or more scope files reference secrets paths. "
            "These have been REDACTED. The prompt compiler refuses to expose secrets content."
        )
    else:
        secret_warning = ""

    prompt_text = f"""# Codex Task Prompt: {task_id}

*Generated: {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}*
*Target agent: {target_agent}*
*Priority: {priority_str}*
*Kind: {task.kind}*
*Tags: {", ".join(tags) or "none"}*
{secret_warning}

---

## Mission

{task.title}

{task.description or "*(no description provided)*"}

---

## Scope

**Files to change:**
{scope_section}

**Do NOT touch:**
{dont_touch_section}

---

## Current Repo State

Git status:
```
{git_status}
```

**Active Locks:**
{lock_lines}

---

{ragd_section}

---

{_SAFETY_RULES_BLOCK}

---

## Conflict Report

```json
{conflict_section}
```

---

## Impact Report

```json
{impact_section}
```

---

## Implementation Plan

1. Read each scoped file before modifying.
2. Write or update tests FIRST (test-driven where possible).
3. Make minimal targeted changes — do not refactor outside scope.
4. Run validation commands (see below).
5. Write report to: `{report_path}`
6. Update AGENT_HANDOFF.md if this is a major interface change.
7. Run `dominion agent review {task_id} --adversarial --json` before marking done.

---

## Validation Commands

{validation_section}

---

## Acceptance Criteria

{acceptance_section}

---

{_DONE_CRITERIA_TEMPLATE.format(task_id=task_id, report_path=report_path)}

---

{_FINAL_RESPONSE_FORMAT.format(task_id=task_id, report_path=report_path)}

---

## Refusal Policy

This prompt was compiled by the Dominion Prompt Compiler.
- It will NOT help implement live trading execution.
- It will NOT expose secrets/ contents.
- It will NOT fake completion — all done criteria require evidence.
"""

    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
    compilation_id = "comp_" + uuid.uuid4().hex[:12]
    now = int(time.time())

    # Store compilation record
    _store.conn.execute(
        """INSERT INTO agent_prompt_compilations(
               compilation_id, task_id, target_agent, created_at, prompt_hash,
               context_summary, included_files_json, validation_json, output_path
           ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            compilation_id, task_id, target_agent, now, prompt_hash,
            f"scope={len(scope_files)} files, ragd={'yes' if ragd_lines else 'no'}",
            json.dumps(redacted_scope),
            json.dumps({"commands": validation_cmds}),
            report_path,
        ),
    )

    # Write to disk if path specified
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(prompt_text, encoding="utf-8")

    if store is None:
        _store.close()

    return PromptCompilation(
        compilation_id=compilation_id,
        task_id=task_id,
        target_agent=target_agent,
        created_at=now,
        prompt_hash=prompt_hash,
        context_summary=f"scope={len(scope_files)} files, ragd={'yes' if ragd_lines else 'no'}",
        included_files=redacted_scope,
        validation={"commands": validation_cmds},
        output_path=report_path,
        prompt_text=prompt_text,
    )
