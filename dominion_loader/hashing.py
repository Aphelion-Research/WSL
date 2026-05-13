"""Content hashing and change detection for dominion_loader.

Policy (Approach C from spec):
  - Fast path: if mtime_ns + size match the manifest entry, trust the cached hash.
  - Verification path: sha256 the file content when no prior entry exists
    or when the fast path is disabled via DOMINION_HASH=full.
  - A DOMINION_HASH=full env var forces real SHA256 every time (for audits).

Stable IDs:
  document_id  = sha256(repo_root + "::" + relative_path)[:16]
  chunk_id     = sha256(document_id + ":" + line_start + ":" + line_end + ":" + content_hash)[:16]

INTERFACE(agent-1): hash_file, document_id_for, chunk_id_for  (stable, consumed by Agent 2)
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dominion_loader.obs import get_tracer


@dataclass(frozen=True)
class HashResult:
    content_hash: str   # sha256 hex digest
    fast_path: bool     # True if mtime+size short-circuit was used


@dataclass(frozen=True)
class PriorEntry:
    """Minimal info from a ManifestEntry needed for fast-path hashing."""
    content_hash: str
    mtime_ns: int
    size: int


def document_id_for(repo_root: str, relative_path: str) -> str:
    """Stable 16-char document ID.

    sha256(repo_root + '::' + relative_path)[:16]
    Deterministic and collision-resistant for repo scale.
    """
    raw = f"{repo_root}::{relative_path}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def chunk_id_for(
    document_id: str,
    line_start: int,
    line_end: int,
    content_hash: str,
) -> str:
    """Stable 16-char chunk ID.

    sha256(document_id + ':' + line_start + ':' + line_end + ':' + content_hash)[:16]
    """
    raw = f"{document_id}:{line_start}:{line_end}:{content_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def hash_file(
    path: Path | str,
    prior: Optional[PriorEntry] = None,
    *,
    trace_id: str = "",
    force_full: bool = False,
) -> HashResult:
    """Compute or retrieve the SHA256 hash of a file.

    Uses fast path (mtime+size match → trust prior hash) unless:
    - force_full is True
    - DOMINION_HASH=full env var is set
    - No prior entry exists
    - mtime_ns or size differ from prior
    """
    tracer = get_tracer()
    path = Path(path)
    full_mode = force_full or os.environ.get("DOMINION_HASH", "").lower() == "full"

    with tracer.span("hash_file", trace_id=trace_id, attrs={"path": str(path)}):
        if not full_mode and prior is not None:
            try:
                st = path.stat()
                if st.st_mtime_ns == prior.mtime_ns and st.st_size == prior.size:
                    tracer.event(
                        "cache_hit",
                        trace_id=trace_id,
                        attrs={"path": str(path), "reason": "mtime_size_match"},
                    )
                    return HashResult(content_hash=prior.content_hash, fast_path=True)
            except OSError:
                pass  # Fall through to full hash

        content_hash = _sha256_file(path)
        tracer.event(
            "cache_miss",
            trace_id=trace_id,
            attrs={"path": str(path), "reason": "content_read"},
        )
        return HashResult(content_hash=content_hash, fast_path=False)


def _sha256_file(path: Path) -> str:
    """Read file in chunks and return sha256 hex digest."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError as exc:
        raise OSError(f"cannot hash {path}: {exc}") from exc
    return h.hexdigest()
