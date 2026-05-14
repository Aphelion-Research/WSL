"""Type definitions for Dominion Agent OS.

All public dataclasses used throughout the Agent OS.
INTERFACE(agent-4): v1.0.0 — additive only, no removals without sign-off.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums / constants (frozensets for O(1) membership test)
# ---------------------------------------------------------------------------

VALID_SESSION_STATUSES: frozenset[str] = frozenset({
    "active", "idle", "completed", "failed", "abandoned"
})

VALID_ROLES: frozenset[str] = frozenset({
    "foundation", "retrieval", "truth", "orchestrator",
    "review", "docs", "test", "operator", "unknown",
})

VALID_TASK_STATUSES: frozenset[str] = frozenset({
    "open", "claimed", "in_progress", "review", "done", "blocked", "cancelled"
})

VALID_TASK_KINDS: frozenset[str] = frozenset({
    "bugfix", "feature", "audit", "docs", "test",
    "refactor", "research", "ops", "review",
})

VALID_LOCK_MODES: frozenset[str] = frozenset({"read", "write", "review", "exclusive"})

VALID_REVIEW_VERDICTS: frozenset[str] = frozenset({
    "accept", "reject", "needs_changes", "blocked", "unknown"
})

VALID_FINDING_SEVERITIES: frozenset[str] = frozenset({
    "info", "low", "medium", "high", "critical"
})

# Allowed task status transitions.
# "done" and "cancelled" are terminal without --reopen.
TASK_TRANSITIONS: dict[str, frozenset[str]] = {
    "open":        frozenset({"claimed", "blocked", "cancelled"}),
    "claimed":     frozenset({"in_progress", "blocked", "cancelled", "open"}),
    "in_progress": frozenset({"review", "blocked", "cancelled", "claimed"}),
    "review":      frozenset({"done", "in_progress", "blocked", "cancelled"}),
    "done":        frozenset(),
    "blocked":     frozenset({"open", "claimed", "in_progress", "cancelled"}),
    "cancelled":   frozenset(),
}

# Stale session threshold in seconds
STALE_THRESHOLD_SECONDS: int = 30 * 60  # 30 minutes


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Session:
    session_id: str
    agent_name: str
    role: str
    status: str
    started_at: int
    ended_at: Optional[int]
    last_heartbeat: Optional[int]
    git_branch: str
    git_commit_start: str
    git_commit_end: str
    parent_session_id: str
    metadata: dict

    def is_active(self) -> bool:
        return self.status == "active"

    def is_stale(self, threshold_seconds: int = STALE_THRESHOLD_SECONDS) -> bool:
        import time
        if self.status not in ("active", "idle"):
            return False
        ts = self.last_heartbeat or self.started_at
        return (int(time.time()) - ts) > threshold_seconds


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    description: str
    kind: str
    priority: int
    status: str
    created_at: int
    updated_at: int
    claimed_by_session: str
    parent_task_id: str
    scope: dict          # {"files": [...], "packages": [...]}
    validation: dict     # {"commands": [...]}
    acceptance: dict     # {"criteria": [...]}
    risk: dict           # {"level": "...", "notes": [...]}
    tags: list
    evidence: dict       # {"files": [...], "commands": [...], "report": "..."}


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClaimResult:
    claim_id: str
    task_id: str
    session_id: str
    status: str
    claimed_at: int
    released_at: Optional[int]
    note: str


# ---------------------------------------------------------------------------
# File Locks
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileLock:
    lock_id: str
    filepath: str
    session_id: str
    task_id: str
    mode: str
    status: str
    locked_at: int
    released_at: Optional[int]
    expires_at: Optional[int]
    note: str


@dataclass(frozen=True)
class LockResult:
    lock_id: str
    filepath: str
    session_id: str
    acquired: bool
    conflict_reason: str  # empty string if acquired=True


# ---------------------------------------------------------------------------
# File Touch
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FileTouch:
    touch_id: str
    session_id: str
    task_id: str
    filepath: str
    action: str  # inspect|edit|delete|create|test|review
    touched_at: int
    git_commit: str
    note: str


# ---------------------------------------------------------------------------
# Conflict Report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ConflictItem:
    type: str
    filepath: str
    owner_session: str
    severity: str  # low|medium|high|critical
    remedy: str
    details: str


@dataclass(frozen=True)
class ConflictReport:
    status: str             # pass|warn|fail
    risk: str               # low|medium|high|critical
    conflicts: list[ConflictItem]
    recommended_action: str  # proceed|split_task|wait|request_review|block

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "risk": self.risk,
            "conflicts": [
                {
                    "type": c.type,
                    "filepath": c.filepath,
                    "owner_session": c.owner_session,
                    "severity": c.severity,
                    "remedy": c.remedy,
                    "details": c.details,
                }
                for c in self.conflicts
            ],
            "recommended_action": self.recommended_action,
        }


# ---------------------------------------------------------------------------
# Impact Report
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImpactReport:
    files: list[str]
    risk: str               # low|medium|high|critical
    affected_packages: list[str]
    likely_tests: list[str]
    required_commands: list[str]
    optional_commands: list[str]
    reasoning: list[str]

    def to_dict(self) -> dict:
        return {
            "files": self.files,
            "risk": self.risk,
            "affected_packages": self.affected_packages,
            "likely_tests": self.likely_tests,
            "required_commands": self.required_commands,
            "optional_commands": self.optional_commands,
            "reasoning": self.reasoning,
        }


# ---------------------------------------------------------------------------
# Prompt Compilation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PromptCompilation:
    compilation_id: str
    task_id: str
    target_agent: str
    created_at: int
    prompt_hash: str
    context_summary: str
    included_files: list[str]
    validation: dict
    output_path: str
    prompt_text: str


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ReviewFinding:
    severity: str  # info|low|medium|high|critical
    type: str
    message: str
    remedy: str


@dataclass(frozen=True)
class ReviewReport:
    review_id: str
    task_id: str
    verdict: str   # accept|needs_changes|reject|blocked
    score: float   # 0.0–1.0
    findings: list[ReviewFinding]
    commands: list[str]
    summary: str

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "task_id": self.task_id,
            "verdict": self.verdict,
            "score": round(self.score, 2),
            "findings": [
                {
                    "severity": f.severity,
                    "type": f.type,
                    "message": f.message,
                    "remedy": f.remedy,
                }
                for f in self.findings
            ],
            "commands": self.commands,
            "summary": self.summary,
        }


# ---------------------------------------------------------------------------
# Complexity
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComplexityMetrics:
    file_count: int
    public_symbol_count: int
    cli_command_count: int
    test_count: int
    todo_count: int
    temp_adapter_count: int
    broad_except_count: int
    untested_module_count: int
    large_file_penalty: float
    average_file_lines: float
    largest_file_lines: int
    test_to_source_ratio: float

    def to_dict(self) -> dict:
        return {
            "file_count": self.file_count,
            "public_symbol_count": self.public_symbol_count,
            "cli_command_count": self.cli_command_count,
            "test_count": self.test_count,
            "todo_count": self.todo_count,
            "temp_adapter_count": self.temp_adapter_count,
            "broad_except_count": self.broad_except_count,
            "untested_module_count": self.untested_module_count,
            "large_file_penalty": self.large_file_penalty,
            "average_file_lines": round(self.average_file_lines, 1),
            "largest_file_lines": self.largest_file_lines,
            "test_to_source_ratio": round(self.test_to_source_ratio, 2),
        }


@dataclass(frozen=True)
class ComplexityReport:
    package: str
    score: float
    budget: float
    over_budget: bool
    metrics: ComplexityMetrics
    warnings: list[str]
    remediation: list[str]

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "score": round(self.score, 1),
            "budget": self.budget,
            "over_budget": self.over_budget,
            "metrics": self.metrics.to_dict(),
            "warnings": self.warnings,
            "remediation": self.remediation,
        }


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

@dataclass
class SafetyResult:
    ok: bool
    violations: list[str]
    redacted_payload: dict
