"""Formatting helpers for Dominion Agent OS.

Provides dict converters and JSON output helpers.
"""
from __future__ import annotations

import json
import time
from typing import Any

from dominion_agent.types import (
    ClaimResult,
    ComplexityReport,
    ConflictReport,
    FileLock,
    ImpactReport,
    PromptCompilation,
    ReviewReport,
    Session,
    Task,
)


def _ts(epoch: int | None) -> str | None:
    if epoch is None:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

def session_to_dict(s: Session) -> dict:
    return {
        "session_id": s.session_id,
        "agent_name": s.agent_name,
        "role": s.role,
        "status": s.status,
        "started_at": _ts(s.started_at),
        "ended_at": _ts(s.ended_at),
        "last_heartbeat": _ts(s.last_heartbeat),
        "git_branch": s.git_branch,
        "git_commit_start": s.git_commit_start,
        "git_commit_end": s.git_commit_end,
        "parent_session_id": s.parent_session_id,
        "metadata": s.metadata,
    }


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

def task_to_dict(t: Task) -> dict:
    return {
        "task_id": t.task_id,
        "title": t.title,
        "description": t.description,
        "kind": t.kind,
        "priority": t.priority,
        "status": t.status,
        "created_at": _ts(t.created_at),
        "updated_at": _ts(t.updated_at),
        "claimed_by_session": t.claimed_by_session,
        "parent_task_id": t.parent_task_id,
        "scope": t.scope,
        "validation": t.validation,
        "acceptance": t.acceptance,
        "risk": t.risk,
        "tags": t.tags,
        "evidence": t.evidence,
    }


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

def claim_to_dict(c: ClaimResult) -> dict:
    return {
        "claim_id": c.claim_id,
        "task_id": c.task_id,
        "session_id": c.session_id,
        "status": c.status,
        "claimed_at": _ts(c.claimed_at),
        "released_at": _ts(c.released_at),
        "note": c.note,
    }


# ---------------------------------------------------------------------------
# FileLock
# ---------------------------------------------------------------------------

def lock_to_dict(l: FileLock) -> dict:
    return {
        "lock_id": l.lock_id,
        "filepath": l.filepath,
        "session_id": l.session_id,
        "task_id": l.task_id,
        "mode": l.mode,
        "status": l.status,
        "locked_at": _ts(l.locked_at),
        "released_at": _ts(l.released_at),
        "expires_at": _ts(l.expires_at),
        "note": l.note,
    }


# ---------------------------------------------------------------------------
# ConflictReport
# ---------------------------------------------------------------------------

def conflict_report_to_dict(r: ConflictReport) -> dict:
    return {
        "status": r.status,
        "risk": r.risk,
        "recommended_action": r.recommended_action,
        "conflicts": [
            {
                "type": c.type,
                "filepath": c.filepath,
                "owner_session": c.owner_session,
                "severity": c.severity,
                "remedy": c.remedy,
                "details": c.details,
            }
            for c in r.conflicts
        ],
    }


# ---------------------------------------------------------------------------
# ImpactReport
# ---------------------------------------------------------------------------

def impact_report_to_dict(r: ImpactReport) -> dict:
    return {
        "files": r.files,
        "risk": r.risk,
        "affected_packages": r.affected_packages,
        "likely_tests": r.likely_tests,
        "required_commands": r.required_commands,
        "optional_commands": r.optional_commands,
        "reasoning": r.reasoning,
    }


# ---------------------------------------------------------------------------
# ReviewReport
# ---------------------------------------------------------------------------

def review_report_to_dict(r: ReviewReport) -> dict:
    return {
        "review_id": r.review_id,
        "task_id": r.task_id,
        "verdict": r.verdict,
        "score": r.score,
        "summary": r.summary,
        "commands": r.commands,
        "findings": [
            {
                "severity": f.severity,
                "type": f.type,
                "message": f.message,
                "remedy": f.remedy,
            }
            for f in r.findings
        ],
    }


# ---------------------------------------------------------------------------
# ComplexityReport
# ---------------------------------------------------------------------------

def complexity_report_to_dict(r: ComplexityReport) -> dict:
    return {
        "package": r.package,
        "score": r.score,
        "budget": r.budget,
        "over_budget": r.over_budget,
        "warnings": r.warnings,
        "remediation": r.remediation,
        "metrics": {
            "file_count": r.metrics.file_count,
            "public_symbol_count": r.metrics.public_symbol_count,
            "cli_command_count": r.metrics.cli_command_count,
            "test_count": r.metrics.test_count,
            "todo_count": r.metrics.todo_count,
            "temp_adapter_count": r.metrics.temp_adapter_count,
            "broad_except_count": r.metrics.broad_except_count,
            "untested_module_count": r.metrics.untested_module_count,
            "large_file_penalty": r.metrics.large_file_penalty,
            "average_file_lines": r.metrics.average_file_lines,
            "largest_file_lines": r.metrics.largest_file_lines,
        },
    }


# ---------------------------------------------------------------------------
# PromptCompilation
# ---------------------------------------------------------------------------

def compilation_to_dict(c: PromptCompilation) -> dict:
    return {
        "compilation_id": c.compilation_id,
        "task_id": c.task_id,
        "target_agent": c.target_agent,
        "created_at": _ts(c.created_at),
        "prompt_hash": c.prompt_hash,
        "context_summary": c.context_summary,
        "included_files": c.included_files,
        "validation": c.validation,
        "output_path": c.output_path,
    }


# ---------------------------------------------------------------------------
# Generic JSON output
# ---------------------------------------------------------------------------

def format_json_output(data: Any, pretty: bool = True) -> str:
    return json.dumps(data, indent=2 if pretty else None, default=str)
