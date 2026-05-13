from __future__ import annotations

import json
import os
from typing import Iterator

import requests

from ..registry import GenerateRequest, ProviderHealth, Token, default_model_id


class OllamaProvider:
    def __init__(self, host: str | None = None):
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")

    def health(self) -> ProviderHealth:
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            if not response.ok:
                return ProviderHealth(False, "ollama", [], f"HTTP {response.status_code}", self.host)
            data = response.json()
            return ProviderHealth(True, "ollama", [item.get("name", "") for item in data.get("models", [])], host=self.host)
        except Exception as exc:
            return ProviderHealth(False, "ollama", [], str(exc), self.host)

    def generate(self, req: GenerateRequest) -> Iterator[Token]:
        model = req.model_id or os.environ.get("DOMINION_LLM_MODEL") or default_model_id()
        payload = {"model": model, "prompt": req.prompt, "stream": bool(req.stream)}
        response = requests.post(f"{self.host}/api/generate", json=payload, timeout=req.timeout_s, stream=bool(req.stream))
        response.raise_for_status()
        if req.stream:
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                data = json.loads(line)
                yield Token(str(data.get("response") or ""), bool(data.get("done")))
        else:
            data = response.json()
            yield Token(str(data.get("response") or ""), True)

    def embed(self, text: str) -> list[float] | None:
        model = os.environ.get("DOMINION_EMBED_MODEL")
        if not model:
            return None
        response = requests.post(f"{self.host}/api/embeddings", json={"model": model, "prompt": text}, timeout=30)
        if not response.ok:
            return None
        data = response.json()
        embedding = data.get("embedding")
        return embedding if isinstance(embedding, list) else None
