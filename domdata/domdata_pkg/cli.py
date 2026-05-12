from __future__ import annotations

import argparse

from . import commands
from .collector import collect_status, collect_xau
from .safety import BLOCKED_COMMANDS, blocked_command, notice


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--terminal-path", default=None)


def add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["json", "jsonl", "csv"], default="json")
    parser.add_argument("--out", default=None)


def main() -> None:
    parser = argparse.ArgumentParser(prog="domdata", description="Dominion MT5 read-only data CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("notice")
    p.set_defaults(func=notice)

    p = sub.add_parser("doctor")
    p.set_defaults(func=commands.doctor)

    for name, func in [("version", commands.version), ("terminal-info", commands.terminal_info), ("account-info", commands.account_info)]:
        p = sub.add_parser(name)
        add_common(p)
        add_output(p)
        p.set_defaults(func=func)

    p = sub.add_parser("symbols-get")
    p.add_argument("--group", default=None)
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.symbols_get)

    p = sub.add_parser("select")
    p.add_argument("symbol")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.select_symbol)

    p = sub.add_parser("symbol-info")
    p.add_argument("symbol")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.symbol_info)

    p = sub.add_parser("symbol-tick")
    p.add_argument("symbol")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.symbol_tick)

    p = sub.add_parser("rates-pos")
    p.add_argument("symbol")
    p.add_argument("timeframe")
    p.add_argument("start_pos", type=int)
    p.add_argument("count", type=int)
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.rates_pos)

    p = sub.add_parser("ticks-from")
    p.add_argument("symbol")
    p.add_argument("start")
    p.add_argument("count", type=int)
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.ticks_from)

    p = sub.add_parser("ticks-range")
    p.add_argument("symbol")
    p.add_argument("start")
    p.add_argument("end")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.ticks_range)

    p = sub.add_parser("tick")
    p.add_argument("symbol")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.symbol_tick)

    p = sub.add_parser("rates")
    p.add_argument("symbol")
    p.add_argument("timeframe")
    p.add_argument("--count", type=int, default=100)
    add_common(p)
    add_output(p)
    p.set_defaults(func=lambda args: (setattr(args, "start_pos", 0), commands.rates_pos(args))[1])

    p = sub.add_parser("ticks")
    p.add_argument("symbol")
    p.add_argument("--start", required=True)
    p.add_argument("--count", type=int, default=100)
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.ticks_from)

    p = sub.add_parser("xau")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.xau)

    p = sub.add_parser("xautick")
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.xautick)

    p = sub.add_parser("xaurates")
    p.add_argument("--count", type=int, default=100)
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.xaurates)

    p = sub.add_parser("xauticks")
    p.add_argument("--start", default="2026-05-11T00:00:00Z")
    p.add_argument("--count", type=int, default=100)
    add_common(p)
    add_output(p)
    p.set_defaults(func=commands.xauticks)

    p = sub.add_parser("collect-xau")
    p.add_argument("--symbol", default="XAUUSD")
    p.add_argument("--tick-interval-ms", type=int, default=250)
    p.add_argument("--bar-interval-sec", type=int, default=10)
    p.add_argument("--heartbeat-sec", type=int, default=10)
    p.add_argument("--max-runtime-sec", type=int, default=None)
    p.add_argument("--out-root", default="~/Dominion/data/raw/mt5")
    add_common(p)
    p.set_defaults(func=collect_xau)

    p = sub.add_parser("collect-status")
    p.add_argument("--out-root", default="~/Dominion/data/raw/mt5")
    p.set_defaults(func=collect_status)

    for name in sorted(BLOCKED_COMMANDS):
        p = sub.add_parser(name, help="BLOCKED by read-only policy")
        p.set_defaults(func=blocked_command)

    args = parser.parse_args()
    args.func(args)
