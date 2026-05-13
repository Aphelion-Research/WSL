from __future__ import annotations

from dominion_ai.obs import emit_span
from dominion_ai.trace import render_trace


def test_trace_renders_spans(monkeypatch, tmp_path):
    monkeypatch.setattr("dominion_ai.obs.TRACE_DIR", tmp_path)
    monkeypatch.setattr("dominion_ai.trace.trace_path", lambda trace_id: tmp_path / f"{trace_id}.jsonl")
    emit_span("abc", "plan", {"query": "x"})
    assert "plan" in render_trace("abc")
