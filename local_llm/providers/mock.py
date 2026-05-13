from __future__ import annotations

from typing import Iterator

from ..registry import GenerateRequest, ProviderHealth, Token


class MockProvider:
    def health(self) -> ProviderHealth:
        return ProviderHealth(ok=True, provider="mock", models=["mock-local"])

    def generate(self, req: GenerateRequest) -> Iterator[Token]:
        for part in ["mock ", "response"]:
            yield Token(part)
        yield Token("", done=True)

    def embed(self, text: str) -> list[float] | None:
        return [float(len(text) % 7), 1.0]
