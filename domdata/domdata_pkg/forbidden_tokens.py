"""Canonical forbidden trading token set.

Single source of truth shared by:
  - domdata/check_no_trading.py     (file scanner)
  - domdata/domdata_pkg/safety.py   (runtime monkeypatch guard)
  - dominion_agent/adversary.py     (adversarial review lane)

This file is allowlisted in check_no_trading.py and must remain so.
Add tokens here; they propagate to all consumers automatically.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _policy_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "forbidden_tokens.json"


def _load_policy() -> dict:
    return json.loads(_policy_path().read_text(encoding="utf-8"))


def _tokens_from_policy(policy: dict) -> frozenset[str]:
    tokens: set[str] = set()
    for values in policy.get("groups", {}).values():
        tokens.update(str(token) for token in values)
    return frozenset(tokens)


FORBIDDEN_POLICY: dict = _load_policy()

# Exact string tokens that must never appear outside allowlisted safety files.
# Covers MT5 Python APIs, MQL action constants, and legacy wrapper names.
FORBIDDEN_TOKENS: frozenset[str] = _tokens_from_policy(FORBIDDEN_POLICY)
FORBIDDEN_POLICY_FINGERPRINT: str = hashlib.sha256(
    json.dumps(FORBIDDEN_POLICY, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
