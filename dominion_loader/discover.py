"""Deterministic directory walker for dominion_loader.

Key properties:
- Sorted directory listings → two runs produce identical output when nothing changed.
- Symlinks are followed for files, not for directories (avoids cycles).
- Per-file errors are caught and yielded as structured error events, not swallowed.
- No global mutable state.

INTERFACE(agent-1): discover(repo_root, ignore) -> Iterator[DiscoveredFile]
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from dominion_loader.ignore import Ignore
from dominion_loader.obs import Span, get_tracer


@dataclass(frozen=True)
class DiscoveredFile:
    """A file found by the directory walker, before hashing or classification."""

    path: Path
    relative_path: str   # relative to repo_root, POSIX separators
    repo_root: str
    size: int            # bytes
    mtime_ns: int        # nanoseconds since epoch


@dataclass(frozen=True)
class DiscoveryError:
    """Structured error emitted when a path cannot be stat'd or read."""

    path: Path
    error: str


def discover(
    repo_root: Path | str,
    ignore: Ignore,
    *,
    trace_id: str = "",
) -> Iterator[DiscoveredFile | DiscoveryError]:
    """Yield DiscoveredFile for every indexable file under repo_root.

    Files are yielded in deterministic sorted order.
    Errors are yielded as DiscoveryError, never raised.
    """
    tracer = get_tracer()
    repo_root = Path(repo_root).resolve()

    with tracer.span("scan_root", trace_id=trace_id, attrs={"repo_root": str(repo_root)}):
        yield from _walk(repo_root, repo_root, ignore, trace_id, tracer)


def _walk(
    base: Path,
    repo_root: Path,
    ignore: Ignore,
    trace_id: str,
    tracer: object,
) -> Iterator[DiscoveredFile | DiscoveryError]:
    """Recursive sorted walk. base is the current directory."""
    tracer = get_tracer()  # tracer is stateless, re-acquire

    try:
        entries = sorted(os.scandir(base), key=lambda e: e.name)
    except OSError as exc:
        yield DiscoveryError(path=base, error=str(exc))
        return

    with tracer.span("discover_dir", trace_id=trace_id, attrs={"dir": str(base)}):
        for entry in entries:
            path = Path(entry.path)
            rel = path.relative_to(repo_root).as_posix()

            # Check dir-level ignore before descending
            if entry.is_dir(follow_symlinks=False):
                if ignore.match(path):
                    continue
                yield from _walk(path, repo_root, ignore, trace_id, tracer)
                continue

            # Regular file (follow symlinks to files, not dirs)
            if not entry.is_file(follow_symlinks=True):
                continue

            if ignore.match(path):
                tracer.event(
                    "file_skipped",
                    trace_id=trace_id,
                    attrs={"path": rel, "reason": "ignore_rule"},
                )
                continue

            try:
                stat = entry.stat(follow_symlinks=True)
            except OSError as exc:
                yield DiscoveryError(path=path, error=str(exc))
                continue

            size = stat.st_size
            if ignore.match_size(size):
                tracer.event(
                    "file_skipped",
                    trace_id=trace_id,
                    attrs={"path": rel, "reason": "too_large", "size": size},
                )
                continue

            yield DiscoveredFile(
                path=path,
                relative_path=rel,
                repo_root=str(repo_root),
                size=size,
                mtime_ns=stat.st_mtime_ns,
            )
