"""RAGD daemon client for episodic memory."""
from __future__ import annotations

import json
from typing import Any

from hydra.config import RAGD_URL


def _get_client():
    import httpx
    return httpx.Client(base_url=RAGD_URL, timeout=2.0)


def remember(kind: str, payload: dict) -> bool:
    """Ingest a memory into RAGD."""
    try:
        cli = _get_client()
        r = cli.post("/ingest", json={
            "kind": kind,
            "text": json.dumps(payload),
            "ts": payload.get("ts"),
        })
        return r.status_code == 200
    except Exception:
        return False


def recall(query_text: str, k: int = 10) -> list[dict]:
    """Retrieve k nearest memories from RAGD."""
    try:
        cli = _get_client()
        r = cli.post("/query", json={"q": query_text, "k": k, "mode": "hybrid"})
        if r.status_code == 200:
            return r.json().get("hits", [])
    except Exception:
        pass
    return []


def emit_event(event_type: str, data: dict) -> bool:
    """Post event to RAGD WebSocket bus."""
    try:
        cli = _get_client()
        r = cli.post("/events", json={"type": event_type, "data": data})
        return r.status_code == 200
    except Exception:
        return False
