#!/usr/bin/env python3
"""
Tiny, safe smoke test for the local RAGD HTTP health endpoint.

- Uses only Python standard library.
- Reads http://127.0.0.1:7474/health
- Prints a few key fields and exits non-fatally on connection errors.
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def _get_json(url: str, timeout_s: float = 2.0) -> dict:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": "ragd-mcp-smoke/1.0 (stdlib urllib)",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        raw = response.read()
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON from {url}: {exc}") from exc


def main() -> int:
    print("RAGD MCP smoke test")

    url = "http://127.0.0.1:7474/health"
    try:
        payload = _get_json(url)
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        print(f"error: could not reach {url}: {exc}")
        return 0
    except ValueError as exc:
        print(f"error: {exc}")
        return 0

    # Be tolerant to schema drift: print requested keys if present.
    for key in ("ok", "ragd_version", "active_chunks", "todos"):
        value = payload.get(key)
        print(f"{key}: {value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

