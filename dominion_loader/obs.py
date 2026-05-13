"""Observability: JSONL trace spans and events for dominion_loader.

Design: lightweight, offline-safe, no external dependencies.
Spans and events are written to ~/.dominion/traces/<trace_id>.jsonl.
Feature flag: DOMINION_TRACE=off disables all I/O (still provides the API).

Trace span schema:
  {"event":"span","trace_id":"...","span":"...","start_ns":...,"end_ns":...,"attrs":{...}}

Event schema:
  {"event":"<type>","trace_id":"...","attrs":{...},"ts_ns":...}

INTERFACE(agent-1): Tracer, Span, get_tracer()  (consumed by Agent 2 via trace_id)
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def _traces_dir() -> Path:
    dominion_home = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
    return dominion_home / "traces"


def new_trace_id() -> str:
    """Generate a 128-bit (32 hex char) trace ID."""
    return uuid.uuid4().hex  # 128-bit → no collision concern


class Tracer:
    """Writes trace spans and events to a per-trace JSONL file.

    Thread-safe via a per-file lock.
    No global mutable state — each Tracer owns its file handle lifecycle.
    """

    def __init__(self, trace_id: str, *, enabled: bool = True) -> None:
        self.trace_id = trace_id
        self._enabled = enabled and os.environ.get("DOMINION_TRACE", "on").lower() != "off"
        self._lock = threading.Lock()
        self._file: Any = None

        if self._enabled:
            traces_dir = _traces_dir()
            traces_dir.mkdir(parents=True, exist_ok=True)
            self._path = traces_dir / f"{trace_id}.jsonl"
            self._file = open(self._path, "a", encoding="utf-8", buffering=1)  # line-buffered

    def _write(self, record: dict[str, Any]) -> None:
        if not self._enabled or self._file is None:
            return
        with self._lock:
            self._file.write(json.dumps(record, separators=(",", ":")) + "\n")

    @contextmanager
    def span(
        self,
        name: str,
        *,
        trace_id: str = "",
        attrs: dict[str, Any] | None = None,
    ) -> Iterator[None]:
        """Context manager that emits open/close span records."""
        tid = trace_id or self.trace_id
        start_ns = time.monotonic_ns()
        try:
            yield
        finally:
            end_ns = time.monotonic_ns()
            self._write({
                "event": "span",
                "trace_id": tid,
                "span": name,
                "start_ns": start_ns,
                "end_ns": end_ns,
                "duration_ms": (end_ns - start_ns) / 1_000_000,
                "attrs": attrs or {},
            })

    def event(
        self,
        event_type: str,
        *,
        trace_id: str = "",
        attrs: dict[str, Any] | None = None,
    ) -> None:
        """Emit a point-in-time event record."""
        self._write({
            "event": event_type,
            "trace_id": trace_id or self.trace_id,
            "ts_ns": time.monotonic_ns(),
            "attrs": attrs or {},
        })

    def close(self) -> None:
        """Flush and close the trace file."""
        if self._file is not None:
            with self._lock:
                self._file.flush()
                self._file.close()
                self._file = None

    def __enter__(self) -> "Tracer":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()


class _NullTracer:
    """No-op tracer used when DOMINION_TRACE=off or in tests."""

    def __init__(self) -> None:
        self.trace_id = ""

    @contextmanager
    def span(self, name: str, *, trace_id: str = "", attrs: dict | None = None) -> Iterator[None]:
        yield

    def event(self, event_type: str, *, trace_id: str = "", attrs: dict | None = None) -> None:
        pass

    def close(self) -> None:
        pass

    def __enter__(self) -> "_NullTracer":
        return self

    def __exit__(self, *_: Any) -> None:
        pass


# Thread-local singleton — each thread/scan gets its own tracer via get_tracer()
_local = threading.local()


def get_tracer() -> Tracer | _NullTracer:
    """Return the active tracer for the current thread.

    Returns a NullTracer if no tracer has been set (safe for library use).
    """
    return getattr(_local, "tracer", _NullTracer())


def set_tracer(tracer: Tracer | _NullTracer) -> None:
    """Set the active tracer for the current thread."""
    _local.tracer = tracer


def make_tracer(*, trace_id: str | None = None, enabled: bool = True) -> Tracer:
    """Create and register a new tracer for the current thread."""
    tid = trace_id or new_trace_id()
    tracer = Tracer(tid, enabled=enabled)
    set_tracer(tracer)
    return tracer


# Convenience: a Span context manager as a free function
class Span:
    """Convenience wrapper: ``with Span("name", trace_id=tid): ...``"""

    def __init__(self, name: str, *, trace_id: str = "", attrs: dict | None = None) -> None:
        self._name = name
        self._trace_id = trace_id
        self._attrs = attrs

    def __enter__(self) -> "Span":
        tracer = get_tracer()
        self._ctx = tracer.span(self._name, trace_id=self._trace_id, attrs=self._attrs)
        self._ctx.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self._ctx.__exit__(*args)
