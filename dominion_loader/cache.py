"""Content-addressed cache with fingerprint validation for dominion_loader.

Design (Approach B — cache-aside with fingerprint):
- Cache.get() returns a CacheHit or None; caller MUST check fingerprint.
- Corrupt entries are quarantined (renamed .corrupt), never silently served.
- Namespace-keyed: loader:hash:<document_id>, chunker:chunks:..., etc.
- Agent 2 reserves the 'retrieval:' and 'context:' namespaces.
- Feature flag: DOMINION_CACHE=off → all operations are no-ops.

INTERFACE(agent-1): Cache.get, Cache.put, Cache.verify  (consumed by Agent 2)
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dominion_loader.obs import get_tracer


class CacheCorruption(Exception):
    """Raised when a cache entry fails fingerprint verification."""


@dataclass(frozen=True)
class CacheHit:
    value: bytes
    fingerprint: str


class Cache:
    """Content-addressed on-disk cache.

    Keys are namespaced: namespace + ':' + key.
    Values are stored as raw bytes. Fingerprint is a sha256 of the expected
    source content — mismatch → quarantine.
    """

    def __init__(self, cache_dir: Path | str | None = None) -> None:
        if cache_dir is None:
            dominion_home = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
            cache_dir = dominion_home / "cache"
        self._root = Path(cache_dir)
        self._enabled = os.environ.get("DOMINION_CACHE", "on").lower() != "off"
        if self._enabled:
            self._root.mkdir(parents=True, exist_ok=True)

    def get(self, namespace: str, key: str, *, fingerprint: str) -> Optional[CacheHit]:
        """Read a cache entry.

        Returns CacheHit if found AND fingerprint matches.
        Returns None if not found.
        Raises CacheCorruption if found but fingerprint mismatches.
        """
        if not self._enabled:
            return None

        tracer = get_tracer()
        cache_path = self._entry_path(namespace, key)

        if not cache_path.exists():
            tracer.event("cache_miss", attrs={"ns": namespace, "key": key[:16]})
            return None

        try:
            raw = cache_path.read_bytes()
        except OSError:
            tracer.event("cache_miss", attrs={"ns": namespace, "key": key[:16], "reason": "read_error"})
            return None

        # Verify: the stored content must begin with a fingerprint header line
        try:
            nl = raw.index(b"\n")
            stored_fp = raw[:nl].decode("ascii").strip()
            value = raw[nl + 1:]
        except (ValueError, UnicodeDecodeError) as exc:
            self._quarantine(cache_path, namespace, key)
            raise CacheCorruption(f"malformed cache entry {cache_path}: {exc}") from exc

        if stored_fp != fingerprint:
            self._quarantine(cache_path, namespace, key)
            raise CacheCorruption(
                f"fingerprint mismatch for {namespace}:{key[:16]} "
                f"stored={stored_fp[:8]}... expected={fingerprint[:8]}..."
            )

        tracer.event("cache_hit", attrs={"ns": namespace, "key": key[:16]})
        return CacheHit(value=value, fingerprint=fingerprint)

    def put(self, namespace: str, key: str, value: bytes, *, fingerprint: str) -> None:
        """Write a cache entry with its fingerprint."""
        if not self._enabled:
            return

        tracer = get_tracer()
        cache_path = self._entry_path(namespace, key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Write atomically: tmp → rename
        tmp = cache_path.with_suffix(".tmp")
        try:
            raw = fingerprint.encode("ascii") + b"\n" + value
            tmp.write_bytes(raw)
            tmp.rename(cache_path)
            tracer.event("cache_put", attrs={"ns": namespace, "key": key[:16]})
        except OSError as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise OSError(f"cache write failed for {namespace}:{key}: {exc}") from exc

    def verify(self) -> list[dict]:
        """Walk cache, verify all entries, return list of corrupt/suspicious entries."""
        if not self._enabled:
            return []

        results: list[dict] = []
        if not self._root.exists():
            return results

        for path in sorted(self._root.rglob("*.cache")):
            try:
                raw = path.read_bytes()
                nl = raw.index(b"\n")
                raw[:nl].decode("ascii").strip()  # Just parse; fingerprint unknown here
            except (ValueError, UnicodeDecodeError, OSError) as exc:
                results.append({
                    "path": str(path),
                    "status": "corrupt",
                    "error": str(exc),
                })
        return results

    def nuke(self) -> int:
        """Remove all cache entries. Returns count deleted."""
        count = 0
        if not self._root.exists():
            return 0
        for path in list(self._root.rglob("*.cache")) + list(self._root.rglob("*.corrupt")):
            try:
                path.unlink()
                count += 1
            except OSError:
                pass
        return count

    def stats(self) -> dict[str, int]:
        """Return cache statistics."""
        if not self._root.exists():
            return {"entries": 0, "corrupt": 0, "bytes": 0}
        entries = list(self._root.rglob("*.cache"))
        corrupt = list(self._root.rglob("*.corrupt"))
        total_bytes = sum(p.stat().st_size for p in entries if p.exists())
        return {"entries": len(entries), "corrupt": len(corrupt), "bytes": total_bytes}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _entry_path(self, namespace: str, key: str) -> Path:
        """Derive a filesystem path from namespace+key, content-addressed by their hash."""
        compound = f"{namespace}:{key}"
        h = hashlib.sha256(compound.encode("utf-8")).hexdigest()
        # Two-level directory sharding: h[:2]/h[2:4]/h.cache
        return self._root / h[:2] / h[2:4] / f"{h}.cache"

    def _quarantine(self, cache_path: Path, namespace: str, key: str) -> None:
        """Move a corrupt entry to .corrupt extension and emit a trace event."""
        tracer = get_tracer()
        corrupt_path = cache_path.with_suffix(".corrupt")
        try:
            cache_path.rename(corrupt_path)
        except OSError:
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass
        tracer.event(
            "cache_corruption",
            attrs={"ns": namespace, "key": key[:16], "quarantined": str(corrupt_path)},
        )
