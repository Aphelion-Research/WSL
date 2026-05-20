"""ETA engine — rolling throughput estimation."""
from __future__ import annotations

import time
from collections import deque


class ETAEstimator:
    def __init__(self, window: int = 20, stall_seconds: float = 120.0):
        self._samples: deque = deque(maxlen=window)
        self._stall_seconds = stall_seconds
        self._last_update = time.time()

    def update(self, done: float, total: float) -> None:
        now = time.time()
        self._samples.append((now, done))
        self._last_update = now

    def eta_seconds(self, done: float, total: float) -> float | None:
        if len(self._samples) < 2:
            return None
        t0, d0 = self._samples[0]
        t1, d1 = self._samples[-1]
        dt = t1 - t0
        dd = d1 - d0
        if dt <= 0 or dd <= 0:
            return None
        rate = dd / dt
        remaining = total - done
        if remaining <= 0:
            return 0.0
        return remaining / rate

    def eta_human(self, done: float, total: float) -> str:
        if time.time() - self._last_update > self._stall_seconds:
            return "stalled?"
        if len(self._samples) < 3:
            return "warming up"
        secs = self.eta_seconds(done, total)
        if secs is None:
            return "N/A"
        if secs <= 0:
            return "done"
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = int(secs % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def throughput(self, done: float, total: float) -> float | None:
        if len(self._samples) < 2:
            return None
        t0, d0 = self._samples[0]
        t1, d1 = self._samples[-1]
        dt = t1 - t0
        dd = d1 - d0
        if dt <= 0:
            return None
        return dd / dt

    @property
    def is_stalled(self) -> bool:
        return time.time() - self._last_update > self._stall_seconds
