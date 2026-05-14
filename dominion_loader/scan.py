"""Main scan orchestration for dominion_loader.

Pipeline: discover → classify → hash → manifest → RAGD bridge
Produces a deterministic scan_trace.jsonl and updates the manifest.

Key invariant: unchanged file (same mtime_ns, size, content_hash)
produces 0 new RAGD inserts on rescan.

Feature flags:
  DOMINION_LOADER=new|legacy  (new is default)
  DOMINION_RAGD_BRIDGE=on|off
  DOMINION_TRACE=on|off
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

from dominion_loader.classify import classify, is_likely_binary
from dominion_loader.discover import discover, DiscoveredFile, DiscoveryError
from dominion_loader.hashing import hash_file, document_id_for, PriorEntry
from dominion_loader.ignore import Ignore
from dominion_loader.manifest import Manifest, ManifestEntry
from dominion_loader.obs import get_tracer, make_tracer, new_trace_id
from dominion_loader.ragd_bridge import RagdBridge


@dataclass(frozen=True)
class LoadedFile:
    """A file that has been discovered, classified, and hashed.

    This is the stable interface consumed by Agent 2.
    INTERFACE(agent-1): v1 — additive additions only, no removals without sign-off.
    """
    path: str
    relative_path: str
    repo_root: str
    size: int
    mtime_ns: int
    file_class: str          # "code" | "doc" | "config" | "data" | "binary" | "unknown"
    language: str
    content_hash: str        # sha256 hex
    document_id: str         # 16-char stable ID
    trace_id: str
    is_new: bool             # True if not seen in prior manifest
    is_changed: bool         # True if content_hash differs from prior


@dataclass
class ScanStats:
    trace_id: str
    repo_root: str
    files_seen: int = 0
    files_new: int = 0
    files_changed: int = 0
    files_deleted: int = 0
    files_skipped: int = 0
    files_error: int = 0
    ragd_chunks_indexed: int = 0
    ragd_errors: int = 0
    ragd_paths_deleted: int = 0
    ragd_chunks_deleted: int = 0
    ragd_delete_errors: int = 0
    duration_ms: float = 0.0


def scan(
    repo_root: Path | str,
    *,
    dry_run: bool = False,
    force_full: bool = False,
    once: bool = True,
    trace_id: Optional[str] = None,
    manifest: Optional[Manifest] = None,
    bridge: Optional[RagdBridge] = None,
    ignore: Optional[Ignore] = None,
) -> ScanStats:
    """Run a full scan of repo_root.

    Args:
        dry_run: discover and hash but do NOT write to manifest or RAGD.
        force_full: force sha256 of every file (ignore mtime fast-path).
        once: run once and return (vs. watch mode — not implemented here).
        trace_id: explicit trace ID (auto-generated if None).
        manifest: inject a Manifest (for testing).
        bridge: inject a RagdBridge (for testing).
        ignore: inject an Ignore (for testing).
    """
    repo_root = Path(repo_root).resolve()
    tid = trace_id or new_trace_id()
    tracer = make_tracer(trace_id=tid)

    _manifest = manifest or Manifest()
    _bridge = bridge or RagdBridge()
    _ignore = ignore or Ignore(dominionignore_path=repo_root / ".dominionignore")

    stats = ScanStats(trace_id=tid, repo_root=str(repo_root))
    start = time.monotonic()

    try:
        run_id: Optional[int] = None
        if not dry_run:
            run_id = _manifest.start_scan_run(tid, str(repo_root))

        # Track all known document IDs to detect deletions
        known_ids = _manifest.list_all_document_ids(str(repo_root))
        seen_ids: set[str] = set()

        # Batch paths to ingest into RAGD
        ingest_batch: list[str] = []
        delete_batch: list[str] = []

        with tracer.span("scan_root", trace_id=tid, attrs={"repo_root": str(repo_root), "dry_run": dry_run}):
            for item in discover(repo_root, _ignore, trace_id=tid):
                if isinstance(item, DiscoveryError):
                    tracer.event(
                        "error",
                        trace_id=tid,
                        attrs={
                            "class": "DiscoveryError",
                            "message": item.error,
                            "path": str(item.path),
                        },
                    )
                    stats.files_error += 1
                    continue

                assert isinstance(item, DiscoveredFile)
                stats.files_seen += 1

                # Binary detection
                if is_likely_binary(item.path):
                    tracer.event(
                        "file_skipped",
                        trace_id=tid,
                        attrs={"path": item.relative_path, "reason": "binary"},
                    )
                    stats.files_skipped += 1
                    continue

                doc_id = document_id_for(str(repo_root), item.relative_path)
                seen_ids.add(doc_id)

                file_class, language = classify(item.path)

                # Get prior manifest entry for fast-path hashing
                prior_entry = _manifest.get(doc_id)
                prior = (
                    PriorEntry(
                        content_hash=prior_entry.content_hash,
                        mtime_ns=prior_entry.mtime_ns,
                        size=prior_entry.size,
                    )
                    if prior_entry else None
                )

                try:
                    hash_result = hash_file(
                        item.path,
                        prior,
                        trace_id=tid,
                        force_full=force_full,
                    )
                except OSError as exc:
                    tracer.event(
                        "error",
                        trace_id=tid,
                        attrs={"class": "OSError", "message": str(exc), "path": item.relative_path},
                    )
                    stats.files_error += 1
                    continue

                is_new = prior_entry is None
                is_changed = (
                    not is_new
                    and prior_entry.content_hash != hash_result.content_hash
                )

                if is_new:
                    stats.files_new += 1
                elif is_changed:
                    stats.files_changed += 1

                loaded = LoadedFile(
                    path=str(item.path),
                    relative_path=item.relative_path,
                    repo_root=str(repo_root),
                    size=item.size,
                    mtime_ns=item.mtime_ns,
                    file_class=file_class,
                    language=language,
                    content_hash=hash_result.content_hash,
                    document_id=doc_id,
                    trace_id=tid,
                    is_new=is_new,
                    is_changed=is_changed,
                )

                if not dry_run:
                    # Only submit to RAGD if new or changed
                    if is_new or is_changed:
                        ingest_batch.append(str(item.path))

                    _manifest.upsert(ManifestEntry(
                        document_id=doc_id,
                        repo_root=str(repo_root),
                        relative_path=item.relative_path,
                        file_class=file_class,
                        language=language,
                        content_hash=hash_result.content_hash,
                        mtime_ns=item.mtime_ns,
                        size=item.size,
                        indexed_at=int(time.time()),
                        ragd_ingested=prior_entry.ragd_ingested if prior_entry else 0,
                        ragd_ingested_at=prior_entry.ragd_ingested_at if prior_entry else None,
                        status="active",
                    ))

            # Detect deletions: IDs we knew about but didn't see
            deleted_ids = known_ids - seen_ids
            for doc_id in deleted_ids:
                entry = _manifest.get(doc_id)
                if entry is not None:
                    delete_batch.append(str((Path(entry.repo_root) / entry.relative_path).resolve()))
                if not dry_run:
                    _manifest.mark_deleted(doc_id)
                stats.files_deleted += 1
                tracer.event(
                    "file_deleted",
                    trace_id=tid,
                    attrs={"document_id": doc_id},
                )

            if delete_batch and not dry_run:
                with tracer.span("ragd_delete_batch", trace_id=tid, attrs={"count": len(delete_batch)}):
                    delete_result = _bridge.delete_paths(delete_batch)
                    stats.ragd_paths_deleted = delete_result.files_marked_deleted
                    stats.ragd_chunks_deleted = delete_result.chunks_marked_deleted
                    stats.ragd_delete_errors = len(delete_result.errors)
                    if delete_result.skipped:
                        tracer.event(
                            "ragd_delete_skipped",
                            trace_id=tid,
                            attrs={"reason": delete_result.reason or "unknown", "paths": len(delete_batch)},
                        )
                    for error in delete_result.errors:
                        tracer.event(
                            "error",
                            trace_id=tid,
                            attrs={"class": "RagdDeleteError", "message": error.get("error", ""), "path": error.get("path", "")},
                        )

            # Batch ingest into RAGD
            if ingest_batch and not dry_run:
                with tracer.span("ragd_index_batch", trace_id=tid, attrs={"count": len(ingest_batch)}):
                    ingest_result = _bridge.ingest_paths(ingest_batch)
                    if ingest_result.error:
                        stats.ragd_errors += 1
                        tracer.event(
                            "error",
                            trace_id=tid,
                            attrs={"class": "RagdError", "message": ingest_result.error},
                        )
                    else:
                        stats.ragd_chunks_indexed = ingest_result.chunks_indexed
                        # Mark ingested documents
                        for path_str in ingest_batch:
                            path = Path(path_str)
                            try:
                                rel = path.relative_to(repo_root).as_posix()
                                did = document_id_for(str(repo_root), rel)
                                _manifest.mark_ragd_ingested(did)
                            except (ValueError, OSError):
                                pass

        stats.duration_ms = (time.monotonic() - start) * 1000

        if not dry_run and run_id is not None:
            _manifest.finish_scan_run(
                run_id,
                files_seen=stats.files_seen,
                files_new=stats.files_new,
                files_changed=stats.files_changed,
                files_deleted=stats.files_deleted,
            )

    except Exception as exc:
        tracer.event(
            "error",
            trace_id=tid,
            attrs={"class": type(exc).__name__, "message": str(exc)},
        )
        if not dry_run and run_id is not None:
            try:
                _manifest.finish_scan_run(
                    run_id,
                    files_seen=stats.files_seen,
                    files_new=stats.files_new,
                    files_changed=stats.files_changed,
                    files_deleted=stats.files_deleted,
                    status="failed",
                )
            except Exception:
                pass
        raise
    finally:
        tracer.close()

    return stats


def iter_loaded_files(
    repo_root: Path | str,
    *,
    force_full: bool = False,
    trace_id: Optional[str] = None,
    manifest: Optional[Manifest] = None,
    ignore: Optional[Ignore] = None,
) -> Iterator[LoadedFile]:
    """Yield LoadedFile for every indexable file under repo_root.

    Does NOT write to manifest or RAGD. Pure read path for Agent 2 consumption.
    """
    repo_root = Path(repo_root).resolve()
    tid = trace_id or new_trace_id()
    _manifest = manifest or Manifest()
    _ignore = ignore or Ignore(dominionignore_path=repo_root / ".dominionignore")

    for item in discover(repo_root, _ignore, trace_id=tid):
        if isinstance(item, DiscoveryError):
            continue
        if is_likely_binary(item.path):
            continue

        doc_id = document_id_for(str(repo_root), item.relative_path)
        file_class, language = classify(item.path)

        prior_entry = _manifest.get(doc_id)
        prior = (
            PriorEntry(
                content_hash=prior_entry.content_hash,
                mtime_ns=prior_entry.mtime_ns,
                size=prior_entry.size,
            )
            if prior_entry else None
        )

        try:
            hash_result = hash_file(item.path, prior, trace_id=tid, force_full=force_full)
        except OSError:
            continue

        yield LoadedFile(
            path=str(item.path),
            relative_path=item.relative_path,
            repo_root=str(repo_root),
            size=item.size,
            mtime_ns=item.mtime_ns,
            file_class=file_class,
            language=language,
            content_hash=hash_result.content_hash,
            document_id=doc_id,
            trace_id=tid,
            is_new=prior_entry is None,
            is_changed=prior_entry is not None and prior_entry.content_hash != hash_result.content_hash,
        )
