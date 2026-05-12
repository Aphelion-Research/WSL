from __future__ import annotations

from local_llm.cli import build_parser


def test_cli_parses_query_expand():
    args = build_parser().parse_args(["query-expand", "xauusd"])
    assert args.text == "xauusd"
