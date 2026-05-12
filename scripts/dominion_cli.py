#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser()
RAGD = os.environ.get("RAGD_URL", "http://127.0.0.1:7474").rstrip("/")


def run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        return result.returncode, (result.stdout or result.stderr or "").strip()
    except Exception as exc:
        return 124, f"unavailable: {exc}"


def http_json(url: str, payload: dict | None = None, timeout: int = 5) -> dict:
    try:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=timeout) as response:
            return {"ok": True, "status_code": response.status, "data": json.loads(response.read().decode("utf-8"))}
    except (OSError, URLError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def ragd_health() -> dict:
    return http_json(f"{RAGD}/health")


def tmux_sessions() -> str:
    return run(["tmux", "ls"], timeout=3)[1] or "No tmux sessions."


def research_counts() -> dict[str, int | str]:
    path = ROOT / "research" / "research.db"
    if not path.exists():
        return {"status": "missing"}
    try:
        conn = sqlite3.connect(path)
        return {
            "sources": conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "jobs": conn.execute("SELECT COUNT(*) FROM crawl_jobs").fetchone()[0],
            "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "chunks": conn.execute("SELECT COUNT(*) FROM document_chunks").fetchone()[0],
        }
    except Exception as exc:
        return {"status": f"error: {exc}"}


def codex_config_status() -> dict[str, bool]:
    paths = [Path.home() / ".codex" / "config.toml", ROOT / ".codex" / "config.toml"]
    return {str(path): (path.exists() and "ragd" in path.read_text(encoding="utf-8", errors="replace")) for path in paths}


def print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def cmd_status(args: argparse.Namespace) -> int:
    tailscale = run(["tailscale", "ip", "-4"], timeout=3)[1]
    ssh = run(["service", "ssh", "status"], timeout=3)[1]
    ragd = ragd_health()
    domdata_notice = run(["domdata", "notice"], timeout=20)[1]
    data = {
        "tailscale_ip": tailscale,
        "ssh_active": "Active: active" in ssh,
        "tmux": tmux_sessions(),
        "ragd": ragd,
        "codex_mcp_config": codex_config_status(),
        "domdata_read_only": "READ-ONLY" in domdata_notice and "Blocked forever" in domdata_notice,
        "research": research_counts(),
        "local_llm": run(["llm", "doctor"], timeout=5)[1],
    }
    if args.json:
        print_json(data)
    else:
        print("Dominion Status")
        print(f"Tailscale IP: {data['tailscale_ip'] or 'unavailable'}")
        print(f"SSH active: {data['ssh_active']}")
        print("tmux:")
        print(data["tmux"])
        health = ragd.get("data", {}) if ragd.get("ok") else {}
        print(f"RAGD: {health.get('status', 'unreachable')} active_chunks={health.get('active_chunks', 'n/a')} chunks={health.get('chunks', 'n/a')} todos={health.get('todos', 'n/a')} embed_backend={health.get('embed_backend', 'n/a')}")
        print(f"Codex RAGD MCP config: {any(data['codex_mcp_config'].values())}")
        print(f"domdata read-only: {data['domdata_read_only']}")
        print(f"Research: {data['research']}")
        print("Local LLM: disabled" if '"ok": false' in str(data["local_llm"]) else "Local LLM: see llm doctor")
    return 0 if ragd.get("ok") else 1


def cmd_start(args: argparse.Namespace) -> int:
    print("Dominion start")
    run(["service", "ssh", "start"], timeout=10)
    for name, command in {
        "matin": f"cd {ROOT}; export DOMINION_PERSON=matin; exec bash -l",
        "dan": f"cd {ROOT}; export DOMINION_PERSON=dan; exec bash -l",
        "dominion": f"cd {ROOT}; export DOMINION_PERSON=dominion; exec bash -l",
    }.items():
        if run(["tmux", "has-session", "-t", name], timeout=2)[0] != 0:
            run(["tmux", "new-session", "-d", "-s", name, command], timeout=5)
    if not ragd_health().get("ok") and (ROOT / "ragd" / "build" / "ragd").exists():
        # Note: `dominion start` only manages the local default RAGD instance (127.0.0.1:7474).
        # If you point `RAGD_URL` elsewhere, this start path does not manage that remote instance.
        command = f"cd {ROOT / 'ragd'}; ./build/ragd --db ~/.ragd/ragd.db --host 127.0.0.1 --port 7474 --path {ROOT}"
        run(["tmux", "new-session", "-d", "-s", "ragd", command], timeout=5)
    print("Next commands:")
    print("  warp matin")
    print("  warp dan")
    print("  dominion status")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    checks = [
        ("dominion-health", ["dominion-health"]),
        ("RAGD health", ["curl", "-sf", f"{RAGD}/health"]),
        ("research doctor", ["research", "doctor"]),
        ("llm doctor", ["llm", "doctor"]),
        ("domdata notice", ["domdata", "notice"]),
        ("domdata order-send blocked", ["bash", "-lc", "domdata order-send >/tmp/dominion-order-send.out 2>&1; test $? -ne 0"]),
    ]
    failed = 0
    for label, cmd in checks:
        code, output = run(cmd, timeout=30)
        status = "PASS" if code == 0 else "FAIL"
        if code != 0:
            failed += 1
        print(f"{status} {label}")
        if args.verbose and output:
            print(output[:1000])
    return 1 if failed else 0


def cmd_tmux(args: argparse.Namespace) -> int:
    print(tmux_sessions())
    print("Use: warp matin | warp dan | warp dominion | warp codex | warp ragd")
    return 0


def cmd_codex(args: argparse.Namespace) -> int:
    tools = http_json(f"{RAGD}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    print("Codex")
    print(f"version: {run(['codex', '--version'], timeout=5)[1]}")
    print(f"binary: {shutil.which('codex')}")
    print(f"RAGD MCP config: {codex_config_status()}")
    print(f"RAGD MCP tools reachable: {tools.get('ok', False)}")
    print("Suggested: warp codex")
    return 0 if tools.get("ok") else 1


def cmd_ragd(args: argparse.Namespace) -> int:
    print_json({"health": ragd_health(), "tools": http_json(f"{RAGD}/mcp", {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})})
    return 0


def cmd_research(args: argparse.Namespace) -> int:
    print(run(["research", "status"], timeout=10)[1])
    print(run(["research", "doctor"], timeout=10)[1])
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    for cmd in (["domdata", "notice"], ["domdata", "collect-status"], ["domdata", "xautick"]):
        print(f"$ {' '.join(cmd)}")
        print(run(cmd, timeout=30)[1])
    return 0


def cmd_llm(args: argparse.Namespace) -> int:
    print(run(["llm", "doctor"], timeout=10)[1])
    return 0


def _latest_report() -> str:
    reports = (ROOT / "reports").glob("dominion-*-latest.md")
    latest = sorted((p.name for p in reports))
    return latest[-1] if latest else ""


def cmd_phase_report(args: argparse.Namespace) -> int:
    code, status = run(["git", "-C", str(ROOT), "status", "--short"], timeout=10)
    data = {
        "phase": args.phase,
        "root": str(ROOT),
        "git_dirty": bool(status.strip()),
        "git_status_short": status,
        "research_doctor": run(["research", "doctor", "--json"], timeout=10)[1],
        "llm_doctor": run(["llm", "doctor"], timeout=10)[1],
        "ragd_health": ragd_health(),
        "latest_report": _latest_report(),
        "recommended_validation": [
            "python -m pytest -q",
            "python domdata/check_no_trading.py",
            "./scripts/bootstrap_python.sh",
        ],
    }
    if args.json:
        print_json(data)
    else:
        print(f"Dominion phase-report ({args.phase})")
        print(f"root: {ROOT}")
        print(f"git dirty: {data['git_dirty']}")
        if status.strip():
            print("git status --short:")
            print(status)
        print(f"latest report: {data['latest_report'] or 'none'}")
        print("recommended validation:")
        for cmd in data["recommended_validation"]:
            print(f"  {cmd}")
    return 0


def cmd_next_prompt(args: argparse.Namespace) -> int:
    prompt = "\n".join(
        [
            "You are Codex working in /home/Martin/Dominion.",
            "Follow the Dominion Platform Contract in AGENTS.md (data-only, no secrets, no trading, bounded research).",
            "",
            "Startup protocol:",
            "cd /home/Martin/Dominion",
            "git status --short",
            "cat AGENT_HANDOFF.md",
            "cat PROGRESS.md | tail -n 120",
            "ragd_handoff_read || true",
            "codexrag \"Dominion V2.5\" || true",
            "research ragd-status || true",
            "dominion status || true",
            "",
            "Validation:",
            "python -m pytest -q",
            "python domdata/check_no_trading.py",
            "./scripts/bootstrap_python.sh",
            "",
            f"Current focus: {args.focus}",
        ]
    )
    print(prompt)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dominion", description="Dominion V2 command center")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (
        ("start", cmd_start),
        ("health", cmd_status),
        ("status", cmd_status),
        ("tmux", cmd_tmux),
        ("codex", cmd_codex),
        ("ragd", cmd_ragd),
        ("research", cmd_research),
        ("data", cmd_data),
        ("llm", cmd_llm),
    ):
        p = sub.add_parser(name)
        p.add_argument("--json", action="store_true") if name in {"status", "health"} else None
        p.set_defaults(func=func)
    p = sub.add_parser("doctor")
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(func=cmd_doctor)
    p = sub.add_parser("help")
    p.set_defaults(func=lambda args: (parser.print_help() or 0))

    p = sub.add_parser("phase-report")
    p.add_argument("--phase", default="v2.5")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_phase_report)

    p = sub.add_parser("next-prompt")
    p.add_argument("--focus", default="Continue Dominion V2.5 phase work")
    p.set_defaults(func=cmd_next_prompt)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
