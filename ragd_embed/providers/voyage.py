from __future__ import annotations

from typing import Any

from ragd_embed.config import VOYAGE_MODEL


class VoyageProvider:
    name = "voyage"
    dim = 3072

    def __init__(self, *, api_key: str, model: str = VOYAGE_MODEL) -> None:
        if not api_key:
            raise RuntimeError("RAGD_EMBED_API_KEY is required for Voyage embeddings")
        self.api_key = api_key
        self.model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import voyageai

        client = voyageai.Client(api_key=self.api_key)
        result = client.embed(texts, model=self.model, input_type="document")
        return [list(vector) for vector in result.embeddings]

    def health(self) -> dict[str, Any]:
        try:
            import voyageai  # noqa: F401
        except Exception as exc:
            return {"ok": False, "provider": self.name, "model": self.model, "error": str(exc)}
        return {"ok": True, "provider": self.name, "model": self.model, "dim": self.dim}
