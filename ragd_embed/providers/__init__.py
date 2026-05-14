from __future__ import annotations

from typing import Any, Protocol


class EmbedProvider(Protocol):
    name: str
    model: str
    dim: int

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
    def health(self) -> dict[str, Any]: ...
