"""File classification for dominion_loader.

Classifies each file into one of: code, doc, config, data, binary, unknown.
Language inference is done from extension and MIME-like signals.

INTERFACE(agent-1): classify(path) -> FileClass  (stable, consumed by Agent 2)
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

FileClass = Literal["code", "doc", "config", "data", "binary", "unknown"]

# Extension → (file_class, language)
_EXT_MAP: dict[str, tuple[FileClass, str]] = {
    # Code
    ".py":    ("code", "python"),
    ".pyi":   ("code", "python"),
    ".cpp":   ("code", "cpp"),
    ".cc":    ("code", "cpp"),
    ".cxx":   ("code", "cpp"),
    ".c":     ("code", "c"),
    ".h":     ("code", "cpp"),
    ".hpp":   ("code", "cpp"),
    ".hxx":   ("code", "cpp"),
    ".rs":    ("code", "rust"),
    ".go":    ("code", "go"),
    ".js":    ("code", "javascript"),
    ".mjs":   ("code", "javascript"),
    ".cjs":   ("code", "javascript"),
    ".ts":    ("code", "typescript"),
    ".tsx":   ("code", "typescript"),
    ".jsx":   ("code", "javascript"),
    ".java":  ("code", "java"),
    ".kt":    ("code", "kotlin"),
    ".scala": ("code", "scala"),
    ".rb":    ("code", "ruby"),
    ".php":   ("code", "php"),
    ".swift": ("code", "swift"),
    ".cs":    ("code", "csharp"),
    ".lua":   ("code", "lua"),
    ".r":     ("code", "r"),
    ".R":     ("code", "r"),
    ".jl":    ("code", "julia"),
    ".sh":    ("code", "shell"),
    ".bash":  ("code", "shell"),
    ".zsh":   ("code", "shell"),
    ".fish":  ("code", "shell"),
    ".ps1":   ("code", "powershell"),
    ".sql":   ("code", "sql"),
    # Docs
    ".md":    ("doc", "markdown"),
    ".mdx":   ("doc", "markdown"),
    ".rst":   ("doc", "rst"),
    ".txt":   ("doc", "text"),
    ".adoc":  ("doc", "asciidoc"),
    ".org":   ("doc", "org"),
    ".tex":   ("doc", "latex"),
    # Config
    ".json":  ("config", "json"),
    ".yaml":  ("config", "yaml"),
    ".yml":   ("config", "yaml"),
    ".toml":  ("config", "toml"),
    ".ini":   ("config", "ini"),
    ".cfg":   ("config", "ini"),
    ".conf":  ("config", "conf"),
    ".env":   ("config", "env"),
    ".xml":   ("config", "xml"),
    ".proto": ("config", "proto"),
    ".cmake": ("config", "cmake"),
    # Data (text-form, safe to index)
    ".csv":   ("data", "csv"),
    ".tsv":   ("data", "tsv"),
    ".jsonl": ("data", "jsonl"),
    ".ndjson":("data", "jsonl"),
    ".parquet": ("data", "parquet"),  # will be binary-detected at read time
    ".log":   ("data", "text"),
}

# Names with no extension that are recognizable config/doc files
_NAME_MAP: dict[str, tuple[FileClass, str]] = {
    "Makefile":       ("config", "makefile"),
    "Dockerfile":     ("config", "dockerfile"),
    "Jenkinsfile":    ("config", "groovy"),
    ".gitignore":     ("config", "text"),
    ".dominionignore":("config", "text"),
    "AGENTS.md":      ("doc", "markdown"),
    "README":         ("doc", "text"),
    "LICENSE":        ("doc", "text"),
    "CHANGELOG":      ("doc", "text"),
    "COPYING":        ("doc", "text"),
    "CMakeLists.txt": ("config", "cmake"),
}


def classify(path: Path | str) -> tuple[FileClass, str]:
    """Return (file_class, language) for the given path.

    Purely name/extension based — does not read file content.
    Returns ("unknown", "unknown") for unrecognised extensions.
    """
    path = Path(path)
    name = path.name

    if name in _NAME_MAP:
        return _NAME_MAP[name]

    ext = path.suffix.lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]

    return ("unknown", "unknown")


def is_likely_binary(path: Path, *, sample_bytes: int = 8192) -> bool:
    """Heuristic binary detection: check for null bytes in first sample_bytes.

    Fast path — only reads a small chunk.
    """
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_bytes)
        return b"\x00" in chunk
    except OSError:
        return True  # unreadable → treat as binary
