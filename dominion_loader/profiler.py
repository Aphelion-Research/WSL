"""Self-profiling runtime brain for dominion_loader (S01).

Per-stage timer spans persisted to manifest.db profile_spans table.
Daily roll-up report via dominion profile report.

Feature flag: DOMINION_PROFILER=off disables I/O but preserves API.
INTERFACE(agent-1): Profiler.span()  (Agent 2 may extend profile queries)
"""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

_PROFILER_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS profile_spans(
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id   TEXT NOT NULL DEFAULT '',
    stage      TEXT NOT NULL,
    start_ns   INTEGER NOT NULL,
    end_ns     INTEGER NOT NULL,
    duration_ms REAL NOT NULL,
    attrs_json TEXT NOT NULL DEFAULT '{}',
    recorded_at INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_profile_stage ON profile_spans(stage);
CREATE INDEX IF NOT EXISTS idx_profile_trace ON profile_spans(trace_id);
"""


@dataclass(frozen=True)
class ProfileSpan:
    stage: str
    duration_ms: float
    trace_id: str
    attrs: dict


class Profiler:
    """Records per-stage timing spans to SQLite.

    No global mutable state — each Profiler is independent.
    Sample-rate cap: profiler only records every Nth call when under load.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        *,
        sample_rate: int = 1,  # 1 = always; N = every Nth call
    ) -> None:
        self._enabled = os.environ.get("DOMINION_PROFILER", "on").lower() != "off"
        self._sample_rate = max(1, sample_rate)
        self._call_count = 0

        if self._enabled:
            if db_path is None:
                dominion_home = Path(os.environ.get("DOMINION_HOME", str(Path.home() / ".dominion")))
                db_path = dominion_home / "manifest.db"
            self._db_path = Path(db_path)
            self._conn = sqlite3.connect(str(self._db_path), isolation_level=None, check_same_thread=False)
            self._conn.executescript(_PROFILER_SCHEMA)
        else:
            self._conn = None  # type: ignore[assignment]

    @contextmanager
    def span(self, stage: str, *, trace_id: str = "", attrs: dict | None = None) -> Iterator[None]:
        """Context manager that records a timed span."""
        if not self._enabled or not self._should_sample():
            yield
            return

        start_ns = time.monotonic_ns()
        try:
            yield
        finally:
            end_ns = time.monotonic_ns()
            duration_ms = (end_ns - start_ns) / 1_000_000
            self._write(stage, start_ns, end_ns, duration_ms, trace_id, attrs or {})

    def _should_sample(self) -> bool:
        self._call_count += 1
        return (self._call_count % self._sample_rate) == 0

    def _write(
        self, stage: str, start_ns: int, end_ns: int,
        duration_ms: float, trace_id: str, attrs: dict
    ) -> None:
        import json
        now = int(time.time())
        try:
            self._conn.execute(
                """
                INSERT INTO profile_spans(trace_id, stage, start_ns, end_ns, duration_ms, attrs_json, recorded_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (trace_id, stage, start_ns, end_ns, duration_ms, json.dumps(attrs), now),
            )
            self._conn.commit()
        except Exception:
            pass  # Profiler must never crash the main path

    def report(self, *, top_n: int = 10, last_hours: int = 24) -> dict:
        """Generate a performance report: top N hot paths, p50/p95 per stage."""
        if not self._enabled or self._conn is None:
            return {"enabled": False, "spans": []}

        import json as _json
        cutoff = int(time.time()) - last_hours * 3600
        rows = self._conn.execute(
            """
            SELECT stage, duration_ms
            FROM profile_spans
            WHERE recorded_at > ?
            ORDER BY stage, duration_ms
            """,
            (cutoff,),
        ).fetchall()

        by_stage: dict[str, list[float]] = {}
        for row in rows:
            stage, duration_ms = row[0], row[1]
            by_stage.setdefault(stage, []).append(duration_ms)

        def percentile(values: list[float], p: float) -> float:
            if not values:
                return 0.0
            idx = min(int(len(values) * p / 100), len(values) - 1)
            return sorted(values)[idx]

        stage_stats = []
        for stage, durations in by_stage.items():
            stage_stats.append({
                "stage": stage,
                "count": len(durations),
                "p50_ms": round(percentile(durations, 50), 3),
                "p95_ms": round(percentile(durations, 95), 3),
                "total_ms": round(sum(durations), 3),
            })

        stage_stats.sort(key=lambda x: x["total_ms"], reverse=True)

        return {
            "enabled": True,
            "last_hours": last_hours,
            "total_spans": sum(len(v) for v in by_stage.values()),
            "top_stages": stage_stats[:top_n],
        }

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
