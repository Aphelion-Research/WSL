from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .api import ask
from .bench import run_suite
from .eval import run_eval
from .ledger import entries_to_dict, list_entries, search_entries, show_entry
from .planner import plan
from .ragd_client import RagdClient, RagdError, chunk_by_id, chunk_to_json
from .rerank import rerank
from .retrieval import retrieve
from .trace import latest_traces, render_trace


def print_json(data: object) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_search(args) -> int:
    try:
        retrieval_plan = plan(args.query, {"top_k": args.top_k, "mode": args.mode, "rerank_strategy": args.rerank})
        chunks = rerank(retrieval_plan, retrieve(retrieval_plan))[: args.top_k]
    except RagdError as exc:
        payload = {"ok": False, "error": str(exc)}
        print_json(payload) if args.json else print(payload["error"])
        return 2
    payload = {"ok": True, "trace_id": retrieval_plan.trace_id, "query": args.query, "results": [chunk_to_json(chunk) for chunk in chunks]}
    if args.json:
        print_json(payload)
    else:
        print(f"trace_id: {retrieval_plan.trace_id}")
        for chunk in chunks:
            print(f"{chunk.score:.4f} conf={chunk.confidence:.2f} rerank={chunk.rerank_score:.2f} {chunk.filepath}:{chunk.line_start}-{chunk.line_end} [{chunk.chunk_id}]")
    return 0


def cmd_ask(args) -> int:
    try:
        result = ask(args.query, generate=args.generate, budget=args.budget)
    except RagdError as exc:
        payload = {"ok": False, "error": str(exc)}
        print_json(payload) if args.json else print(payload["error"])
        return 2
    if args.json:
        print_json(result.to_dict())
    else:
        print(result.answer)
        print(f"\ntrace_id: {result.trace_id}")
    return 0 if result.ok else 1


def cmd_explain(args) -> int:
    found = chunk_by_id(str(args.chunk))
    payload = {
        "ok": bool(found),
        "chunk": None if found is None else chunk_to_json(found),
        "why": None if found is None else "Read from RAGD chunk store by chunk_id; provenance is RAGD filepath, line range, symbol, type, and content_hash.",
    }
    if args.json:
        print_json(payload)
    elif found:
        print(f"{found.filepath}:{found.line_start}-{found.line_end} [{found.chunk_id}]")
        print(f"type={found.chunk_type} symbol={found.symbol_name} hash={found.content_hash}")
        print(payload["why"])
    else:
        print(f"chunk not found: {args.chunk}")
    return 0 if found else 1


def cmd_trace(args) -> int:
    try:
        spans = render_trace(args.trace_id)
    except FileNotFoundError as exc:
        print_json({"ok": False, "error": str(exc)}) if args.json else print(str(exc))
        return 1
    if args.json:
        from .trace import load_trace

        print_json({"ok": True, "trace_id": args.trace_id, "spans": load_trace(args.trace_id)})
    else:
        print(spans)
    return 0


def cmd_eval(args) -> int:
    result = run_eval(args.bundle, top_k=args.top_k)
    print_json(result)
    return 0


def cmd_ledger(args) -> int:
    if args.ledger_command == "show":
        entry = show_entry(args.entry_id)
        payload = {"ok": entry is not None, "entry": None if entry is None else asdict(entry)}
    elif args.ledger_command == "search":
        payload = {"ok": True, "entries": entries_to_dict(search_entries(args.query, limit=args.limit))}
    else:
        payload = {"ok": True, "entries": entries_to_dict(list_entries(kind=args.kind, session=args.session, tag=args.tag, since=args.since, limit=args.limit))}
    if args.json:
        print_json(payload)
    else:
        for entry in payload.get("entries", []):
            print(f"{entry['id']} {entry['kind']} {entry['created_at']} {entry['filepath']}: {entry['text'][:120]}")
        if payload.get("entry"):
            entry = payload["entry"]
            print(f"{entry['id']} {entry['kind']} {entry['created_at']}\n{entry['text']}")
    return 0 if payload["ok"] else 1


def cmd_graph(args) -> int:
    client = RagdClient()
    if args.graph_command in {"neighbors", "query", "subgraph"}:
        payload = client.graph_symbols(root=getattr(args, "node", "") or getattr(args, "from_file", "") or getattr(args, "label", ""), depth=args.depth)
    elif args.graph_command in {"build", "stats", "callers", "callees", "imports", "importers"}:
        from ragd_graph.graph import build_graph, callees, callers, importers, imports, stats

        if args.graph_command == "build":
            payload = {"ok": True, "stats": asdict(build_graph())}
        elif args.graph_command == "stats":
            payload = {"ok": True, "stats": asdict(stats())}
        elif args.graph_command == "callers":
            payload = {"ok": True, "callers": callers(args.symbol or "")}
        elif args.graph_command == "callees":
            payload = {"ok": True, "callees": callees(args.symbol or "")}
        elif args.graph_command == "imports":
            payload = {"ok": True, "imports": imports(args.filepath or "")}
        else:
            payload = {"ok": True, "importers": importers(args.filepath or "")}
    else:
        payload = {"ok": False, "error": "unknown graph command"}
    print_json(payload) if args.json else print_json(payload)
    return 0


def cmd_bench(args) -> int:
    print_json(run_suite(args.suite, iterations=args.iterations))
    return 0


def latest_queries_panel(limit: int = 5) -> str:
    lines = []
    for path in latest_traces(limit):
        lines.append(path.stem)
    return "\n".join(lines) if lines else "no query traces"


def latest_decisions_panel(limit: int = 5) -> str:
    entries = list_entries(kind="decision", limit=limit)
    return "\n".join(f"{entry.id} {entry.created_at} {entry.text[:100]}" for entry in entries) if entries else "no decisions"
