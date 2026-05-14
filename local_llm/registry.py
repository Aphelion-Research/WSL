from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Iterator, Protocol


MODEL_REGISTRY = {
    "retrieve_only_4gb": {
        "model_id": "",
        "max_vram_bytes": 0,
        "provider": "none",
        "mode": "retrieve_only",
        "reason": "No configured local generation model fits the 3.5 GB safety ceiling for a 4 GB GPU.",
    },
    "cpu_safe": {
        "model_id": "qwen2.5-coder:7b-instruct-q3_K_M",
        "max_vram_bytes": 0,
        "provider": "ollama",
        "mode": "generate",
    },
    "gpu_4gb_manual_risky": {
        "model_id": "qwen2.5-coder:7b-instruct-q3_K_M",
        "max_vram_bytes": 3_808_405_193,
        "provider": "ollama",
        "mode": "generate",
        "requires_manual": True,
        "reason": "Manual-only: estimated VRAM exceeds the 3.5 GB safety ceiling.",
    },
    "embedding": {"model_id": "nomic-embed-text", "provider": "ollama", "mode": "embed", "max_vram_bytes": 0},
}


def default_model_id(profile: str = "cpu_safe") -> str:
    return str(MODEL_REGISTRY[profile]["model_id"])


def default_embed_model_id() -> str:
    return str(MODEL_REGISTRY["embedding"]["model_id"])


@dataclass(frozen=True)
class ProviderHealth:
    ok: bool
    provider: str
    models: list[str]
    message: str = ""
    host: str = ""
    vram_bytes_used: int = 0
    vram_bytes_free: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class GenerateRequest:
    prompt: str
    model_id: str
    timeout_s: int = 30
    stream: bool = True


@dataclass(frozen=True)
class Token:
    text: str
    done: bool = False


class Provider(Protocol):
    def health(self) -> ProviderHealth: ...

    def generate(self, req: GenerateRequest) -> Iterator[Token]: ...

    def embed(self, text: str) -> list[float] | None: ...


def provider(name: str = "ollama") -> Provider:
    if name == "mock":
        from .providers.mock import MockProvider

        return MockProvider()
    if name == "ollama":
        from .providers.ollama import OllamaProvider

        return OllamaProvider()
    raise ValueError(f"unknown provider: {name}")


def provider_for_plan(plan) -> Provider:
    return provider(plan.provider)


def registry_json() -> str:
    return json.dumps(MODEL_REGISTRY, indent=2, sort_keys=True)
