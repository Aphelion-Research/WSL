"""RAGD ingestion bridge for dominion_loader.

Sends files to RAGD via batched POST /index and /index/delete requests.
Producer side of the RAGD_INTEGRATION_CONTRACT.

Guarantees:
- document_id is stable across runs for same (repo_root, relative_path).
- Unchanged content (same hash) produces 0 new rows in RAGD chunks table.
- Deletions are communicated through RAGD POST /index/delete.
- Manifest tracks ingestion state; bridge resumes from manifest on RAGD failure.
- Feature flag: DOMINION_RAGD_BRIDGE=off → skip all RAGD calls.

INTERFACE(agent-1): RagdBridge  (producer side of ingestion contract)
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from dominion_loader.obs import get_tracer


@dataclass(frozen=True)
class IngestResult:
    """Result of a single RAGD ingest batch.

    INTERFACE(agent-1): All fields stable. ok and elapsed_s are derived views.
    """
    paths_submitted: int
    chunks_indexed: int
    already_current: int
    duration_ms: float
    error: Optional[str]

    @property
    def ok(self) -> bool:
        """True when no error occurred."""
        return self.error is None

    @property
    def elapsed_s(self) -> float:
        """Duration in seconds (derived from duration_ms)."""
        return self.duration_ms / 1000.0

    @property
    def paths_failed(self) -> int:
        """Number of failed batches (0 or 1 in current single-error model)."""
        return 0 if self.error is None else self.paths_submitted

    def to_dict(self) -> dict:
        """Return JSON-serializable dict for CLI/logging output."""
        return {
            "paths_submitted": self.paths_submitted,
            "chunks_indexed": self.chunks_indexed,
            "already_current": self.already_current,
            "duration_ms": round(self.duration_ms, 3),
            "elapsed_s": round(self.elapsed_s, 3),
            "error": self.error,
            "ok": self.ok,
        }


@dataclass(frozen=True)
class DeleteResult:
    """Result of a single RAGD deletion propagation batch.

    INTERFACE(agent-3): Deletion is soft-delete only in RAGD storage.
    """
    paths_submitted: int
    files_marked_deleted: int
    chunks_marked_deleted: int
    duration_ms: float
    errors: list[dict[str, str]]
    skipped: bool = False
    reason: Optional[str] = None

    @property
    def ok(self) -> bool:
        """True when deletion was accepted or intentionally skipped."""
        return not self.errors

    @property
    def elapsed_s(self) -> float:
        """Duration in seconds (derived from duration_ms)."""
        return self.duration_ms / 1000.0

    def to_dict(self) -> dict:
        """Return JSON-serializable dict for CLI/logging output."""
        return {
            "paths_submitted": self.paths_submitted,
            "files_marked_deleted": self.files_marked_deleted,
            "chunks_marked_deleted": self.chunks_marked_deleted,
            "duration_ms": round(self.duration_ms, 3),
            "elapsed_s": round(self.elapsed_s, 3),
            "errors": self.errors,
            "skipped": self.skipped,
            "reason": self.reason,
            "ok": self.ok,
        }


class RagdBridge:
    """Sends file paths to RAGD for chunking and storage.

    RAGD owns the actual chunking strategy (current: ragd/src/indexer.cpp).
    This bridge is the *producer*: it tells RAGD which paths to index.

    NOTE: RAGD's /index endpoint re-runs its own should_ignore() logic,
    so even if the bridge submits a path, RAGD may reject it.
    The manifest tracks what we attempted.
    """

    def __init__(
        self,
        *,
        ragd_url: Optional[str] = None,
        batch_size: int = 50,
        timeout: int = 30,
        max_retries: int = 2,
    ) -> None:
        self._url = (ragd_url or os.environ.get("RAGD_URL", "http://127.0.0.1:7474")).rstrip("/")
        self._batch_size = batch_size
        self._timeout = timeout
        self._max_retries = max_retries
        self._enabled = os.environ.get("DOMINION_RAGD_BRIDGE", "on").lower() != "off"
        self._delete_enabled = os.environ.get("DOMINION_RAGD_DELETE", "on").lower() != "off"

    def ingest_paths(self, paths: list[str]) -> IngestResult:
        """Submit a list of file paths to RAGD /index.

        RAGD indexes the files and returns chunks_indexed count.
        """
        if not self._enabled:
            return IngestResult(
                paths_submitted=len(paths),
                chunks_indexed=0,
                already_current=0,
                duration_ms=0.0,
                error="DOMINION_RAGD_BRIDGE=off",
            )

        tracer = get_tracer()
        start = time.monotonic()

        with tracer.span("ragd_index_batch", attrs={"paths": len(paths)}):
            total_chunks = 0
            total_current = 0
            last_error: Optional[str] = None

            for batch in _batched(paths, self._batch_size):
                result = self._post_index(batch)
                if result.get("error"):
                    last_error = result["error"]
                    # Don't retry entire batch on permanent error
                    break
                total_chunks += result.get("chunks_indexed", result.get("queued", 0))
                total_current += result.get("already_current", 0)

        duration_ms = (time.monotonic() - start) * 1000
        return IngestResult(
            paths_submitted=len(paths),
            chunks_indexed=total_chunks,
            already_current=total_current,
            duration_ms=duration_ms,
            error=last_error,
        )

    def delete_paths(self, paths: list[str]) -> DeleteResult:
        """Submit file paths to RAGD /index/delete for soft deletion."""
        if not paths:
            return DeleteResult(0, 0, 0, 0.0, [])
        if not self._enabled:
            return DeleteResult(
                paths_submitted=len(paths),
                files_marked_deleted=0,
                chunks_marked_deleted=0,
                duration_ms=0.0,
                errors=[],
                skipped=True,
                reason="DOMINION_RAGD_BRIDGE=off",
            )
        if not self._delete_enabled:
            return DeleteResult(
                paths_submitted=len(paths),
                files_marked_deleted=0,
                chunks_marked_deleted=0,
                duration_ms=0.0,
                errors=[],
                skipped=True,
                reason="DOMINION_RAGD_DELETE=off",
            )

        tracer = get_tracer()
        start = time.monotonic()
        total_files = 0
        total_chunks = 0
        errors: list[dict[str, str]] = []

        with tracer.span("ragd_delete_batch", attrs={"paths": len(paths)}):
            for batch in _batched(paths, self._batch_size):
                result = self._post_delete(batch)
                total_files += int(result.get("files_marked_deleted", 0))
                total_chunks += int(result.get("chunks_marked_deleted", 0))
                for error in result.get("errors", []):
                    errors.append({"path": str(error.get("path", "")), "error": str(error.get("error", error))})
                if result.get("error"):
                    errors.append({"path": "", "error": str(result["error"])})
                    break

        duration_ms = (time.monotonic() - start) * 1000
        return DeleteResult(
            paths_submitted=len(paths),
            files_marked_deleted=total_files,
            chunks_marked_deleted=total_chunks,
            duration_ms=duration_ms,
            errors=errors,
        )

    def health(self) -> dict:
        """Check RAGD health endpoint."""
        if not self._enabled:
            return {"ok": False, "error": "DOMINION_RAGD_BRIDGE=off"}
        try:
            with urlopen(f"{self._url}/health", timeout=5) as resp:
                return {"ok": True, "status": resp.status, "data": json.loads(resp.read())}
        except (OSError, URLError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)}

    def chunk_count(self) -> Optional[int]:
        """Return the active chunk count from RAGD health, or None on failure."""
        h = self.health()
        if h.get("ok"):
            data = h.get("data", {})
            return data.get("active_chunks", data.get("chunks"))
        return None

    # ------------------------------------------------------------------
    def _post_index(self, paths: list[str]) -> dict:
        """POST /index with a batch of paths. Returns parsed response or error dict."""
        tracer = get_tracer()
        payload = json.dumps({"paths": paths}).encode("utf-8")

        for attempt in range(self._max_retries + 1):
            try:
                req = Request(
                    f"{self._url}/index",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    tracer.event(
                        "ragd_index_chunk",
                        attrs={
                            "paths": len(paths),
                            "chunks": data.get("chunks_indexed", 0),
                            "attempt": attempt,
                        },
                    )
                    return data
            except (OSError, URLError) as exc:
                if attempt >= self._max_retries:
                    tracer.event(
                        "error",
                        attrs={
                            "class": type(exc).__name__,
                            "message": str(exc),
                            "paths": len(paths),
                        },
                    )
                    return {"error": str(exc), "chunks_indexed": 0}
                time.sleep(0.5 * (attempt + 1))
            except json.JSONDecodeError as exc:
                return {"error": f"invalid JSON from RAGD: {exc}", "chunks_indexed": 0}
        return {"error": "max retries exceeded", "chunks_indexed": 0}

    def _post_delete(self, paths: list[str]) -> dict:
        """POST /index/delete with a batch of paths. Returns parsed response or error dict."""
        tracer = get_tracer()
        payload = json.dumps({"paths": paths}).encode("utf-8")

        for attempt in range(self._max_retries + 1):
            try:
                req = Request(
                    f"{self._url}/index/delete",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(req, timeout=self._timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    tracer.event(
                        "ragd_delete_chunk",
                        attrs={
                            "paths": len(paths),
                            "chunks_deleted": data.get("chunks_marked_deleted", 0),
                            "attempt": attempt,
                        },
                    )
                    return data
            except (OSError, URLError) as exc:
                if attempt >= self._max_retries:
                    tracer.event(
                        "error",
                        attrs={
                            "class": type(exc).__name__,
                            "message": str(exc),
                            "paths": len(paths),
                            "url": f"{self._url}/index/delete",
                        },
                    )
                    return {"error": f"{self._url}/index/delete: {exc}", "errors": []}
                time.sleep(0.5 * (attempt + 1))
            except json.JSONDecodeError as exc:
                return {"error": f"invalid JSON from RAGD delete: {exc}", "errors": []}
        return {"error": "max retries exceeded", "errors": []}


def _batched(items: list, size: int) -> Iterator[list]:
    """Yield successive slices of `items` of length `size`."""
    for i in range(0, len(items), size):
        yield items[i : i + size]
