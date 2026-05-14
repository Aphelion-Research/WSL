"""CLI command handlers for dominion_loader.

Used as a thin delegation target from scripts/dominion_cli.py.
Each function signature: (args: argparse.Namespace) -> int
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


ROOT = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser()


def _print_json(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


def cmd_scan(args) -> int:
    """Run dominion_loader scan over the repo."""
    from dominion_loader.scan import scan
    from dominion_loader.manifest import Manifest
    from dominion_loader.obs import _NullTracer, set_tracer

    set_tracer(_NullTracer())
    repo = Path(getattr(args, "repo", None) or ROOT)
    dry_run = getattr(args, "dry_run", False)

    manifest = Manifest()
    try:
        stats = scan(repo, dry_run=dry_run, manifest=manifest)
    finally:
        manifest.close()

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
    from dominion_loader.obs import _NullTracer, set_tracer

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
