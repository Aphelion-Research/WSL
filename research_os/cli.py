from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from . import __version__
from . import db
from .adapters.registry import available_adapters, default_config, resolve_adapter
from .config import ensure_dirs, load_sources, paths, upsert_source_yaml, write_default_sources
from .fetcher import validate_url_for_source
from .models import Source
from .quality import assess_quality
from .extractor import extract
from .chunker import chunk_markdown
from .ragd_client import health as ragd_health, try_index_path
from .scheduler import run as run_scheduler


def _conn():
    p = paths()
    ensure_dirs(p)
    conn = db.connect(p.db)
    db.initialize(conn)
    return conn


def _sync_sources(conn) -> None:
    write_default_sources()
    db.import_sources(conn, load_sources())


def cmd_init(args: argparse.Namespace) -> int:
    p = paths()
    ensure_dirs(p)
    write_default_sources(p.sources_yaml)
    conn = db.connect(p.db)
    db.initialize(conn)
    _sync_sources(conn)
    print(f"Research OS initialized at {p.research}")
    print(f"Database: {p.db}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    conn = _conn()
    _sync_sources(conn)
    counts = db.counts(conn)
    if args.json:
        print(json.dumps({"version": __version__, "counts": counts, "db": str(paths().db)}, indent=2, sort_keys=True))
    else:
        print("Research OS Status")
        print(f"db: {paths().db}")
        for key, value in counts.items():
            print(f"{key}: {value}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    conn = _conn()
    _sync_sources(conn)
    p = paths()
    data = {
        "root": str(p.root),
        "db": str(p.db),
        "db_exists": p.db.exists(),
        "sources_yaml": str(p.sources_yaml),
        "sources_yaml_exists": p.sources_yaml.exists(),
        "python": shutil.which("python") or "",
        "directories": {"raw": p.raw.exists(), "markdown": p.markdown.exists(), "extracted": p.extracted.exists()},
        "adapters": sorted(available_adapters().keys()),
    }
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print("Research OS Doctor")
        print(f"root: {p.root}")
        print(f"db: {'ok' if p.db.exists() else 'missing'}")
        print(f"sources_yaml: {'ok' if p.sources_yaml.exists() else 'missing'}")
        print(f"python: {data['python'] or 'unavailable'}")
        print(f"directories: raw={p.raw.exists()} markdown={p.markdown.exists()} extracted={p.extracted.exists()}")
        print(f"adapters: {', '.join(data['adapters'])}")
    return 0


def cmd_add_source(args: argparse.Namespace) -> int:
    conn = _conn()
    source = Source(args.name, args.base_url, args.trust, args.rate_limit_sec, True, args.adapter_preference)
    db.upsert_source(conn, source)
    upsert_source_yaml(source)
    print(f"source added: {source.name} {source.base_url}")
    return 0


def cmd_list_sources(args: argparse.Namespace) -> int:
    conn = _conn()
    _sync_sources(conn)
    rows = db.list_sources(conn)
    if args.json:
        print(json.dumps([dict(row) for row in rows], indent=2, sort_keys=True))
    else:
        for row in rows:
            enabled = "enabled" if row["enabled"] else "disabled"
            print(f"{row['name']}\t{row['trust']}\t{enabled}\t{row['rate_limit_sec']}s\t{row['base_url']}")
    return 0


def cmd_add_url(args: argparse.Namespace) -> int:
    conn = _conn()
    _sync_sources(conn)
    row = db.get_source(conn, args.source)
    if not row:
        print(f"source not found: {args.source}")
        return 2
    source = Source(
        row["name"],
        row["base_url"],
        row["trust"],
        float(row["rate_limit_sec"]),
        bool(row["enabled"]),
        str(row["adapter_preference"] or "requests"),
    )
    try:
        validate_url_for_source(args.url, source)
    except Exception as exc:
        print(f"rejected: {exc}")
        return 2
    db.add_job(conn, args.url, args.source, args.priority)
    print(f"queued: {args.url}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    conn = _conn()
    _sync_sources(conn)
    result = run_scheduler(args.limit)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["failed"] == 0 else 1


def cmd_list(args: argparse.Namespace) -> int:
    conn = _conn()
    rows = db.list_documents(conn, args.limit)
    for row in rows:
        print(f"{row['id']}\t{row['source_name']}\t{row['fetched_at']}\t{row['title']}\t{row['url']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    conn = _conn()
    row = db.get_document(conn, args.document_id)
    if not row:
        print(f"document not found: {args.document_id}")
        return 2
    print(json.dumps(dict(row), indent=2, sort_keys=True))
    if row["markdown_path"] and Path(row["markdown_path"]).exists():
        text = Path(row["markdown_path"]).read_text(encoding="utf-8", errors="replace")
        print("\n--- markdown preview ---")
        print(text[: args.chars])
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    conn = _conn()
    rows = db.search_chunks(conn, args.text, args.limit)
    for row in rows:
        print(f"[{row['document_id']}:{row['chunk_index']}] {row['title']} {row['url']}")
        print(row["content"][: args.chars].strip())
        print()
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    conn = _conn()
    row = db.get_document(conn, args.document_id)
    if not row:
        print(f"document not found: {args.document_id}")
        return 2
    text = Path(row["markdown_path"]).read_text(encoding="utf-8", errors="replace") if row["markdown_path"] else ""
    from .ollama_client import summarize

    result = summarize(text[:8000])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def cmd_ingest_ragd(args: argparse.Namespace) -> int:
    conn = _conn()
    p = paths()
    bundle = p.extracted / "ragd_ingest"
    bundle.mkdir(parents=True, exist_ok=True)
    rows = db.list_documents(conn, 10000)
    written = 0
    for row in rows:
        markdown_path = Path(row["markdown_path"] or "")
        if not markdown_path.exists():
            continue
        target = bundle / f"document-{row['id']}.md"
        target.write_text(markdown_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        written += 1
    before = ragd_health()
    index_result = try_index_path(bundle) if written else {"ok": False, "errors": ["no documents to ingest"]}
    after = ragd_health()
    print(json.dumps({"bundle": str(bundle), "files_written": written, "ragd_before": before, "index": index_result, "ragd_after": after}, indent=2, sort_keys=True))
    return 0 if written else 1


def cmd_ragd_status(args: argparse.Namespace) -> int:
    conn = _conn()
    status = ragd_health()
    counts = db.counts(conn)
    print(json.dumps({"ragd": status, "research": counts}, indent=2, sort_keys=True))
    return 0 if status.get("reachable") else 1


def cmd_adapters(args: argparse.Namespace) -> int:
    adapters = available_adapters()
    if args.json:
        print(json.dumps({"adapters": sorted(adapters.keys())}, indent=2, sort_keys=True))
    else:
        for name in sorted(adapters.keys()):
            print(name)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    conn = _conn()
    _sync_sources(conn)
    row = db.get_source(conn, args.source)
    if not row:
        print(f"source not found: {args.source}")
        return 2
    source = Source(
        name=row["name"],
        base_url=row["base_url"],
        trust=row["trust"],
        rate_limit_sec=float(row["rate_limit_sec"]),
        enabled=bool(row["enabled"]),
        adapter_preference=str(row["adapter_preference"] or "requests"),
    )
    adapter_name = args.adapter or source.adapter_preference
    adapter = resolve_adapter(adapter_name)
    if adapter is None:
        print(json.dumps({"ok": False, "error": f"unknown adapter: {adapter_name}", "adapters": sorted(available_adapters().keys())}, indent=2, sort_keys=True))
        return 2

    result = adapter.fetch(args.url, source, default_config())
    if args.json:
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    if not result.ok:
        print(f"FAIL adapter={result.adapter_name} error_class={result.error_class} error={result.error}")
        return 1
    extracted = extract(
        result.text,
        url=result.url,
        final_url=result.final_url,
        source_name=source.name,
        fetched_at_utc=result.fetched_at_utc,
        content_hash=result.content_hash,
        trust=source.trust,
        adapter_name=result.adapter_name,
        content_type=result.content_type,
    )
    chunks = chunk_markdown(extracted.markdown)
    quality = assess_quality(
        fetch_ok=True,
        source_allowed=True,
        text_length=extracted.text_length,
        has_title=bool(extracted.title and extracted.title != "Untitled"),
        chunk_count=len(chunks),
        duplicate_content_hash=False,
        adapter_used=result.adapter_name,
        error_class=None,
    )
    print(f"OK adapter={result.adapter_name} status={result.status_code} content_type={result.content_type} bytes={len(result.text)}")
    print(f"title: {extracted.title}")
    print(f"chunks: {len(chunks)} quality_score: {quality.score}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="research", description="Dominion Research OS CLI")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("doctor")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("add-source")
    p.add_argument("name")
    p.add_argument("base_url")
    p.add_argument("--trust", required=True)
    p.add_argument("--rate-limit-sec", type=float, default=2.0)
    p.add_argument("--adapter-preference", default="requests")
    p.set_defaults(func=cmd_add_source)

    p = sub.add_parser("list-sources")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list_sources)

    p = sub.add_parser("add-url")
    p.add_argument("url")
    p.add_argument("--source", required=True)
    p.add_argument("--priority", type=int, default=5)
    p.set_defaults(func=cmd_add_url)

    p = sub.add_parser("run")
    p.add_argument("--limit", type=int, default=1)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("list")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show")
    p.add_argument("document_id", type=int)
    p.add_argument("--chars", type=int, default=2000)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("query")
    p.add_argument("text")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--chars", type=int, default=600)
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("summarize")
    p.add_argument("document_id", type=int)
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("ingest-ragd")
    p.set_defaults(func=cmd_ingest_ragd)

    p = sub.add_parser("ragd-status")
    p.set_defaults(func=cmd_ragd_status)

    p = sub.add_parser("adapters")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_adapters)

    p = sub.add_parser("fetch")
    p.add_argument("url")
    p.add_argument("--source", required=True)
    p.add_argument("--adapter", default="")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_fetch)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
