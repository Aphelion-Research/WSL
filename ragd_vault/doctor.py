from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class VaultDoctorReport:
    ok: bool
    total_notes: int
    broken_links: list[str]
    invalid_frontmatter: list[str]
    orphan_notes: list[str]
    mermaid_errors: list[str]


_WIKILINK = re.compile(r"\[\[([^]|#]+)(?:#[^]|]+)?(?:\|[^]]+)?\]\]")
_MERMAID = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def _frontmatter(text: str):
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("unterminated YAML frontmatter")
    return yaml.safe_load(text[4:end]) or {}


def inspect_vault(vault_root: Path) -> VaultDoctorReport:
    root = Path(vault_root)
    notes = sorted(root.rglob("*.md")) if root.exists() else []
    note_targets = {str(path.relative_to(root).with_suffix("")).replace("\\", "/") for path in notes}
    basenames = {path.stem for path in notes}
    broken: list[str] = []
    invalid: list[str] = []
    incoming = {str(path.relative_to(root).with_suffix("")).replace("\\", "/"): 0 for path in notes}
    mermaid_errors: list[str] = []
    for path in notes:
        rel = str(path.relative_to(root))
        text = path.read_text(encoding="utf-8")
        try:
            _frontmatter(text)
        except Exception as exc:
            invalid.append(f"{rel}: {exc}")
        for block in _MERMAID.findall(text):
            if block.count("{") != block.count("}"):
                mermaid_errors.append(rel)
        for match in _WIKILINK.findall(text):
            target = match.strip()
            if target in note_targets:
                incoming[target] = incoming.get(target, 0) + 1
            elif target.rsplit("/", 1)[-1] in basenames:
                continue
            else:
                broken.append(f"{rel} -> {target}")
    orphan_notes = [target for target, count in incoming.items() if count == 0 and not target.startswith("_index/") and not target.startswith("_daily/")]
    return VaultDoctorReport(ok=not broken and not invalid and not mermaid_errors, total_notes=len(notes), broken_links=broken, invalid_frontmatter=invalid, orphan_notes=orphan_notes, mermaid_errors=mermaid_errors)
