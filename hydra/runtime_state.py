"""HYDRA runtime state — crash-safe progress tracking for all long operations."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hydra.utils.atomic import atomic_write_json, safe_read_json
from hydra.utils.system_monitor import get_system_stats

STATE_PATH = Path.home() / "Dominion" / "runs" / "hydra_runtime_state.json"
EVENTS_DIR = Path.home() / "Dominion" / "runs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _idle_state() -> dict:
    return {
        "schema_version": 1,
        "active": False,
        "run_id": None,
        "status": "IDLE",
        "phase": "IDLE",
        "mode": "none",
        "symbol": "XAUUSD",
        "timeframe": "none",
        "provider": "Unknown",
        "current_task": "No training at this time",
        "iteration": 0,
        "max_iterations": 0,
        "progress_pct": 0.0,
        "phase_progress_pct": 0.0,
        "rows_done": 0,
        "rows_total": 0,
        "bars_done": 0,
        "bars_total": 0,
        "files_done": 0,
        "files_total": 0,
        "started_at": None,
        "updated_at": _now_iso(),
        "eta_seconds": None,
        "eta_human": "N/A",
        "latest_log_file": None,
        "latest_error_file": None,
        "latest_artifact_dir": None,
        "last_error": None,
        "warnings": [],
        "metrics_preview": {
            "best_validation_sharpe": None,
            "best_validation_profit_factor": None,
            "best_iteration": None,
            "trades_so_far": 0,
            "current_oos_locked": True,
        },
        "modes": {
            m: {"status": "pending", "reason": None, "progress_pct": 0,
                "best_validation_sharpe": None, "trades": 0}
            for m in ("scalp", "daytrade", "swing", "combined")
        },
        "providers": {
            p: {"status": "unknown", "coverage_pct": None, "reason": None}
            for p in ("LocalCanonical", "DuckDB", "MT5", "Dukascopy", "Yahoo")
        },
        "system": get_system_stats(),
    }


def read_state() -> dict:
    state = safe_read_json(STATE_PATH)
    if state is None:
        state = _idle_state()
        write_state(state)
    return state


def write_state(state: dict) -> None:
    state["updated_at"] = _now_iso()
    atomic_write_json(STATE_PATH, state)


def update_state(**kwargs) -> dict:
    state = read_state()
    for k, v in kwargs.items():
        if k in state:
            state[k] = v
        elif "." in k:
            parts = k.split(".", 1)
            if parts[0] in state and isinstance(state[parts[0]], dict):
                state[parts[0]][parts[1]] = v
    state["system"] = get_system_stats()
    write_state(state)
    return state


def set_phase(phase: str, task: str = "", **extra) -> dict:
    return update_state(phase=phase, current_task=task, active=True, status="RUNNING", **extra)


def set_idle() -> dict:
    state = _idle_state()
    write_state(state)
    return state


def set_failed(error: str) -> dict:
    return update_state(status="FAILED", active=False, last_error=error)


def set_complete() -> dict:
    return update_state(status="COMPLETE", active=False, phase="COMPLETE",
                        progress_pct=100.0, phase_progress_pct=100.0)


class StateUpdater:
    """Context manager for a run phase — auto-updates state on enter/exit."""

    def __init__(self, run_id: str, phase: str, task: str = ""):
        self.run_id = run_id
        self.phase = phase
        self.task = task

    def __enter__(self):
        set_phase(self.phase, self.task, run_id=self.run_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            set_failed(str(exc_val))
        return False

    def progress(self, pct: float, task: str = "", **kw):
        update_state(phase_progress_pct=pct, current_task=task or self.task, **kw)


def append_event(run_id: str, level: str, phase: str, event: str,
                 message: str, mode: str = "", metrics: Optional[dict] = None) -> None:
    import json
    events_path = EVENTS_DIR / run_id / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": _now_iso(),
        "level": level,
        "phase": phase,
        "mode": mode,
        "event": event,
        "message": message,
    }
    if metrics:
        entry["metrics"] = metrics
    with open(events_path, "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")
        f.flush()
