"""File ignore rules for dominion_loader.

Design: Hybrid built-in (non-overridable) deny list + optional .dominionignore.
The built-in rules can never be removed by user config — this prevents accidental
indexing of secrets/, model files, raw data, or Wine prefixes.

INTERFACE(agent-1): Ignore.match(path) -> bool  (stable, consumed by Agent 2)
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import FrozenSet, Optional


# ---------------------------------------------------------------------------
# Built-in deny list (IMMUTABLE — cannot be overridden by user config)
# Any path component matching one of these names is always ignored.
# ---------------------------------------------------------------------------
_BUILTIN_DIR_DENY: FrozenSet[str] = frozenset({
    "secrets",          # SECURITY: never index secrets
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "build",
    "dist",
    "vendor",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "eggs",
    ".eggs",
    ".hg",
    ".svn",
    # Wine / MT5 artifacts
    "drive_c",
    "dosdevices",
    "apps",             # MT5 wine apps — never index
})

# Path substring patterns — always excluded regardless of component position
_BUILTIN_PATH_DENY: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p) for p in [
        r"(?:^|[/\\])data[/\\]raw[/\\]",
        r"(?:^|[/\\])data[/\\]normalized[/\\]",
        r"(?:^|[/\\])secrets[/\\]",
        r"(?:^|[/\\])backups[/\\]",
        r"(?:^|[/\\])models[/\\]active[/\\]",
        r"(?:^|[/\\])\.ragd[/\\]",
        r"[^/\\][/\\]tmp[/\\]",     # project tmp/ subdirectory only (not /tmp at fs root)
    ]
)

# File extension deny list (binary, model, DB files)
_BUILTIN_EXT_DENY: FrozenSet[str] = frozenset({
    ".duckdb", ".sqlite", ".sqlite3", ".db", ".db3",
    ".gguf", ".ggml", ".bin", ".pth", ".pt", ".onnx",
    ".pkl", ".pickle", ".npy", ".npz",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo",
    ".whl", ".egg",
    ".tar", ".gz", ".bz2", ".xz", ".zip", ".7z",
    ".iso", ".img",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".ico",
    ".mp3", ".mp4", ".avi", ".mkv", ".mov", ".wav", ".flac",
    ".pdf",
})

# Maximum file size to index (bytes) — 512 KB default
DEFAULT_MAX_BYTES: int = 512 * 1024


class Ignore:
    """Evaluates whether a path should be ignored.

    Thread-safe and stateless once constructed. Accepts config
    explicitly — no module-level mutable state.
    """

    def __init__(
        self,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        dominionignore_path: Optional[Path] = None,
        extra_dir_deny: Optional[FrozenSet[str]] = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._extra_dir_deny: FrozenSet[str] = extra_dir_deny or frozenset()
        self._user_patterns: list[re.Pattern[str]] = []
        if dominionignore_path and dominionignore_path.is_file():
            self._user_patterns = _load_dominionignore(dominionignore_path)

    # ------------------------------------------------------------------
    def match(self, path: Path | str) -> bool:
        """Return True if the path should be ignored (excluded from indexing).

        SECURITY: built-in rules (including secrets/) are always enforced
        and cannot be overridden by user config.
        """
        path = Path(path)
        name = path.name
        path_str = str(path)

        # Built-in dir component check
        for part in path.parts:
            if part in _BUILTIN_DIR_DENY or part in self._extra_dir_deny:
                return True

        # Built-in substring pattern check
        for pat in _BUILTIN_PATH_DENY:
            if pat.search(path_str):
                return True

        # Extension check
        ext = path.suffix.lower()
        if ext in _BUILTIN_EXT_DENY:
            return True

        # Dot-files and dot-dirs (other than known useful ones)
        if name.startswith(".") and name not in {".env.example", ".dominionignore"}:
            return True

        # User patterns from .dominionignore
        for pat in self._user_patterns:
            if pat.search(path_str):
                return True

        return False

    def match_size(self, size: int) -> bool:
        """Return True if file is too large to index."""
        return size > self._max_bytes

    # ------------------------------------------------------------------
    @staticmethod
    def builtin_rules() -> dict[str, object]:
        """Export the current built-in rule set (for dominion ignore show).

        INTERFACE(agent-1): dict with 'dir_deny', 'path_deny', 'ext_deny'
        """
        return {
            "dir_deny": sorted(_BUILTIN_DIR_DENY),
            "path_deny": [p.pattern for p in _BUILTIN_PATH_DENY],
            "ext_deny": sorted(_BUILTIN_EXT_DENY),
            "max_bytes": DEFAULT_MAX_BYTES,
            "secrets_always_ignored": True,  # invariant assertion for tests
        }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _load_dominionignore(path: Path) -> list[re.Pattern[str]]:
    """Parse .dominionignore as gitignore-style lines → compiled regex patterns.

    Lines starting with # are comments.  Glob '*' → '.*' for substring matching.
    Importantly, this cannot disable built-in rules.
    """
    patterns: list[re.Pattern[str]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Simple glob-to-regex: * → [^/]*, ** → .*
            escaped = re.escape(line).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
            try:
                patterns.append(re.compile(escaped))
            except re.error:
                pass  # malformed pattern — skip silently
    except OSError:
        pass
    return patterns
