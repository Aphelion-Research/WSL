from __future__ import annotations

from local_llm.ollama import health


def test_ollama_health_handles_missing_service():
    result = health("http://127.0.0.1:1")
    assert result["ok"] is False
    assert result["disabled"] is True
