from __future__ import annotations

import os
from typing import Any

import requests

from .models import LLMConfig
from .prompts import claims_prompt, query_expand_prompt, summarize_prompt, tag_prompt
from .registry import default_embed_model_id, default_model_id


def config() -> LLMConfig:
    return LLMConfig(
        host=os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"),
        model=os.environ.get("DOMINION_LLM_MODEL", default_model_id()),
        embed_model=os.environ.get("DOMINION_EMBED_MODEL", default_embed_model_id()),
    )


def health(host: str | None = None) -> dict[str, Any]:
    cfg = config()
    base = (host or cfg.host).rstrip("/")
    try:
        response = requests.get(f"{base}/api/tags", timeout=2)
        if not response.ok:
            return {"ok": False, "disabled": True, "host": base, "error": f"HTTP {response.status_code}"}
        data = response.json()
        return {"ok": True, "disabled": False, "host": base, "models": [item.get("name") for item in data.get("models", [])]}
    except Exception as exc:
        return {"ok": False, "disabled": True, "host": base, "error": str(exc)}


def list_models() -> dict[str, Any]:
    return health()


def _generate(prompt: str) -> dict[str, Any]:
    cfg = config()
    status = health(cfg.host)
    if not status.get("ok"):
        return {"ok": False, "disabled": True, "message": "Ollama is not available", "health": status}
    try:
        response = requests.post(
            f"{cfg.host}/api/generate",
            json={"model": cfg.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        if not response.ok:
            return {"ok": False, "disabled": False, "error": f"HTTP {response.status_code}: {response.text[:300]}"}
        data = response.json()
        return {"ok": True, "model": cfg.model, "response": data.get("response", ""), "raw": data}
    except Exception as exc:
        return {"ok": False, "disabled": True, "error": str(exc)}


def summarize(text: str) -> dict[str, Any]:
    return _generate(summarize_prompt(text))


def tag(text: str) -> dict[str, Any]:
    return _generate(tag_prompt(text))


def extract_claims(text: str) -> dict[str, Any]:
    return _generate(claims_prompt(text))


def query_expand(text: str) -> dict[str, Any]:
    return _generate(query_expand_prompt(text))
