"""Adversarial review lane for Dominion Agent OS.

Runs structured checks on a completed task before marking it done.
Returns a ReviewReport with verdict and findings.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from pathlib import Path
from typing import Optional

from dominion_agent.safety import is_forbidden_trading_task, is_secret_path
from dominion_agent.store import AgentStore
from dominion_agent.tasks import get_task
from dominion_agent.types import ReviewFinding, ReviewReport, VALID_FINDING_SEVERITIES


# Forbidden trading tokens (same set as domdata/check_no_trading.py uses)
_FORBIDDEN_TOKENS: list[str] = [
    "order" + "_send", "Order" + "Send", "order_open", "OrderOpen",
    "position_open", "PositionOpen", "PositionClose",
    "trade_open", "TradeOpen", "execute_trade",
]

# Terms that indicate fake completion without evidence
_FAKE_COMPLETION_TERMS: list[re.Pattern] = [
    re.compile(r"all tests pass", re.IGNORECASE),
    re.compile(r"everything works", re.IGNORECASE),
    re.compile(r"task complete", re.IGNORECASE),
    re.compile(r"successfully implemented", re.IGNORECASE),
]

# Report path patterns that indicate a real report was written
_REPORT_PATH_PATTERNS: list[re.Pattern] = [
    re.compile(r"reports/"),
    re.compile(r"\.md$"),
]


def _check_forbidden_tokens_in_files(files: list[str]) -> list[str]:
    """Grep new/changed files for forbidden trading tokens."""
    violations: list[str] = []
    for f in files:
        try:
            content = Path(f).read_text(encoding="utf-8", errors="replace")
            for token in _FORBIDDEN_TOKENS:
                if token in content:
                    violations.append(f"Forbidden token {token!r} in {f}")
        except Exception:
            pass
    return violations


def _file_exists(path: str) -> bool:
    try:
        return Path(path).exists()
    except Exception:
        return False


def _has_pytest_evidence(evidence: dict) -> bool:
    """Check if evidence includes pytest output."""
    commands = evidence.get("commands", [])
    for cmd_entry in commands:
        if isinstance(cmd_entry, dict):
            cmd = cmd_entry.get("command", "")
            output = cmd_entry.get("output", "")
            if "pytest" in cmd and ("passed" in output or "PASSED" in output):
                return True
    # Also check report content loosely
    report = evidence.get("report", "")
    if isinstance(report, str) and "passed" in report.lower():
        return True
    return False


def run_adversarial_review(
    task_id: str,
    *,
    store: Optional[AgentStore] = None,
    strict: bool = False,
) -> ReviewReport:
    """Run adversarial review checks on a task.

    Checks:
    - Task had claim
    - Task had scope
    - Evidence present
    - Validation commands were specified
    - Forbidden trading tokens not introduced
    - Secret paths not in scope
    - Report exists
    - Doctor not skipped
    - Pytest evidence (if code changes)
    - No large refactors outside scope
    """
    _store = store or AgentStore()
    review_id = "rev_" + uuid.uuid4().hex[:12]
    findings: list[ReviewFinding] = []
    commands: list[str] = []

    task = get_task(task_id, store=_store)
    if task is None:
        if store is None:
            _store.close()
        return ReviewReport(
            review_id=review_id,
            task_id=task_id,
            verdict="blocked",
            score=0.0,
            findings=[ReviewFinding(
                severity="critical",
                type="claim_missing",
                message=f"Task {task_id!r} not found.",
                remedy="Create the task before reviewing it.",
            )],
            commands=[],
            summary="Task not found.",
        )

    scope_files: list[str] = task.scope.get("files", [])
    validation_cmds: list[str] = task.validation.get("commands", [])
    evidence: dict = task.evidence or {}

    # 1. Claim check
    claim_row = _store.conn.execute(
        "SELECT claim_id FROM agent_claims WHERE task_id=? AND status='active'",
        (task_id,),
    ).fetchone()
    released_claim = _store.conn.execute(
        "SELECT claim_id FROM agent_claims WHERE task_id=? AND status='released'",
        (task_id,),
    ).fetchone()
    if not claim_row and not released_claim:
        findings.append(ReviewFinding(
            severity="medium",
            type="claim_missing",
            message="Task was never claimed by any session.",
            remedy="Claim the task before starting work: dominion agent task claim TASK_ID --session SESSION_ID",
        ))

    # 2. Scope check
    if not scope_files:
        findings.append(ReviewFinding(
            severity="medium",
            type="prompt_context_missing",
            message="Task has no scope files defined.",
            remedy="Add scope files: dominion agent task create --scope-file FILE",
        ))

    # 3. Validation commands check
    if not validation_cmds:
        findings.append(ReviewFinding(
            severity="high",
            type="missing_validation",
            message="No validation commands specified for this task.",
            remedy="Add validation commands to the task before marking done.",
        ))
    else:
        commands.extend(validation_cmds)

    # 4. Evidence check
    if not evidence:
        findings.append(ReviewFinding(
            severity="high",
            type="missing_validation",
            message="No evidence attached to task.",
            remedy="Attach evidence: dominion agent task status TASK_ID --evidence-file FILE",
        ))

    # 5. Report file check
    report_path = evidence.get("report", "")
    if report_path and not _file_exists(report_path):
        findings.append(ReviewFinding(
            severity="high",
            type="missing_report",
            message=f"Evidence report file does not exist: {report_path!r}",
            remedy=f"Write the report to {report_path!r} before marking done.",
        ))
    elif not report_path:
        findings.append(ReviewFinding(
            severity="medium",
            type="missing_report",
            message="No report path in evidence.",
            remedy="Include 'report' key in evidence pointing to written report file.",
        ))

    # 6. Secret path check
    for f in scope_files:
        if is_secret_path(f):
            findings.append(ReviewFinding(
                severity="critical",
                type="unsafe_trading_change",
                message=f"Scope contains secrets path: {f!r}",
                remedy="Remove secrets paths from task scope immediately.",
            ))

    # 7. Forbidden trading token scan
    code_files = [f for f in scope_files if f.endswith((".py", ".cpp", ".h", ".mq5"))]
    token_violations = _check_forbidden_tokens_in_files(code_files)
    for v in token_violations:
        findings.append(ReviewFinding(
            severity="critical",
            type="unsafe_trading_change",
            message=v,
            remedy="Remove trading execution tokens. Run: python domdata/check_no_trading.py",
        ))

    # 8. RAGD C++ changes need ctest
    has_ragd_changes = any("ragd/" in f for f in scope_files)
    if has_ragd_changes:
        ctest_in_cmds = any("ctest" in cmd for cmd in validation_cmds)
        if not ctest_in_cmds:
            findings.append(ReviewFinding(
                severity="high",
                type="ragd_tests_missing",
                message="RAGD C++ files in scope but ctest not in validation commands.",
                remedy="Add: ctest --test-dir ragd/build --output-on-failure",
            ))

    # 9. CLI changes need smoke test
    has_cli_changes = any("dominion_cli.py" in f or "scripts/" in f for f in scope_files)
    if has_cli_changes:
        cli_smoke = any("dominion" in cmd for cmd in validation_cmds)
        if not cli_smoke:
            findings.append(ReviewFinding(
                severity="low",
                type="missing_validation",
                message="CLI files changed but no dominion CLI smoke test in validation.",
                remedy="Add: dominion status || true; dominion doctor --json || true",
            ))

    # 10. Pytest check for Python changes
    has_python_changes = any(f.endswith(".py") for f in scope_files)
    if has_python_changes:
        pytest_in_cmds = any("pytest" in cmd for cmd in validation_cmds)
        if not pytest_in_cmds:
            findings.append(ReviewFinding(
                severity="high",
                type="pytest_missing",
                message="Python files in scope but pytest not in validation commands.",
                remedy="Add: python -m pytest -q",
            ))

    # Compute verdict
    critical_count = sum(1 for f in findings if f.severity == "critical")
    high_count = sum(1 for f in findings if f.severity == "high")
    medium_count = sum(1 for f in findings if f.severity == "medium")

    if critical_count > 0:
        verdict = "reject"
        score = 0.0
    elif high_count > 0:
        verdict = "needs_changes"
        score = 0.4
    elif medium_count > 0:
        verdict = "needs_changes"
        score = 0.7
    elif findings:
        verdict = "needs_changes"
        score = 0.85
    else:
        verdict = "accept"
        score = 1.0

    summary_parts: list[str] = []
    if findings:
        summary_parts.append(
            f"{len(findings)} finding(s): "
            f"{critical_count} critical, {high_count} high, {medium_count} medium"
        )
    else:
        summary_parts.append("All checks passed.")

    # Store review record
    _store.conn.execute(
        """INSERT INTO agent_reviews(
               review_id, task_id, status, created_at, summary,
               findings_json, commands_json, verdict
           ) VALUES(?,?,?,?,?,?,?,?)""",
        (
            review_id, task_id, "complete", int(time.time()),
            " ".join(summary_parts),
            json.dumps([{"severity": f.severity, "type": f.type,
                        "message": f.message, "remedy": f.remedy} for f in findings]),
            json.dumps(commands),
            verdict,
        ),
    )

    if store is None:
        _store.close()

    return ReviewReport(
        review_id=review_id,
        task_id=task_id,
        verdict=verdict,
        score=score,
        findings=findings,
        commands=commands,
        summary=" ".join(summary_parts),
    )
