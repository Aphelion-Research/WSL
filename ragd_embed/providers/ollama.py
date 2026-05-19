from __future__ import annotations

from typing import Any

import requests

from ragd_embed.config import OLLAMA_MODEL


class OllamaProvider:
    name = "ollama"
    dim = 768

    def __init__(self, *, api_key: str = "", model: str = "nomic-embed-text", base_url: str = "http://localhost:11434") -> None:
        # Ollama doesn't need API key - param kept for interface compat
        self.model = model
        self.base_url = base_url.rstrip("/")

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        MAX_CHARS = 2000
        cleaned = []
        for text in texts:
            text = text or ""
            text = text.strip()
            if len(text) > MAX_CHARS:
                text = text[:MAX_CHARS]
            if not text:
                text = "."
            cleaned.append(text)
        response = requests.post(
            f"{self.base_url}/api/embed",
            json={"model": self.model, "input": cleaned},
            timeout=300,
        )
        if response.status_code != 200:
            error_body = response.text[:500]
            raise RuntimeError(f"Ollama API error {response.status_code}: {error_body}")
        result = response.json()
        return result["embeddings"]

    def health(self) -> dict[str, Any]:
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = {m.get("name", "").split(":")[0] for m in models}
            if self.model not in model_names:
                return {
                    "ok": False,
                    "provider": self.name,
                    "model": self.model,
                    "error": f"Model {self.model} not found in Ollama. Available: {', '.join(sorted(model_names))}",
                }
            return {"ok": True, "provider": self.name, "model": self.model, "dim": self.dim}
        except Exception as exc:
            return {"ok": False, "provider": self.name, "model": self.model, "error": str(exc)}
