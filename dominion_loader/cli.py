"""CLI command handlers for dominion_loader.

Used as a thin delegation target from scripts/dominion_cli.py.
Each function signature: (args: argparse.Namespace) -> int
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from pathlib import Path


ROOT = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser()


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Native scan helpers
# ---------------------------------------------------------------------------

_NATIVE_KIND_TO_CLASS: dict[str, str] = {
    "document": "doc",
    "source": "code",
    "config": "config",
    "data": "data",
    "binary": "binary",
}


def _native_scan_binary() -> Path:
    """Return path to the native scan binary (may not exist)."""
    candidates = [
        Path(__file__).resolve().parents[1] / "ragd" / "build" / "dominion-native-scan",
        Path(os.environ.get("DOMINION_NATIVE_BIN", "")) / "dominion-native-scan",
    ]
    for p in candidates:
        if p.is_file():
            return p
    # Return first candidate even if it doesn't exist (caller checks .exists())
    return candidates[0]


def _run_native_scan(repo_root: Path) -> dict:
    """Run dominion-native-scan and return parsed JSON output."""
    binary = _native_scan_binary()
    if not binary.is_file():
        raise FileNotFoundError(f"native scan binary not found: {binary}")
    result = subprocess.run(
        [str(binary), "--root", str(repo_root), "--json"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"native scan failed (exit {result.returncode}): {result.stderr[:200]}")
    return json.loads(result.stdout)


def cmd_scan_native(args) -> int:
    """Run scan using native C++ binary for file discovery and hashing."""
    from dominion_loader.hashing import document_id_for
    from dominion_loader.manifest import Manifest, ManifestEntry
    from dominion_loader.obs import _NullTracer, get_tracer, set_tracer
    from dominion_loader.ragd_bridge import RagdBridge

    previous_tracer = get_tracer()
    set_tracer(_NullTracer())
    dry_run = getattr(args, "dry_run", False)
    repo = Path(getattr(args, "repo", None) or ROOT).resolve()

    try:
        native_data = _run_native_scan(repo)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"native scan unavailable, falling back to Python scan: {exc}", file=sys.stderr)
        args.native = False  # clear flag then delegate
        return cmd_scan(args)

    native_files: list[dict] = native_data.get("files", [])
    native_errors: list = native_data.get("errors", [])

    manifest = Manifest()
    bridge = RagdBridge()
    start = time.monotonic()

    files_seen = len(native_files)
    files_new = files_changed = files_skipped = files_error = 0
    ingest_batch: list[str] = []
    seen_ids: set[str] = set()

    known_ids = manifest.list_all_document_ids(str(repo))

    try:
        if not dry_run:
            from dominion_loader.obs import new_trace_id
            trace_id = new_trace_id()
            manifest.start_scan_run(trace_id, str(repo))
        else:
            trace_id = "dry-run"

        for nf in native_files:
            rel_path: str = nf["relative_path"]
            file_class: str = _NATIVE_KIND_TO_CLASS.get(nf.get("kind", ""), "unknown")
            if file_class == "binary":
                files_skipped += 1
                continue

            doc_id = document_id_for(str(repo), rel_path)
            seen_ids.add(doc_id)

            content_hash: str = nf.get("content_hash", "")
            mtime_ns: int = int(nf.get("mtime_ns", 0))
            size: int = int(nf.get("size_bytes", 0))
            language: str = nf.get("language", "unknown")

            prior_entry = manifest.get(doc_id)
            is_new = prior_entry is None
            is_changed = (not is_new) and (prior_entry.content_hash != content_hash)

            if is_new:
                files_new += 1
            elif is_changed:
                files_changed += 1

            if not dry_run:
                if is_new or is_changed:
                    ingest_batch.append(nf["absolute_path"])
                manifest.upsert(ManifestEntry(
                    document_id=doc_id,
                    repo_root=str(repo),
                    relative_path=rel_path,
                    file_class=file_class,
                    language=language,
                    content_hash=content_hash,
                    mtime_ns=mtime_ns,
                    size=size,
                    indexed_at=int(time.time()),
                    ragd_ingested=prior_entry.ragd_ingested if prior_entry else 0,
                    ragd_ingested_at=prior_entry.ragd_ingested_at if prior_entry else None,
                    status="active",
                ))

        # Deletions
        files_deleted = 0
        deleted_ids = known_ids - seen_ids
        delete_batch: list[str] = []
        for doc_id in deleted_ids:
            entry = manifest.get(doc_id)
            if entry is not None:
                delete_batch.append(str((Path(entry.repo_root) / entry.relative_path).resolve()))
            if not dry_run:
                manifest.mark_deleted(doc_id)
            files_deleted += 1

        ragd_chunks_indexed = ragd_errors = ragd_paths_deleted = ragd_chunks_deleted = ragd_delete_errors = 0
        if not dry_run:
            if ingest_batch:
                ingest_result = bridge.ingest_paths(ingest_batch)
                ragd_chunks_indexed = ingest_result.chunks_indexed
                ragd_errors = ingest_result.errors
            if delete_batch:
                delete_result = bridge.delete_paths(delete_batch)
                ragd_paths_deleted = delete_result.files_marked_deleted
                ragd_chunks_deleted = delete_result.chunks_deleted
                ragd_delete_errors = delete_result.errors
    finally:
        manifest.close()

    duration_ms = (time.monotonic() - start) * 1000
    data = {
        "trace_id": trace_id,
        "repo_root": str(repo),
        "native": True,
        "files_seen": files_seen,
        "files_new": files_new,
        "files_changed": files_changed,
        "files_deleted": files_deleted,
        "files_skipped": files_skipped,
        "files_error": files_error + len(native_errors),
        "ragd_chunks_indexed": ragd_chunks_indexed,
        "ragd_errors": ragd_errors,
        "ragd_paths_deleted": ragd_paths_deleted,
        "ragd_chunks_deleted": ragd_chunks_deleted,
        "ragd_delete_errors": ragd_delete_errors,
        "duration_ms": round(duration_ms, 1),
        "dry_run": dry_run,
    }
    if getattr(args, "json", False):
        _print_json(data)
    else:
        prefix = "[DRY RUN] " if dry_run else ""
        print(
            f"{prefix}native scan complete: seen={data['files_seen']} new={files_new} "
            f"changed={files_changed} deleted={files_deleted} "
            f"skipped={files_skipped} errors={data['files_error']} "
            f"ragd_chunks={ragd_chunks_indexed} ({duration_ms:.0f}ms)"
        )
    return 0


def cmd_scan(args) -> int:
    """Run dominion_loader scan over the repo."""
    if getattr(args, "native", False):
        return cmd_scan_native(args)

    from dominion_loader.scan import scan
    from dominion_loader.manifest import Manifest
    from dominion_loader.obs import _NullTracer, get_tracer, set_tracer

    previous_tracer = get_tracer()
    set_tracer(_NullTracer())
    try:
        repo = Path(getattr(args, "repo", None) or ROOT)
        dry_run = getattr(args, "dry_run", False)

        manifest = Manifest()
        try:
            stats = scan(repo, dry_run=dry_run, manifest=manifest)
        finally:
            manifest.close()
    finally:
        set_tracer(previous_tracer)

    data = {
        "trace_id": stats.trace_id,
        "repo_root": stats.repo_root,
        "files_seen": stats.files_seen,
        "files_new": stats.files_new,
        "files_changed": stats.files_changed,
        "files_deleted": stats.files_deleted,
        "files_skipped": stats.files_skipped,
        "files_error": stats.files_error,
        "ragd_chunks_indexed": stats.ragd_chunks_indexed,
        "ragd_errors": stats.ragd_errors,
        "ragd_paths_deleted": stats.ragd_paths_deleted,
        "ragd_chunks_deleted": stats.ragd_chunks_deleted,
        "ragd_delete_errors": stats.ragd_delete_errors,
        "duration_ms": round(stats.duration_ms, 1),
        "dry_run": dry_run,
    }

    if getattr(args, "json", False):
        _print_json(data)
    else:
        prefix = "[DRY RUN] " if dry_run else ""
        print(
            f"{prefix}scan complete: seen={stats.files_seen} new={stats.files_new} "
            f"changed={stats.files_changed} deleted={stats.files_deleted} "
            f"skipped={stats.files_skipped} errors={stats.files_error} "
            f"ragd_chunks={stats.ragd_chunks_indexed} "
            f"ragd_deleted={stats.ragd_chunks_deleted} ({stats.duration_ms:.0f}ms)"
        )
    return 0


def cmd_cache(args) -> int:
    """Manage the dominion_loader cache."""
    from dominion_loader.cache import Cache

    cache = Cache()
    sub = getattr(args, "cache_command", "stats")

    if sub == "stats":
        stats = cache.stats()
        if getattr(args, "json", False):
            _print_json(stats)
        else:
            print(f"cache entries={stats['entries']} bytes={stats['bytes']}")
        return 0

    if sub == "verify":
        results = cache.verify()
        if getattr(args, "json", False):
            _print_json({"corrupt": results, "count": len(results)})
        else:
            if results:
                print(f"WARN: {len(results)} corrupt cache entries:")
                for r in results:
                    print(f"  {r['path']}: {r['error']}")
            else:
                print("cache OK: no corrupt entries")
        return 1 if results else 0

    if sub == "nuke":
        count = cache.nuke()
        if getattr(args, "json", False):
            _print_json({"deleted": count})
        else:
            print(f"cache nuke: deleted {count} entries")
        return 0

    return 0


def cmd_manifest(args) -> int:
    """Inspect the dominion_loader manifest."""
    import datetime
    from dominion_loader.manifest import Manifest
    from dominion_loader.obs import _NullTracer, get_tracer, set_tracer

    previous_tracer = get_tracer()
    set_tracer(_NullTracer())
    manifest = Manifest()
    sub = getattr(args, "manifest_command", "list")

    try:
        if sub == "list":
            since_iso = getattr(args, "changed_since", None)
            if since_iso:
                try:
                    epoch = int(datetime.datetime.fromisoformat(since_iso).timestamp())
                    entries = list(manifest.list_changed_since(epoch))
                except ValueError:
                    print(f"Invalid ISO timestamp: {since_iso}", file=sys.stderr)
                    return 1
            else:
                entries = list(manifest.list_active())

            if getattr(args, "json", False):
                _print_json([{
                    "document_id": e.document_id,
                    "relative_path": e.relative_path,
                    "file_class": e.file_class,
                    "language": e.language,
                    "content_hash": e.content_hash[:8] + "...",
                    "status": e.status,
                    "ragd_ingested": bool(e.ragd_ingested),
                } for e in entries])
            else:
                print(f"Manifest entries: {len(entries)}")
                for e in entries[:50]:
                    print(f"  [{e.file_class}/{e.language}] {e.relative_path}")
                if len(entries) > 50:
                    print(f"  ... ({len(entries) - 50} more)")

        elif sub == "stats":
            stats = manifest.stats()
            if getattr(args, "json", False):
                _print_json(stats)
            else:
                for k, v in stats.items():
                    print(f"  {k}: {v}")

    finally:
        manifest.close()
        set_tracer(previous_tracer)

    return 0


def cmd_loader_bench(args) -> int:
    """Run dominion_loader benchmark suite."""
    from dominion_loader.bench import run_suite, list_suites

    suite_name = getattr(args, "suite", "foundation")
    runs = getattr(args, "runs", 3)
    out_dir_str = getattr(args, "out", None)
    out_dir = Path(out_dir_str) if out_dir_str else None

    try:
        result = run_suite(suite_name, runs=runs, out_dir=out_dir)
    except KeyError as exc:
        available = list_suites()
        print(f"Unknown suite: {exc}. Available: {available}", file=sys.stderr)
        return 1

    if getattr(args, "json", False):
        _print_json(result)
    else:
        print(f"Benchmark: {result['suite']} ({result['runs']} runs)")
        for name, m in result["metrics"].items():
            print(f"  {name}: p50={m['p50']:.3f} p95={m['p95']:.3f} {m['unit']}")
    return 0


def cmd_loader_ledger(args) -> int:
    """Append an entry to the multi-agent memory ledger."""
    from dominion_loader.ledger import Ledger

    sub = getattr(args, "loader_ledger_command", "append")

    if sub == "append":
        kind = getattr(args, "kind", None)
        payload_str = getattr(args, "payload", "{}")

        if not kind:
            print("--kind is required", file=sys.stderr)
            return 1

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON payload: {exc}", file=sys.stderr)
            return 1

        ledger = Ledger()
        try:
            eid = ledger.append(kind, payload)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        finally:
            ledger.close()

        if getattr(args, "json", False):
            _print_json({"entry_id": eid, "kind": kind})
        else:
            print(f"ledger append: kind={kind} entry_id={eid}")

    elif sub == "stats":
        ledger = Ledger()
        try:
            stats = ledger.stats()
        finally:
            ledger.close()
        if getattr(args, "json", False):
            _print_json(stats)
        else:
            for k, v in stats.items():
                print(f"  {k}: {v}")

    return 0


def cmd_graph_foundation(args) -> int:
    """Foundation graph commands: stats, build."""
    from dominion_loader.graph import KnowledgeGraph

    sub = getattr(args, "graph_foundation_command", "stats")
    kg = KnowledgeGraph()

    try:
        if sub == "stats":
            stats = kg.stats()
            if getattr(args, "json", False):
                _print_json(stats)
            else:
                print(f"graph nodes={stats['nodes']} edges={stats['edges']}")
                if stats.get("by_kind"):
                    for kind, count in stats["by_kind"].items():
                        print(f"  {kind}: {count}")

        elif sub == "build":
            from dominion_loader.graph import ingest_from_ragd
            ragd_db = Path(os.environ.get("RAGD_DB", str(Path.home() / ".ragd" / "ragd.db")))
            result = ingest_from_ragd(kg, ragd_db)
            if getattr(args, "json", False):
                _print_json(result)
            else:
                print(f"graph build: nodes_added={result.get('nodes', 0)} edges_added={result.get('edges', 0)}")
    finally:
        kg.close()

    return 0
