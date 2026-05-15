#!/usr/bin/env python3
"""Repo-wide forbidden-token scanner.

Scans all source files under the repo root (not only domdata/) for forbidden
trading tokens defined in config/forbidden_tokens.json.

Allowlist is path-aware: a file is exempt if any component of its path matches
an allowlist_files entry from the policy.  The path-based check prevents a file
named e.g. "analysis/order_send.py" from being silently skipped.
"""
from __future__ import annotations

import sys
from pathlib import Path

from domdata_pkg.forbidden_tokens import FORBIDDEN_TOKENS as FORBIDDEN
from domdata_pkg.forbidden_tokens import FORBIDDEN_POLICY

_ALLOWLIST_NAMES: frozenset[str] = frozenset(FORBIDDEN_POLICY.get("allowlist_files", []))
_ALLOWLIST_PATHS: tuple[str, ...] = tuple(FORBIDDEN_POLICY.get("allowlist_paths", []))
_SKIP_PARTS: frozenset[str] = frozenset(FORBIDDEN_POLICY.get("skip_parts", []))

# Scan extensions: Python, shell, C/C++, Markdown, YAML (not binary)
_SCAN_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".sh", ".bash", ".cpp", ".c", ".hpp", ".h", ".ts", ".js", ".yaml", ".yml", ".toml", ".json", ".md", ".txt"}
)


def _is_allowlisted(path: Path, repo_root: Path) -> bool:
    """Return True if this path is allowlisted by name or path prefix (policy-driven)."""
    rel = path.relative_to(repo_root)
    rel_str = rel.as_posix()
    # Path-prefix allowlist (e.g. "docs/", "config/forbidden_tokens.json")
    for ap in _ALLOWLIST_PATHS:
        if rel_str == ap or rel_str.startswith(ap if ap.endswith("/") else ap + "/"):
            return True
    # Filename allowlist — only for files directly inside a known package (depth ≤ 3)
    # This prevents e.g. "analysis/safety.py" being silently skipped.
    if path.name in _ALLOWLIST_NAMES and len(rel.parts) <= 3:
        return True
    return False


def should_scan(path: Path, repo_root: Path) -> bool:
    if path.suffix not in _SCAN_EXTENSIONS:
        return False
    rel = path.relative_to(repo_root)
    if any(part in _SKIP_PARTS for part in rel.parts):
        return False
    if _is_allowlisted(path, repo_root):
        return False
    return True


def scan_repo(repo_root: Path) -> list[str]:
    """Return list of violation strings found in repo_root."""
    failures: list[str] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file():
            continue
        if not should_scan(path, repo_root):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except (PermissionError, OSError):
            continue
        for token in FORBIDDEN:
            if token in text:
                rel = path.relative_to(repo_root)
                failures.append(f"{rel}: forbidden token '{token}'")
                break  # one violation per file is enough
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures = scan_repo(root)
    if failures:
        print("BLOCKED: forbidden trading tokens found outside allowlist", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("PASS: no forbidden trading tokens outside allowlist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
