from __future__ import annotations

from dominion_ai.rerank import rerank
from dominion_ai.types import RetrievalPlan, ScoredChunk


def _chunk(chunk_id: str, content: str) -> ScoredChunk:
    return ScoredChunk(chunk_id, "doc", f"/repo/{chunk_id}.py", 1, 1, content, 0.1, 0, 0, 0, 0, 0.2, chunk_id, [])


def test_heuristic_rerank_promotes_term_hits():
    plan = RetrievalPlan("agent memory", "agent_memory", [], {}, 10, 10, "heuristic", None, "t")
    chunks = rerank(plan, [_chunk("a", "nothing"), _chunk("b", "agent memory ledger")])
    assert chunks[0].chunk_id == "b"
