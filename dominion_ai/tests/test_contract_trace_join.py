from __future__ import annotations

from dominion_ai.obs import emit_span
from dominion_ai.trace import load_trace


def test_trace_join_schema_uses_trace_id(monkeypatch, tmp_path):
    monkeypatch.setattr("dominion_ai.obs.TRACE_DIR", tmp_path)
    monkeypatch.setattr("dominion_ai.trace.trace_path", lambda trace_id: tmp_path / f"{trace_id}.jsonl")
    emit_span("joinable", "loader", {"agent": "agent-1"})
    emit_span("joinable", "plan", {"agent": "agent-2"})
    spans = load_trace("joinable")
    assert {span["trace_id"] for span in spans} == {"joinable"}
    assert {span["span"] for span in spans} == {"loader", "plan"}
