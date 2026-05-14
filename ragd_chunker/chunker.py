from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ASTChunk:
    filepath: str
    content: str
    lang: str
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

    def to_dict(self) -> dict:
        return asdict(self)


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def module_name(filepath: str) -> str:
    path = Path(filepath)
    parts = list(path.with_suffix("").parts)
    if "Dominion" in parts:
        parts = parts[parts.index("Dominion") + 1:]
    return ".".join(part for part in parts if part not in {".", ""})


def _module_chunk(filepath: str, content: str, lang: str) -> list[ASTChunk]:
    lines = content.splitlines()
    name = module_name(filepath)
    return [ASTChunk(
        filepath=filepath,
        content=content,
        lang=lang,
        chunk_type="module",
        symbol_name=Path(filepath).name,
        qualified_name=name,
        parent_symbol="",
        line_start=1,
        line_end=max(1, len(lines)),
        docstring="",
        imports=[],
        calls=[],
        is_public=True,
        content_hash=content_hash(content),
    )]


def chunk_file(path: str, content: str, lang: str | None = None) -> list[ASTChunk]:
    suffix = Path(path).suffix.lower()
    language = (lang or "").lower()
    if not language:
        language = {
            ".py": "python",
            ".cc": "cpp",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".hpp": "cpp",
            ".h": "cpp",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".rs": "rust",
            ".go": "go",
        }.get(suffix, "text")
    if language == "python":
        from .languages.python import chunk_python
        return chunk_python(path, content)
    if language in {"cpp", "c++"}:
        from .languages.cpp import chunk_cpp
        return chunk_cpp(path, content)
    return _module_chunk(path, content, language)
