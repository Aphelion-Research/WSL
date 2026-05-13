from __future__ import annotations

from dominion_ai.confidence import score_confidence
from dominion_ai.types import RetrievalPlan, ScoredChunk


def test_confidence_refuses_empty():
    plan = RetrievalPlan("missing", "general", [], {}, 10, 10, "heuristic", None, "t")
    assert score_confidence(plan, []).decision == "refuse"


def test_confidence_ok_with_matching_chunk():
    plan = RetrievalPlan("agent handoff", "handoff", [], {}, 10, 10, "heuristic", None, "t", intent_confidence=0.9)
    chunk = ScoredChunk("1", "doc", "/repo/AGENT_HANDOFF.md", 1, 2, "agent handoff", 1, 0, 0, 0, 0, 1, "h", ["c"])
    assert score_confidence(plan, [chunk]).decision == "ok"
