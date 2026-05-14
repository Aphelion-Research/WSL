from __future__ import annotations

import argparse
import json

from .graph import build_graph, callees, callers, importers, imports, stats


def _json(data) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dominion graph")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "stats"):
        p = sub.add_parser(name)
        p.add_argument("--json", action="store_true")
    p = sub.add_parser("callers")
    p.add_argument("symbol")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("callees")
    p.add_argument("symbol")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("imports")
    p.add_argument("filepath")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("importers")
    p.add_argument("import_name")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "build":
        result = build_graph()
        payload = {"ok": True, "stats": result.__dict__}
    elif args.command == "stats":
        result = stats()
        payload = {"ok": True, "stats": result.__dict__}
    elif args.command == "callers":
        payload = {"ok": True, "callers": callers(args.symbol)}
    elif args.command == "callees":
        payload = {"ok": True, "callees": callees(args.symbol)}
    elif args.command == "imports":
        payload = {"ok": True, "imports": imports(args.filepath)}
    else:
        payload = {"ok": True, "importers": importers(args.import_name)}
    if args.json:
        _json(payload)
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
