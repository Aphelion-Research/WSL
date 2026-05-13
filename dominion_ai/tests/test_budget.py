from __future__ import annotations

from dominion_ai.budget import estimate_tokens, optimize
from dominion_ai.types import ScoredChunk


def test_budget_preserves_high_value_chunk():
    high = ScoredChunk("hi", "doc", "/repo/test.py", 1, 1, "x" * 400, 1, 0, 0, 0, 0, 1, "h", [], chunk_type="test")
    low = ScoredChunk("lo", "doc", "/repo/doc.md", 1, 1, "y" * 400, 1, 0, 0, 0, 0, 1, "h", [], chunk_type="block")
    selected = optimize("test", [low, high], 140)
    assert selected
    assert selected[0].chunk_id == "hi"
    assert sum(estimate_tokens(c.content) + 30 for c in selected) <= 140
