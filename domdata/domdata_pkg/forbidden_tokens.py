"""Canonical forbidden trading token set.

Single source of truth shared by:
  - domdata/check_no_trading.py     (file scanner)
  - domdata/domdata_pkg/safety.py   (runtime monkeypatch guard)
  - dominion_agent/adversary.py     (adversarial review lane)

This file is allowlisted in check_no_trading.py and must remain so.
Add tokens here; they propagate to all consumers automatically.
"""
from __future__ import annotations

# Exact string tokens that must never appear outside allowlisted safety files.
# Covers both snake_case (MT5 Python API) and PascalCase (MQL / third-party)
# trading execution forms.
FORBIDDEN_TOKENS: frozenset[str] = frozenset({
    # MT5 Python API — order execution
    "order_send",
    "order_check",
    # MQL4/5 trade action constants
    "TRADE_ACTION_DEAL",
    "TRADE_ACTION_PENDING",
    # Position management
    "POSITION_CLOSE",
    "position_close",
    # PascalCase / third-party API variants
    "OrderOpen",
    "OrderSend",
    "PositionOpen",
    "PositionClose",
    "TradeOpen",
    # Generic execution helpers
    "execute_trade",
})
