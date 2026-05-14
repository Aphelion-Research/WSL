"""Safety filters for Dominion Agent OS.

Prevents secret access, forbidden trading tasks, and credential leakage.
All agent OS operations must pass through relevant safety checks.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dominion_agent.types import SafetyResult

# ---------------------------------------------------------------------------
# Secret path detection
# ---------------------------------------------------------------------------

_SECRET_DIR_COMPONENTS: frozenset[str] = frozenset({
    "secrets",
    ".secrets",
    "credentials",
    ".credentials",
})

_SECRET_FILE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"secrets[/\\]", re.IGNORECASE),
    re.compile(r"mt5\.env", re.IGNORECASE),
    re.compile(r"\.env$"),
    re.compile(r"\.key$"),
    re.compile(r"\.pem$"),
    re.compile(r"\.pfx$"),
    re.compile(r"\.p12$"),
    re.compile(r"_secret[_.]"),
    re.compile(r"_credential[_.]"),
    re.compile(r"_password[_.]"),
    re.compile(r"_token[_.]"),
    re.compile(r"private_key"),
    re.compile(r"id_rsa"),
    re.compile(r"id_ed25519"),
]


def is_secret_path(path: str) -> bool:
    """Return True if the path references a secrets directory or credential file."""
    p = Path(path)
    # Check directory components
    for part in p.parts[:-1]:  # exclude filename — checked separately below
        if part.lower() in _SECRET_DIR_COMPONENTS:
            return True
    # Also check the full path for the secrets/ pattern (works for both relative and absolute)
    path_str = str(path)
    if _SECRET_FILE_PATTERNS[0].search(path_str):  # secrets[/\] — check full path
        return True
    if _SECRET_FILE_PATTERNS[1].search(path_str):  # mt5\.env — check full path
        return True
    # For remaining patterns, only match against the filename to avoid false positives
    fname = p.name
    for pat in _SECRET_FILE_PATTERNS[2:]:
        if pat.search(fname):
            return True
    return False


def redact_path(path: str) -> str:
    """Return a safe version of the path for logging/prompts.

    Replaces secrets paths with a redacted placeholder.
    """
    if is_secret_path(path):
        p = Path(path)
        return f"[REDACTED/{p.suffix or 'file'}]"
    return path


# ---------------------------------------------------------------------------
# Forbidden trading task detection
# ---------------------------------------------------------------------------

_FORBIDDEN_TRADING_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"order[_\s]*send", re.IGNORECASE),
    re.compile(r"order[_\s]*open", re.IGNORECASE),
    re.compile(r"order[_\s]*close", re.IGNORECASE),
    re.compile(r"order[_\s]*modify", re.IGNORECASE),
    re.compile(r"order[_\s]*delete", re.IGNORECASE),
    re.compile(r"position[_\s]*open", re.IGNORECASE),
    re.compile(r"position[_\s]*close", re.IGNORECASE),
    re.compile(r"execute[_\s]*trade", re.IGNORECASE),
    re.compile(r"live[_\s]*trading", re.IGNORECASE),
    re.compile(r"place[_\s]*order", re.IGNORECASE),
    re.compile(r"send[_\s]*order", re.IGNORECASE),
    re.compile(r"buy[_\s]*market", re.IGNORECASE),
    re.compile(r"sell[_\s]*market", re.IGNORECASE),
    re.compile(r"mt5[_\s]*order", re.IGNORECASE),
    re.compile(r"metatrader.*buy", re.IGNORECASE),
    re.compile(r"metatrader.*sell", re.IGNORECASE),
]

_FORBIDDEN_TRADING_PHRASES: list[str] = [
    "add execution",
    "implement trading",
    "enable trading",
    "enable live trading",
    "connect to broker",
    "submit order",
    "fill order",
    "market order",
    "limit order to execute",
    "read secrets/mt5.env",
    "print credentials",
    "log credentials",
    "disable domdata scanner",
    "bypass domdata",
    "index secrets",
    "read mt5.env",
]


def is_forbidden_trading_task(text: str) -> bool:
    """Return True if the text describes a forbidden live trading operation."""
    lower = text.lower()
    for phrase in _FORBIDDEN_TRADING_PHRASES:
        if phrase in lower:
            return True
    for pat in _FORBIDDEN_TRADING_PATTERNS:
        if pat.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Task payload validation
# ---------------------------------------------------------------------------

_DANGEROUS_TERMS: list[str] = [
    "rm -rf",
    "drop table",
    "truncate table",
    "delete from",
    "git reset --hard",
    "git push --force",
    "chmod 777",
    "sudo rm",
]


def validate_task_payload(payload: dict[str, Any]) -> SafetyResult:
    """Validate a task creation or update payload for safety violations.

    Returns SafetyResult with ok=False and violations if any checks fail.
    """
    violations: list[str] = []
    redacted: dict[str, Any] = {}

    title = payload.get("title", "")
    description = payload.get("description", "")
    scope_files = payload.get("scope_files", [])

    # Check for forbidden trading content
    for field_name, value in [("title", title), ("description", description)]:
        if isinstance(value, str) and is_forbidden_trading_task(value):
            violations.append(
                f"SAFETY: '{field_name}' contains forbidden trading operation: {value[:80]}"
            )

    # Check scope files for secrets
    redacted_files = []
    for f in scope_files:
        if isinstance(f, str) and is_secret_path(f):
            violations.append(f"SAFETY: scope file references secrets path: {redact_path(f)}")
            redacted_files.append(redact_path(f))
        else:
            redacted_files.append(f)

    # Check dangerous terms in title and description
    for text in (title, description):
        if not isinstance(text, str):
            continue
        lower_text = text.lower()
        for term in _DANGEROUS_TERMS:
            if term in lower_text and not payload.get("dangerous"):
                violations.append(
                    f"SAFETY: task contains destructive term '{term}' "
                    "without --dangerous flag. Add 'dangerous: true' to payload if intentional."
                )

    # Check title not empty
    if not title or not title.strip():
        violations.append("SAFETY: task title must not be empty")

    # Build redacted payload
    redacted = {**payload, "scope_files": redacted_files}

    return SafetyResult(
        ok=len(violations) == 0,
        violations=violations,
        redacted_payload=redacted,
    )
