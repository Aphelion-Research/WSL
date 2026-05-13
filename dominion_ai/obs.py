from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .safety import redact_path


TRACE_DIR = Path(os.environ.get("DOMINION_TRACE_DIR", str(Path.home() / ".dominion" / "traces"))).expanduser()


def new_trace_id() -> str:
    return uuid.uuid4().hex


def trace_path(trace_id: str) -> Path:
    return TRACE_DIR / f"{trace_id}.jsonl"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        return redact_path(value)
    return value


def emit_span(trace_id: str, name: str, metadata: dict[str, Any] | None = None, *, started_at: float | None = None) -> None:
    if os.environ.get("DOMINION_TRACE", "on").lower() == "off":
        return
    TRACE_DIR.mkdir(parents=True, exist_ok=True)
    now = time.time()
    payload = {
        "trace_id": trace_id,
        "span": name,
        "ts": now,
        "duration_ms": None if started_at is None else round((now - started_at) * 1000, 3),
        "metadata": _redact(metadata or {}),
    }
    with trace_path(trace_id).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


@contextmanager
def span(trace_id: str, name: str, metadata: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    started = time.time()
    data = dict(metadata or {})
    try:
        yield data
        data.setdefault("ok", True)
    except Exception as exc:
        data["ok"] = False
        data["error"] = str(exc)
        raise
    finally:
        emit_span(trace_id, name, data, started_at=started)
