from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import yaml

from .model import FileInfo, SymbolInfo, load_index, safe_name, vault_file_note, vault_symbol_note


def _frontmatter(data: dict) -> str:
    return "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True).strip() + "\n---\n\n"


def _wikilink(path: Path, label: str | None = None) -> str:
    target = str(path.with_suffix("")).replace("\\", "/")
    return f"[[{target}|{label}]]" if label else f"[[{target}]]"


def _purpose(file: FileInfo) -> str:
    public = [symbol for symbol in file.symbols if symbol.is_public]
    if public and public[0].docstring:
        return public[0].docstring.splitlines()[0]
    names = ", ".join(symbol.symbol_name for symbol in public[:5])
    return f"Defines {len(file.symbols)} indexed symbol(s)" + (f": {names}." if names else ".")


def _file_note(vault_root: Path, file: FileInfo) -> tuple[Path, str]:
    note = vault_file_note(vault_root, file.filepath)
    symbol_links = []
    for symbol in file.symbols:
        if symbol.is_public:
            symbol_note = vault_symbol_note(vault_root, symbol).relative_to(vault_root)
            symbol_links.append((symbol, _wikilink(symbol_note, symbol.symbol_name)))
    imports = sorted({item for symbol in file.symbols for item in symbol.imports})
    calls = sorted({item for symbol in file.symbols for item in symbol.calls})[:12]
    mermaid_lines = ["graph LR"]
    for symbol in file.symbols[:12]:
        source = safe_name(symbol.symbol_name)
        for call in symbol.calls[:4]:
            mermaid_lines.append(f"    {source} --> {safe_name(call)}")
    if len(mermaid_lines) == 1:
        mermaid_lines.append("    file --> symbols")
    body = [
        f"# {Path(file.filepath).name}",
        "",
        f"> **Language**: `{file.language}` | **Symbols**: {len(file.symbols)}",
        "",
        "## Purpose",
        "",
        _purpose(file),
        "",
        "## Public Symbols",
        "",
        "| Symbol | Type | Lines | Description |",
        "|---|---|---:|---|",
    ]
    for symbol, link in symbol_links:
        desc = symbol.docstring.splitlines()[0] if symbol.docstring else symbol.qualified_name
        body.append(f"| {link} | {symbol.chunk_type} | {symbol.line_start}-{symbol.line_end} | {desc} |")
    if not symbol_links:
        body.append("| *(none)* |  |  |  |")
    body.extend(["", "## Imports", ""])
    body.extend([f"- `{item}`" for item in imports] or ["- *(none indexed)*"])
    body.extend(["", "## Call Graph", "", "```mermaid", *mermaid_lines, "```", "", "## Recent Changes", "", f"> Content hash: `{file.content_hash}`. Last modified epoch: `{file.modified_at}`."])
    frontmatter = _frontmatter({
        "title": Path(file.filepath).name,
        "filepath": file.filepath,
        "language": file.language,
        "lines": max((symbol.line_end for symbol in file.symbols), default=0),
        "symbols": len(file.symbols),
        "public_symbols": len(symbol_links),
        "content_hash": file.content_hash,
        "tags": [file.language, "file"],
    })
    return note, frontmatter + "\n".join(body) + "\n"


def _symbol_note(vault_root: Path, symbol: SymbolInfo) -> tuple[Path, str]:
    note = vault_symbol_note(vault_root, symbol)
    file_note = vault_file_note(vault_root, symbol.filepath).relative_to(vault_root)
    body = [
        f"# `{symbol.symbol_name}`",
        "",
        f"> **File**: {_wikilink(file_note, Path(symbol.filepath).name)} | **Lines**: {symbol.line_start}-{symbol.line_end} | **Type**: `{symbol.chunk_type}`",
        "",
        "## Docstring",
        "",
        symbol.docstring or "*(none indexed)*",
        "",
        "## Calls",
        "",
    ]
    body.extend([f"- `{call}`" for call in symbol.calls] or ["- *(none indexed)*"])
    body.extend(["", "## Imports In File", ""])
    body.extend([f"- `{item}`" for item in symbol.imports] or ["- *(none indexed)*"])
    frontmatter = _frontmatter({
        "title": symbol.symbol_name,
        "qualified_name": symbol.qualified_name,
        "symbol_type": symbol.chunk_type,
        "filepath": symbol.filepath,
        "line_start": symbol.line_start,
        "line_end": symbol.line_end,
        "parent_symbol": symbol.parent_symbol,
        "is_public": symbol.is_public,
        "tags": [symbol.chunk_type, symbol.language, "symbol"],
    })
    return note, frontmatter + "\n".join(body) + "\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _settings(vault_root: Path) -> None:
    (vault_root / ".obsidian").mkdir(parents=True, exist_ok=True)
    _write(vault_root / ".obsidian" / "app.json", json.dumps({"defaultViewMode": "preview", "livePreview": True}, indent=2))
    _write(vault_root / ".obsidian" / "appearance.json", json.dumps({"theme": "obsidian", "cssTheme": "Minimal", "font": {"text": "Inter"}}, indent=2))
    _write(vault_root / ".obsidian" / "graph.json", json.dumps({"showTags": True, "showAttachments": False, "colorGroups": [{"query": "tag:#python", "color": {"a": 1, "rgb": 255}}, {"query": "tag:#cpp", "color": {"a": 1, "rgb": 16753920}}, {"query": "tag:#daily", "color": {"a": 1, "rgb": 8421504}}]}, indent=2))


