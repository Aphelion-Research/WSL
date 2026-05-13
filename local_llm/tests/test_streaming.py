from __future__ import annotations

from local_llm.providers.mock import MockProvider
from local_llm.registry import GenerateRequest


def test_mock_stream_can_be_cancelled():
    stream = MockProvider().generate(GenerateRequest("x", "mock"))
    assert next(stream).text == "mock "
    stream.close()
