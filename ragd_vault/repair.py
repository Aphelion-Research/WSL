"""Vault repair: remove stale auto-generated links from SYMBOL_INDEX.md.

Only touches vault/_index/SYMBOL_INDEX.md — never deletes hand-written docs or
any other vault file. All operations default to dry-run.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


_WIKILINK = re.compile(r"\[\[([^]|#]+)(?:#[^]|]+)?(?:\|[^]]+)?\]\]")

_STALE_PREFIXES = (
    "symbols/tmp/",
    "symbols/tmp\\",
)


@dataclass
class RepairReport:
    ok: bool
    vault: str
    dry_run: bool
    stale_removed: int = 0
    stale_examples: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    message: str = ""


def _is_stale_link(target: str) -> bool:
    """Return True for links that reference outside-repo temp paths."""
    for prefix in _STALE_PREFIXES:
        if target.startswith(prefix):
            return True
    # Also catch absolute /tmp/ references that slipped through
    if target.startswith("/tmp/"):
        return True
    return False


def repair_vault(vault_root: Path, *, dry_run: bool = True) -> RepairReport:
    """Strip stale /tmp/ wikilinks from SYMBOL_INDEX.md.

    Args:
        vault_root: Path to the vault directory.
        dry_run:    If True, only report what would change; do not modify files.

    Returns:
        RepairReport describing what was (or would be) changed.
    """
    root = Path(vault_root)
    symbol_index = root / "_index" / "SYMBOL_INDEX.md"

    if not symbol_index.exists():
        return RepairReport(
            ok=True,
            vault=str(root),
            dry_run=dry_run,
            message="SYMBOL_INDEX.md not found; nothing to repair",
        )

    text = symbol_index.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    kept: list[str] = []
    removed: int = 0
    examples: list[str] = []

    for line in lines:
        # Check if this line contains ONLY stale wikilinks (index entry lines)
        matches = _WIKILINK.findall(line)
        if matches and all(_is_stale_link(m.strip()) for m in matches):
            removed += 1
            if len(examples) < 10:
                examples.append(matches[0].strip())
        else:
            kept.append(line)

    report = RepairReport(
        ok=True,
        vault=str(root),
        dry_run=dry_run,
        stale_removed=removed,
        stale_examples=examples,
    )

    if removed == 0:
        report.message = "no stale links found"
        return report

    if dry_run:
        report.message = f"dry-run: would remove {removed} stale link(s)"
        return report

    # Apply
    new_text = "".join(kept)
    symbol_index.write_text(new_text, encoding="utf-8")
    report.files_modified = [str(symbol_index.relative_to(root))]
    report.message = f"removed {removed} stale link(s) from SYMBOL_INDEX.md"
    return report
