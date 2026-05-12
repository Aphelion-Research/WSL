from __future__ import annotations

import sys
from typing import Any


BLOCKED_COMMANDS = {"order-send", "order-check", "buy", "sell", "close", "modify"}
FORBIDDEN_TOKENS = {
    "order_send",
    "order_check",
    "TRADE_ACTION_DEAL",
    "TRADE_ACTION_PENDING",
    "POSITION_CLOSE",
}


def _blocked_trade(*args: Any, **kwargs: Any) -> None:
    raise RuntimeError("DOMDATA READ-ONLY GUARD: trading function blocked.")


def apply_read_only_guard(mt5: Any) -> Any:
    for name in ("order_send", "order_check"):
        if hasattr(mt5, name):
            setattr(mt5, name, _blocked_trade)
    return mt5


def blocked_command(_args: Any) -> None:
    print("BLOCKED: domdata is read-only. This command will never execute trades.", file=sys.stderr)
    raise SystemExit(99)


def notice(_args: Any) -> None:
    print("DOMDATA READ-ONLY MODE")
    print("Blocked forever: order-send, order-check, buy, sell, close, modify, pending orders")
