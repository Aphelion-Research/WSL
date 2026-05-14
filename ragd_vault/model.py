from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SymbolInfo:
    filepath: str
    language: str
    chunk_type: str
    symbol_name: str
    qualified_name: str
    parent_symbol: str
    line_start: int
    line_end: int
    docstring: str
    imports: list[str]
    calls: list[str]
    is_public: bool
    content_hash: str


@dataclass(frozen=True)
class FileInfo:
    filepath: str
    language: str
    content_hash: str
    modified_at: int
    symbols: list[SymbolInfo]


def default_ragd_db() -> Path:
    return Path(os.environ.get("RAGD_DB_PATH", str(Path.home() / ".ragd" / "ragd.db"))).expanduser()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "unnamed"


def _loads(value: str | None) -> list[str]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def load_index(db_path: Path | None = None) -> list[FileInfo]:
    path = Path(db_path or default_ragd_db())
    if not path.exists():
        return []
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)").fetchall()}
        select = [
            "filepath",
            "lang",
            "chunk_type",
            "symbol_name",
            "qualified_name" if "qualified_name" in columns else "symbol_name AS qualified_name",
            "parent_symbol" if "parent_symbol" in columns else "'' AS parent_symbol",
            "line_start",
            "line_end",
            "docstring" if "docstring" in columns else "'' AS docstring",
            "imports_json" if "imports_json" in columns else "'[]' AS imports_json",
            "calls_json" if "calls_json" in columns else "'[]' AS calls_json",
            "is_public" if "is_public" in columns else "1 AS is_public",
            "content_hash",
            "modified_at" if "modified_at" in columns else "0 AS modified_at",
        ]
        rows = conn.execute(f"SELECT {', '.join(select)} FROM chunks WHERE status='active' ORDER BY filepath,line_start").fetchall()
    finally:
        conn.close()
    by_file: dict[str, list[SymbolInfo]] = {}
    file_lang: dict[str, str] = {}
    file_hash: dict[str, str] = {}
    file_modified: dict[str, int] = {}
    for row in rows:
        filepath = row["filepath"]
        info = SymbolInfo(
            filepath=filepath,
            language=row["lang"] or "text",
            chunk_type=row["chunk_type"] or "chunk",
            symbol_name=row["symbol_name"] or Path(filepath).stem,
            qualified_name=row["qualified_name"] or row["symbol_name"] or Path(filepath).stem,
            parent_symbol=row["parent_symbol"] or "",
            line_start=int(row["line_start"] or 1),
            line_end=int(row["line_end"] or row["line_start"] or 1),
            docstring=row["docstring"] or "",
            imports=_loads(row["imports_json"]),
            calls=_loads(row["calls_json"]),
            is_public=bool(row["is_public"]),
            content_hash=row["content_hash"] or "",
        )
        by_file.setdefault(filepath, []).append(info)
        file_lang[filepath] = info.language
        file_hash[filepath] = info.content_hash
        file_modified[filepath] = int(row["modified_at"] or 0)
    return [
        FileInfo(filepath=filepath, language=file_lang.get(filepath, "text"), content_hash=file_hash.get(filepath, ""), modified_at=file_modified.get(filepath, 0), symbols=symbols)
        for filepath, symbols in sorted(by_file.items())
    ]


def vault_file_note(vault_root: Path, filepath: str) -> Path:
    rel = _relative_source_path(filepath)
    return vault_root / "files" / rel.with_suffix(".md")


def vault_symbol_note(vault_root: Path, symbol: SymbolInfo) -> Path:
    rel = _relative_source_path(symbol.filepath).parent
    suffix = (symbol.content_hash or "nohash")[:8]
    return vault_root / "symbols" / rel / f"{safe_name(symbol.qualified_name)}-L{symbol.line_start}-{suffix}.md"


def _relative_source_path(filepath: str) -> Path:
    path = Path(filepath)
    parts = list(path.parts)
    if "Dominion" in parts:
        return Path(*parts[parts.index("Dominion") + 1:])
    if path.is_absolute():
        return Path(*parts[1:])
    return path
