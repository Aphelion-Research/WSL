from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import mask_value
from .mt5_client import connect, shutdown
from .serializers import to_jsonable


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def resolve_root(value: str) -> Path:
    raw = value
    if raw.startswith("~/"):
        raw = os.path.join(os.environ.get("HOME", "/home/Martin"), raw[2:])
    if sys.platform.startswith("win") and raw.startswith("/"):
        raw = "Z:" + raw
    return Path(raw)


def hour_path(root: Path, kind: str, when: datetime, *, timeframe: str | None = None) -> Path:
    date = when.strftime("%Y-%m-%d")
    hour = when.strftime("%H")
    if kind == "bars":
        return root / "xauusd" / "bars" / f"timeframe={timeframe or 'M1'}" / f"date={date}" / f"bars-{hour}.jsonl"
    return root / "xauusd" / kind / f"date={date}" / f"{kind}-{hour}.jsonl"


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
        handle.flush()


def tick_row(symbol: str, tick: Any, collected_at: str) -> dict[str, Any]:
    data = to_jsonable(tick) or {}
    bid = data.get("bid")
    ask = data.get("ask")
    mid = (bid + ask) / 2 if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) else None
    spread = ask - bid if isinstance(bid, (int, float)) and isinstance(ask, (int, float)) else None
    return {
        "source": "mt5_combat",
        "symbol": symbol,
        "time": data.get("time"),
        "time_msc": data.get("time_msc"),
        "bid": bid,
        "ask": ask,
        "mid": mid,
        "spread": spread,
        "flags": data.get("flags"),
        "volume": data.get("volume"),
        "volume_real": data.get("volume_real"),
        "collected_at_utc": collected_at,
    }


def bar_row(symbol: str, bar: dict[str, Any], collected_at: str) -> dict[str, Any]:
    return {
        "source": "mt5_combat",
        "symbol": symbol,
        "timeframe": "M1",
        "time": bar.get("time"),
        "open": bar.get("open"),
        "high": bar.get("high"),
        "low": bar.get("low"),
        "close": bar.get("close"),
        "tick_volume": bar.get("tick_volume"),
        "spread": bar.get("spread"),
        "real_volume": bar.get("real_volume"),
        "collected_at_utc": collected_at,
    }


def mask_login(login: Any) -> str | None:
    if login is None:
        return None
    return mask_value("DOMDATA_MT5_LOGIN", str(login))


def write_health(
    root: Path,
    *,
    mt5_connected: bool,
    account_login_masked: str | None,
    symbol_selected: bool,
    last_tick_age_ms: int | None,
    tick_count_written: int,
    bar_count_written: int,
    errors_count: int,
) -> None:
    when = utc_now()
    row = {
        "collected_at_utc": when.isoformat().replace("+00:00", "Z"),
        "mt5_connected": mt5_connected,
        "account_login_masked": account_login_masked,
        "symbol_selected": symbol_selected,
        "last_tick_age_ms": last_tick_age_ms,
        "tick_count_written": tick_count_written,
        "bar_count_written": bar_count_written,
        "errors_count": errors_count,
        "process_pid": os.getpid(),
    }
    append_jsonl(hour_path(root, "health", when), row)


