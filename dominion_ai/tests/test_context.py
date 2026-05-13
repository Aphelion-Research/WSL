from __future__ import annotations

from dominion_ai.context import assemble
from dominion_ai.types import RetrievalPlan, ScoredChunk


def test_assemble_preserves_citations_and_budget():
    plan = RetrievalPlan("handoff", "handoff", [], {}, 10, 10, "heuristic", None, "t")
    chunk = ScoredChunk("1", "doc", "/repo/a.md", 2, 4, "handoff text", 1, 0, 0, 0, 0, 0.8, "h", [])
    context = assemble(plan, [chunk], 100)
    assert context.citations[0].chunk_id == "1"
    assert context.token_estimate <= context.budget
