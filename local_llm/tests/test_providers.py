from __future__ import annotations

from local_llm.providers.mock import MockProvider
from local_llm.providers.ollama import OllamaProvider
from local_llm.registry import GenerateRequest


def test_mock_provider_contract():
    provider = MockProvider()
    assert provider.health().ok
    assert "".join(token.text for token in provider.generate(GenerateRequest("x", "mock"))) == "mock response"


def test_ollama_provider_handles_missing_service():
    assert OllamaProvider("http://127.0.0.1:1").health().ok is False
