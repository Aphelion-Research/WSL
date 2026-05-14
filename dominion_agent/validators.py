"""Input validators for Dominion Agent OS.

Validates enums, transitions, and field constraints
before any DB writes or state changes.
"""
from __future__ import annotations

from dominion_agent.types import (
    TASK_TRANSITIONS,
    VALID_LOCK_MODES,
    VALID_ROLES,
    VALID_SESSION_STATUSES,
    VALID_TASK_KINDS,
    VALID_TASK_STATUSES,
)


def validate_session_status(status: str) -> bool:
    return status in VALID_SESSION_STATUSES


def validate_role(role: str) -> bool:
    return role in VALID_ROLES


def validate_task_status(status: str) -> bool:
    return status in VALID_TASK_STATUSES


def validate_task_kind(kind: str) -> bool:
    return kind in VALID_TASK_KINDS


def validate_lock_mode(mode: str) -> bool:
    return mode in VALID_LOCK_MODES


def validate_task_transition(current: str, target: str) -> bool:
    """Return True if transitioning from current to target is allowed."""
    allowed = TASK_TRANSITIONS.get(current, frozenset())
    return target in allowed


def require_nonempty(value: str, field: str) -> None:
    """Raise ValueError if value is empty or whitespace."""
    if not value or not value.strip():
        raise ValueError(f"{field} must not be empty")


def require_enum(value: str, valid: frozenset[str], field: str) -> None:
    """Raise ValueError if value is not in the valid set."""
    if value not in valid:
        raise ValueError(
            f"{field} must be one of {sorted(valid)!r}, got {value!r}"
        )


def require_priority(priority: int) -> None:
    """Raise ValueError if priority is outside 1–10."""
    if not (1 <= priority <= 10):
        raise ValueError(f"priority must be 1–10, got {priority}")
