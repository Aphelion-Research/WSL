from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .obs import trace_path


def load_trace(trace_id: str) -> list[dict[str, Any]]:
    path = trace_path(trace_id)
    if not path.exists():
        raise FileNotFoundError(f"trace not found: {path}")
    spans: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                spans.append(json.loads(line))
    return spans


def render_trace(trace_id: str) -> str:
    spans = load_trace(trace_id)
    lines = [f"Trace {trace_id}", "=" * 72]
    for span in spans:
        duration = span.get("duration_ms")
        suffix = "" if duration is None else f" {duration}ms"
        lines.append(f"- {span.get('span')}{suffix}")
        metadata = span.get("metadata") or {}
        for key in ("query", "top_k", "strategy", "candidates", "budget", "score", "decision", "ok", "error"):
            if key in metadata:
                lines.append(f"  {key}: {metadata[key]}")
    return "\n".join(lines)


def latest_traces(limit: int = 5) -> list[Path]:
    root = trace_path("dummy").parent
    if not root.exists():
        return []
    return sorted(root.glob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]
