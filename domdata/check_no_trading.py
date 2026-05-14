#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from domdata_pkg.forbidden_tokens import FORBIDDEN_TOKENS as FORBIDDEN

ALLOWLIST = {
    "safety.py",
    "check_no_trading.py",
    "forbidden_tokens.py",
    "test_safety.py",
}

SKIP_PARTS = {"__pycache__", "backups", ".git", ".venv", "data", "logs"}


def should_scan(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    return path.name not in ALLOWLIST


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    failures: list[str] = []
    for path in root.rglob("*.py"):
        if not should_scan(path):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN:
            if token in text:
                rel = path.relative_to(root)
                failures.append(f"{rel}: forbidden token {token}")
    if failures:
        print("BLOCKED: forbidden trading tokens found outside allowlist", file=sys.stderr)
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("PASS: no forbidden trading tokens outside allowlist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
