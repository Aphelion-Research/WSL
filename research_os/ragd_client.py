from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests


DEFAULT_RAGD = "http://127.0.0.1:7474"


def health(base_url: str = DEFAULT_RAGD) -> dict[str, Any]:
    try:
        response = requests.get(f"{base_url}/health", timeout=3)
        return {"reachable": response.ok, "status_code": response.status_code, "data": response.json() if response.text else {}}
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


def mcp_call(method: str, params: dict[str, Any] | None = None, base_url: str = DEFAULT_RAGD) -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    response = requests.post(f"{base_url}/mcp", json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def try_index_path(path: Path, base_url: str = DEFAULT_RAGD) -> dict[str, Any]:
    attempts = [
        ("POST /index", lambda: requests.post(f"{base_url}/index", json={"path": str(path)}, timeout=30)),
        ("MCP ragd_index", lambda: requests.post(f"{base_url}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "ragd_index", "arguments": {"path": str(path)}}}, timeout=30)),
    ]
    errors: list[str] = []
    for label, call in attempts:
        try:
            response = call()
            if response.ok:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    data = {"text": response.text}
                return {"ok": True, "method": label, "response": data}
            errors.append(f"{label}: HTTP {response.status_code} {response.text[:200]}")
        except Exception as exc:
            errors.append(f"{label}: {exc}")
    return {"ok": False, "errors": errors}
