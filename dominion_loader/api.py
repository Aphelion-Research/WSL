"""Public API for dominion_loader — stable interface consumed by Agent 2.

INTERFACE(agent-1): v1.0.0 — changes require bumped version + INTERFACE(agent-1) note.

All functions accept config explicitly. No global mutable state.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal, Optional

# Re-export core types
from dominion_loader.scan import LoadedFile, iter_loaded_files
from dominion_loader.manifest import Manifest, ManifestEntry
from dominion_loader.semantic_diff import semantic_diff as _semantic_diff, DiffClass
from dominion_loader.cache import Cache, CacheHit, CacheCorruption
from dominion_loader.hw_probe import hw_probe as _hw_probe, HardwareProfile


def iter_files(
    repo_root: str,
    *,
    force_full: bool = False,
) -> Iterator[LoadedFile]:
    """Iterate all indexable files under repo_root.

    Yields LoadedFile in deterministic sorted order.
    Does NOT write to manifest or RAGD (read-only).

    INTERFACE(agent-1): stable — do not change signature without sign-off from Agent 2.
    """
    yield from iter_loaded_files(Path(repo_root), force_full=force_full)


def get_manifest_entry(document_id: str) -> Optional[ManifestEntry]:
    """Retrieve a single manifest entry by document_id.

    Returns None if not found.
    """
    m = Manifest()
    try:
        return m.get(document_id)
    finally:
        m.close()


def list_changed_since(epoch: int) -> Iterator[ManifestEntry]:
    """Yield manifest entries where indexed_at > epoch (seconds since Unix epoch)."""
    m = Manifest()
    try:
        yield from m.list_changed_since(epoch)
    finally:
        m.close()


def semantic_diff(
    old: bytes,
    new: bytes,
) -> Literal["format-only", "comment-only", "whitespace-only", "functional"]:
    """Classify the semantic difference between two versions of a file.

    Conservative bias: returns "functional" when uncertain.
    INTERFACE(agent-1): stable.
    """
    return _semantic_diff(old, new)


def hw_probe() -> "HardwareProfile":
    """Return hardware profile for this machine.

    INTERFACE(agent-1): Agent 2 reads this to choose model strategy.
    """
    return _hw_probe()


def cache_get(namespace: str, key: str, *, fingerprint: str) -> Optional[CacheHit]:
    """Read from the dominion cache.

    Returns CacheHit or None. Raises CacheCorruption on fingerprint mismatch.
    INTERFACE(agent-1): Agent 2 may use 'retrieval:' and 'context:' namespaces.
    """
    c = Cache()
    return c.get(namespace, key, fingerprint=fingerprint)


def cache_put(namespace: str, key: str, value: bytes, *, fingerprint: str) -> None:
    """Write to the dominion cache."""
    c = Cache()
    c.put(namespace, key, value, fingerprint=fingerprint)


__all__ = [
    "LoadedFile",
    "ManifestEntry",
    "HardwareProfile",
    "CacheHit",
    "CacheCorruption",
    "DiffClass",
    "iter_files",
    "get_manifest_entry",
    "list_changed_since",
    "semantic_diff",
    "hw_probe",
    "cache_get",
    "cache_put",
]
