#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser()


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        text = (result.stdout or result.stderr or "").strip()
        return text
    except Exception as exc:
        return f"unavailable: {exc.__class__.__name__}"


def which(name: str) -> str | None:
    return shutil.which(name)


def latest_file(pattern: str) -> Path | None:
    files = [p for p in ROOT.glob(pattern) if p.is_file()]
    return max(files, key=lambda p: p.stat().st_mtime) if files else None


def last_json(path: Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    last = ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                last = line
    if not last:
        return None
    try:
        return json.loads(last)
    except Exception:
        return {"parse_error": str(path)}


def dir_size(path: Path) -> str:
    return run(["du", "-sh", str(path)], timeout=10).split("\t")[0] if path.exists() else "missing"


def collect() -> dict[str, Any]:
    tick_file = latest_file("data/raw/mt5/xauusd/ticks/date=*/ticks-*.jsonl")
    health_file = latest_file("data/raw/mt5/xauusd/health/date=*/health-*.jsonl")
    return {
        "os": run(["uname", "-a"]),
        "uptime": run(["uptime", "-p"]),
        "ram": run(["free", "-h"]),
        "disk": run(["df", "-h", str(ROOT)]),
        "cpu_threads": os.cpu_count(),
        "gpu": run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]),
        "paths": {
            "python": which("python"),
            "node": which("node"),
            "npm": which("npm"),
            "codex": which("codex"),
            "domdata": which("domdata"),
            "mt5start": which("mt5start"),
        },
        "versions": {
            "python": run(["python", "--version"]),
            "node": run(["node", "--version"]),
            "npm": run(["npm", "--version"]),
            "codex": run(["codex", "--version"]),
        },
        "tailscale_ip": run(["tailscale", "ip", "-4"]),
        "tailscale_status": run(["bash", "-lc", "tailscale status 2>&1 | sed -n '1,20p'"]),
        "ssh_status": run(["bash", "-lc", "service ssh status 2>&1 | sed -n '1,12p'"]),
        "tmux": run(["tmux", "ls"]),
        "mt5_running": bool(run(["pgrep", "-f", "[t]erminal64.exe"])),
        "domdata_doctor": run(["domdata", "doctor"], timeout=20),
        "latest_tick_file": str(tick_file) if tick_file else None,
        "latest_tick": last_json(tick_file),
        "latest_collector_health_file": str(health_file) if health_file else None,
        "latest_collector_health": last_json(health_file),
        "data_sizes": {
            "raw_mt5": dir_size(ROOT / "data" / "raw" / "mt5"),
            "normalized_mt5": dir_size(ROOT / "data" / "normalized" / "mt5"),
            "duckdb": str((ROOT / "data" / "dominion.duckdb").stat().st_size) if (ROOT / "data" / "dominion.duckdb").exists() else "missing",
        },
        "git_status": run(["git", "-C", str(ROOT), "status", "--short"]),
    }


def print_text(data: dict[str, Any]) -> None:
    print("Dominion Health")
    print(f"OS: {data['os']}")
    print(f"Uptime: {data['uptime']}")
    print(f"CPU threads: {data['cpu_threads']}")
    print(f"GPU: {data['gpu']}")
    print("Paths:")
    for key, value in data["paths"].items():
        print(f"  {key}: {value}")
    print(f"Tailscale IP: {data['tailscale_ip']}")
    print("SSH:", data["ssh_status"].splitlines()[2] if len(data["ssh_status"].splitlines()) > 2 else data["ssh_status"])
    print(f"tmux: {data['tmux']}")
    print(f"MT5 running: {data['mt5_running']}")
    latest_tick = data.get("latest_tick") or {}
    if latest_tick:
        print(f"Latest XAU tick: bid={latest_tick.get('bid')} ask={latest_tick.get('ask')} collected={latest_tick.get('collected_at_utc')}")
    latest_health = data.get("latest_collector_health") or {}
    if latest_health:
        print(
            "Collector: "
            f"ticks={latest_health.get('tick_count_written')} "
            f"bars={latest_health.get('bar_count_written')} "
            f"errors={latest_health.get('errors_count')} "
            f"at={latest_health.get('collected_at_utc')}"
        )
    print(f"Data sizes: {data['data_sizes']}")
    print(f"Git status: {data['git_status'] or 'clean'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dominion compact health dashboard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    data = collect()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print_text(data)


if __name__ == "__main__":
    main()
