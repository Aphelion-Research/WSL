#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from urllib.request import Request, urlopen


def query(task: str, top_k: int) -> dict:
    payload = {"q": task, "top_k": top_k, "mode": "hybrid"}
    request = Request("http://127.0.0.1:7474/query", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(prog="codexrag", description="Build a RAGD context preamble for Codex")
    parser.add_argument("task", nargs="+")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    task = " ".join(args.task)
    data = query(task, args.top_k)
    print("Codex RAGD Context")
    print(f"Task: {task}")
    print("\nStart every session with:")
    print("- call ragd_handoff_read")
    print("- call ragd_query for task context")
    print("- inspect files before edits")
    print("- validate and call ragd_remember for important decisions")
    print("\nTop RAGD chunks:")
    for item in data.get("results", []):
        print(f"- {item.get('filepath')}:{item.get('line_start')} {item.get('symbol_name')} score={item.get('score')}")
        print((item.get("content") or "").strip()[:700])
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
