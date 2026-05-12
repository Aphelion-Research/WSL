from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from .config import read_config
from .safety import apply_read_only_guard


TIMEFRAMES = {
    "M1": "TIMEFRAME_M1",
    "M5": "TIMEFRAME_M5",
    "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30",
    "H1": "TIMEFRAME_H1",
    "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1",
}


def parse_dt(value: str) -> datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_mt5() -> Any:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        print("MetaTrader5 import failed inside domdata runtime.")
        print(f"error: {exc!r}")
        raise SystemExit(2)
    return apply_read_only_guard(mt5)


def connect(args: Any | None = None) -> Any:
    mt5 = load_mt5()
    cfg = read_config()
    terminal_path = getattr(args, "terminal_path", None) or cfg.terminal_path
    kwargs: dict[str, Any] = {}
    if terminal_path:
        kwargs["path"] = terminal_path
    ok = mt5.initialize(**kwargs)
    if not ok:
        print(f"MT5 initialize failed: {mt5.last_error()}")
        raise SystemExit(3)
    if cfg.login and cfg.password and cfg.server:
        logged = mt5.login(login=int(cfg.login), password=cfg.password, server=cfg.server)
        if not logged:
            print(f"MT5 login failed: {mt5.last_error()}")
            raise SystemExit(4)
    return mt5


def shutdown(mt5: Any) -> None:
    try:
        mt5.shutdown()
    except Exception:
        pass


def timeframe(mt5: Any, name: str) -> Any:
    key = name.upper()
    if key not in TIMEFRAMES:
        raise SystemExit(f"Unsupported timeframe: {name}. Options: {', '.join(TIMEFRAMES)}")
    return getattr(mt5, TIMEFRAMES[key])


def runtime_env_summary() -> dict[str, str | None]:
    return {
        "WINEPREFIX": os.getenv("WINEPREFIX"),
        "DOMDATA_WINEPREFIX": os.getenv("DOMDATA_WINEPREFIX"),
        "DOMDATA_WINE_PYTHON": os.getenv("DOMDATA_WINE_PYTHON"),
    }
