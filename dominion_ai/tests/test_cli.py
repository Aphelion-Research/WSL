from __future__ import annotations

from scripts.dominion_cli import build_parser


def test_cli_parses_new_subcommands():
    parser = build_parser()
    assert parser.parse_args(["ask", "agent handoff", "--json"]).query == "agent handoff"
    assert parser.parse_args(["ledger", "list", "--kind", "decision"]).kind == "decision"
    assert parser.parse_args(["trace", "abc"]).trace_id == "abc"