def collect_xau(args: Any) -> None:
    symbol = args.symbol
    root = resolve_root(args.out_root)
    tick_interval = max(args.tick_interval_ms, 25) / 1000.0
    bar_interval = max(args.bar_interval_sec, 1)
    heartbeat = max(args.heartbeat_sec, 1)
    deadline = time.monotonic() + args.max_runtime_sec if args.max_runtime_sec else None
    tick_seen: set[tuple[Any, Any, Any]] = set()
    bar_seen: set[Any] = set()
    tick_count = 0
    bar_count = 0
    errors = 0
    last_tick_msc: int | None = None
    last_bar_poll = 0.0
    last_heartbeat = 0.0
    account_login_masked: str | None = None
    symbol_selected = False
    mt5 = connect(args)
    try:
        account = to_jsonable(mt5.account_info()) or {}
        account_login_masked = mask_login(account.get("login")) if isinstance(account, dict) else None
        symbol_selected = bool(mt5.symbol_select(symbol, True))
        if not symbol_selected:
            raise SystemExit(f"Failed to select {symbol}: {mt5.last_error()}")
        print(f"collect-xau started symbol={symbol} out_root={root}")
        while True:
            now_monotonic = time.monotonic()
            if deadline and now_monotonic >= deadline:
                break
            collected_at = iso_now()
            try:
                tick = mt5.symbol_info_tick(symbol)
                if tick is not None:
                    row = tick_row(symbol, tick, collected_at)
                    key = (row.get("time_msc"), row.get("bid"), row.get("ask"))
                    if key not in tick_seen:
                        tick_seen.add(key)
                        append_jsonl(hour_path(root, "ticks", utc_now()), row)
                        tick_count += 1
                        if isinstance(row.get("time_msc"), int):
                            last_tick_msc = row["time_msc"]
                if now_monotonic - last_bar_poll >= bar_interval:
                    last_bar_poll = now_monotonic
                    bars = to_jsonable(mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 2)) or []
                    for bar in bars:
                        if not isinstance(bar, dict):
                            continue
                        bar_key = bar.get("time")
                        if bar_key in bar_seen:
                            continue
                        bar_seen.add(bar_key)
                        append_jsonl(hour_path(root, "bars", utc_now(), timeframe="M1"), bar_row(symbol, bar, collected_at))
                        bar_count += 1
                last_tick_age_ms = max(0, int(time.time() * 1000 - last_tick_msc)) if last_tick_msc else None
                if now_monotonic - last_heartbeat >= heartbeat:
                    last_heartbeat = now_monotonic
                    write_health(
                        root,
                        mt5_connected=True,
                        account_login_masked=account_login_masked,
                        symbol_selected=symbol_selected,
                        last_tick_age_ms=last_tick_age_ms,
                        tick_count_written=tick_count,
                        bar_count_written=bar_count,
                        errors_count=errors,
                    )
                    print(f"heartbeat ticks={tick_count} bars={bar_count} errors={errors} last_tick_age_ms={last_tick_age_ms}")
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                errors += 1
                print(f"collector error: {exc!r}")
            time.sleep(tick_interval)
    except KeyboardInterrupt:
        print("collect-xau interrupted")
    finally:
        last_tick_age_ms = max(0, int(time.time() * 1000 - last_tick_msc)) if last_tick_msc else None
        write_health(
            root,
            mt5_connected=True,
            account_login_masked=account_login_masked,
            symbol_selected=symbol_selected,
            last_tick_age_ms=last_tick_age_ms,
            tick_count_written=tick_count,
            bar_count_written=bar_count,
            errors_count=errors,
        )
        shutdown(mt5)
        print(f"collect-xau stopped ticks={tick_count} bars={bar_count} errors={errors}")


def latest_file(pattern: str, root: Path) -> Path | None:
    files = [path for path in root.glob(pattern) if path.is_file()]
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def line_count(path: Path | None) -> int:
    if path is None:
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return sum(1 for _ in handle)


def last_jsonl(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    last = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                last = line
    return json.loads(last) if last else None


def collect_status(args: Any) -> None:
    root = resolve_root(args.out_root)
    tick = latest_file("xauusd/ticks/date=*/ticks-*.jsonl", root)
    bar = latest_file("xauusd/bars/timeframe=M1/date=*/bars-*.jsonl", root)
    health = latest_file("xauusd/health/date=*/health-*.jsonl", root)
    print(f"raw root: {root}")
    for label, path in [("ticks", tick), ("bars", bar), ("health", health)]:
        if path is None:
            print(f"{label}: missing")
        else:
            print(f"{label}: {path} size={path.stat().st_size} rows={line_count(path)}")
    latest_health = last_jsonl(health)
    if latest_health:
        print("latest health:")
        print(json.dumps(latest_health, indent=2, sort_keys=True))