def _indexes(vault_root: Path, files: list[FileInfo]) -> None:
    modules: dict[str, list[FileInfo]] = {}
    for file in files:
        module = Path(file.filepath).parts[-2] if len(Path(file.filepath).parts) > 1 else "root"
        modules.setdefault(module, []).append(file)
    rows = [_frontmatter({"title": "Module Index", "tags": ["index"]}) + "# Module Index", "", "| Module | Files | Public Symbols | Description |", "|---|---:|---:|---|"]
    for module, module_files in sorted(modules.items()):
        public = sum(1 for file in module_files for symbol in file.symbols if symbol.is_public)
        rows.append(f"| `{module}` | {len(module_files)} | {public} | Indexed source module |")
    _write(vault_root / "_index" / "MODULE_INDEX.md", "\n".join(rows) + "\n")
    symbols = [symbol for file in files for symbol in file.symbols if symbol.is_public]
    lines = [_frontmatter({"title": "Symbol Index", "tags": ["index"]}) + "# Symbol Index", ""]
    for symbol in sorted(symbols, key=lambda item: item.qualified_name):
        note = vault_symbol_note(vault_root, symbol).relative_to(vault_root)
        lines.append(f"- {_wikilink(note, symbol.qualified_name)}")
    _write(vault_root / "_index" / "SYMBOL_INDEX.md", "\n".join(lines) + "\n")
    packages = ["dominion_loader", "dominion_ai", "dominion_agent", "ragd", "domdata", "research_os", "ragd_embed", "ragd_chunker", "ragd_hnsw", "ragd_graph", "ragd_vault"]
    nodes = [{"id": package, "type": "text", "text": package, "x": (index % 4) * 320, "y": (index // 4) * 180, "width": 260, "height": 80, "color": "4" if package.startswith("ragd_") else "2"} for index, package in enumerate(packages)]
    edges = [{"id": f"e{index}", "fromNode": edge[0], "toNode": edge[1], "fromSide": "right", "toSide": "left", "label": edge[2]} for index, edge in enumerate([("dominion_loader", "ragd", "indexes"), ("ragd_chunker", "ragd", "chunks"), ("ragd_embed", "ragd_hnsw", "embeds"), ("ragd", "ragd_vault", "feeds"), ("ragd_graph", "ragd_vault", "links")])]
    _write(vault_root / "_index" / "GRAPH_OVERVIEW.canvas", json.dumps({"nodes": nodes, "edges": edges}, indent=2))


def _daily(vault_root: Path, files: list[FileInfo]) -> None:
    today = time.strftime("%Y-%m-%d")
    text = _frontmatter({"date": today, "files_changed": len(files), "files_added": 0, "files_deleted": 0, "symbols_added": sum(len(file.symbols) for file in files), "symbols_deleted": 0, "tags": ["daily", "changelog"]})
    text += f"# {today} — Codebase Changes\n\n## Indexed Files\n\n"
    for file in files[:50]:
        note = vault_file_note(vault_root, file.filepath).relative_to(vault_root)
        text += f"- {_wikilink(note, Path(file.filepath).name)} — {len(file.symbols)} symbol(s)\n"
    _write(vault_root / "_daily" / f"{today}.md", text)


def _templates(vault_root: Path) -> None:
    _write(vault_root / "_templates" / "File Note.md", _frontmatter({"title": "File Note Template", "tags": ["template"]}) + "# {{title}}\n\nGenerated from RAGD chunks.\n")
    _write(vault_root / "_templates" / "Symbol Note.md", _frontmatter({"title": "Symbol Note Template", "tags": ["template"]}) + "# {{qualified_name}}\n\nGenerated from RAGD symbol metadata.\n")
    _write(vault_root / "_templates" / "Daily Changelog.md", _frontmatter({"title": "Daily Changelog Template", "tags": ["template"]}) + "# {{date}}\n\nGenerated by dominion vault sync.\n")


def build_vault(vault_root: Path | None = None, *, ragd_db: Path | None = None, wipe: bool = True) -> dict:
    root = Path(vault_root or Path.home() / "Dominion" / "vault")
    files = load_index(ragd_db)
    if wipe and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    _settings(root)
    _templates(root)
    for file in files:
        path, text = _file_note(root, file)
        _write(path, text)
        for symbol in file.symbols:
            if symbol.is_public:
                spath, stext = _symbol_note(root, symbol)
                _write(spath, stext)
    _indexes(root, files)
    _daily(root, files)
    return {"ok": True, "vault": str(root), "files": len(files), "symbols": sum(1 for file in files for symbol in file.symbols if symbol.is_public)}
