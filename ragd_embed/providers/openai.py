from __future__ import annotations

from typing import Any

from ragd_embed.config import OPENAI_MODEL


class OpenAIProvider:
    name = "openai"
    dim = 1536

    def __init__(self, *, api_key: str, model: str = OPENAI_MODEL) -> None:
        if not api_key:
            raise RuntimeError("RAGD_EMBED_API_KEY is required for OpenAI embeddings")
        self.api_key = api_key
        self.model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.embeddings.create(model=self.model, input=texts)
        return [list(item.embedding) for item in response.data]

    def health(self) -> dict[str, Any]:
        try:
            import openai  # noqa: F401
        except Exception as exc:
            return {"ok": False, "provider": self.name, "model": self.model, "error": str(exc)}
        return {"ok": True, "provider": self.name, "model": self.model, "dim": self.dim}
