from __future__ import annotations

import statistics
import time
from typing import Any

from .api import ask


def run_suite(suite: str = "retrieval", *, iterations: int = 3) -> dict[str, Any]:
    latencies: list[float] = []
    query = "agent handoff"
    for _ in range(iterations):
        started = time.perf_counter()
        ask(query, generate=(suite == "generation"))
        latencies.append((time.perf_counter() - started) * 1000)
    ordered = sorted(latencies)
    return {
        "ok": True,
        "suite": suite,
        "iterations": iterations,
        "p50_ms": statistics.median(ordered),
        "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))],
        "p99_ms": ordered[-1],
        "model_calls_avoided": iterations if suite == "retrieval" else 0,
    }
