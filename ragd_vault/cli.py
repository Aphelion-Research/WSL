from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

from .builder import build_vault
from .doctor import inspect_vault
from .sync import sync_vault


def default_vault() -> Path:
    return Path(os.environ.get("DOMINION_ROOT", str(Path.home() / "Dominion"))).expanduser() / "vault"


def _json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dominion vault")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "sync", "open"):
        sub.add_parser(name)
    p = sub.add_parser("status")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("doctor")
    p.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = default_vault()
    if args.command == "build":
        print(json.dumps(build_vault(root), indent=2, sort_keys=True))
        return 0
    if args.command == "sync":
        print(json.dumps(sync_vault(root), indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        report = inspect_vault(root)
        payload = {"ok": root.exists(), "vault": str(root), "doctor": asdict(report)}
        if args.json:
            _json(payload)
        else:
            print(f"vault={root} notes={report.total_notes} broken_links={len(report.broken_links)}")
        return 0 if root.exists() else 1
    if args.command == "doctor":
        report = inspect_vault(root)
        payload = asdict(report)
        if args.json:
            _json(payload)
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if report.ok else 1
    opener = shutil.which("obsidian") or shutil.which("xdg-open")
    if opener:
        subprocess.Popen([opener, str(root)])
        return 0
    print(f"Open this vault manually: {root}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
