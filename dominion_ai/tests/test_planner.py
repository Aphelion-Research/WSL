from __future__ import annotations

from dominion_ai.planner import plan


def test_golden_handoff_plan():
    result = plan("how does the handoff protocol work", {"trace_id": "t"})
    assert result.intent == "handoff_protocol"
    assert "RAGD handoff" in result.expanded_terms
    assert result.trace_id == "t"


def test_planner_filters_python():
    result = plan("show python tests", {"trace_id": "t"})
    assert result.metadata_filters["lang"] == "python"
    assert result.metadata_filters["path_contains"] == "test"
