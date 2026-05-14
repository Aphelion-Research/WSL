#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
import sys


ROOT = Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def run(cmd: list[str], timeout: int = 5) -> str:
    try:
        result = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)
        return (result.stdout or result.stderr or "").strip()
    except Exception as exc:
        return f"unavailable: {exc}"


def render() -> str:
    from dominion_ai.cli import latest_decisions_panel, latest_queries_panel

    sections = [
        ("Overview", run(["dominion", "status"], timeout=20)),
        ("RAGD", run(["dominion", "ragd"], timeout=10)[:1200]),
        ("Latest queries", latest_queries_panel()),
        ("Latest decisions", latest_decisions_panel()),
        ("Research", run(["research", "status"], timeout=10)),
        ("Data", run(["domdata", "collect-status"], timeout=20)),
        ("Codex", run(["codexstatus"], timeout=10)),
        ("tmux", run(["tmux", "ls"], timeout=5)),
        ("Embeddings", run(["dominion", "embed", "stats"], timeout=10)),
        ("Obsidian Vault", run(["dominion", "vault", "status"], timeout=10)),
    ]

    # Agent OS panels
    try:
        from dominion_agent.tui import render_agent_panels
        agent_panel = render_agent_panels()
    except Exception as e:
        agent_panel = f"(agent os unavailable: {e})"
    sections.append(("Agent OS", agent_panel))

    out = [f"Dominion UI - {datetime.now().isoformat(timespec='seconds')}", "=" * 72]
    for title, body in sections:
        out.append(f"\n[{title}]")
        out.append(body or "no output")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(prog="dominion-ui", description="Dominion terminal dashboard")
    parser.add_argument("--once", action="store_true", help="print one dashboard and exit")
    parser.add_argument("--interval", type=float, default=5.0)
    args = parser.parse_args()
    if args.once:
        print(render())
        return 0
    try:
        while True:
            os.system("clear")
            print(render())
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
