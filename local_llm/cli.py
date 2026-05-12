from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ollama import extract_claims, health, list_models, query_expand, summarize, tag


def _read(value: str) -> str:
    path = Path(value)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return value


def _print(result: dict[str, object]) -> int:
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


def cmd_doctor(args: argparse.Namespace) -> int:
    result = health()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result.get("ok"):
        print("Manual setup, if desired: ollama pull qwen2.5:3b; ollama pull llama3.2:3b; ollama pull nomic-embed-text")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    return _print(list_models())


def cmd_summarize(args: argparse.Namespace) -> int:
    return _print(summarize(_read(args.file_or_text)[: args.max_chars]))


def cmd_tag(args: argparse.Namespace) -> int:
    return _print(tag(_read(args.file_or_text)[: args.max_chars]))


def cmd_claims(args: argparse.Namespace) -> int:
    return _print(extract_claims(_read(args.file_or_text)[: args.max_chars]))


def cmd_query_expand(args: argparse.Namespace) -> int:
    return _print(query_expand(args.text))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llm", description="Dominion local LLM adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("doctor")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("list")
    p.set_defaults(func=cmd_list)

    for name, func in (("summarize", cmd_summarize), ("tag", cmd_tag), ("claims", cmd_claims)):
        p = sub.add_parser(name)
        p.add_argument("file_or_text")
        p.add_argument("--max-chars", type=int, default=8000)
        p.set_defaults(func=func)

    p = sub.add_parser("query-expand")
    p.add_argument("text")
    p.set_defaults(func=cmd_query_expand)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
