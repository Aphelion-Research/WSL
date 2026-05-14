from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VOYAGE_MODEL = "voyage-code-2"
OPENAI_MODEL = "text-embedding-3-small"
MODEL_DIMS = {VOYAGE_MODEL: 3072, OPENAI_MODEL: 1536}
PROVIDER_DEFAULT_MODELS = {"voyage": VOYAGE_MODEL, "openai": OPENAI_MODEL}


@dataclass(frozen=True)
class EmbedConfig:
    provider: str
    model: str
    dim: int
    api_key_env: str
    api_key: str
    batch_size: int
    cache_path: Path
    ragd_db_path: Path


def load_config(*, require_key: bool = True) -> EmbedConfig:
    provider = os.environ.get("RAGD_EMBED_PROVIDER", "voyage").strip().lower()
    if provider not in PROVIDER_DEFAULT_MODELS:
        raise ValueError(f"Unsupported RAGD_EMBED_PROVIDER={provider!r}; expected voyage or openai")
    model = os.environ.get("RAGD_EMBED_MODEL", PROVIDER_DEFAULT_MODELS[provider]).strip()
    dim = MODEL_DIMS.get(model)
    if dim is None:
        raise ValueError(f"Unsupported RAGD_EMBED_MODEL={model!r}; known models: {', '.join(sorted(MODEL_DIMS))}")
    api_key_env = "RAGD_EMBED_API_KEY"
    api_key = os.environ.get(api_key_env, "").strip()
    if require_key and not api_key:
        raise RuntimeError(f"{api_key_env} is required before code embeddings are sent to an external provider")
    batch_size = int(os.environ.get("RAGD_EMBED_BATCH_SIZE", "128"))
    home = Path(os.environ.get("RAGD_HOME", str(Path.home() / ".ragd"))).expanduser()
    return EmbedConfig(
        provider=provider,
        model=model,
        dim=dim,
        api_key_env=api_key_env,
        api_key=api_key,
        batch_size=batch_size,
        cache_path=Path(os.environ.get("RAGD_EMBED_CACHE", str(home / "embed_cache.db"))).expanduser(),
        ragd_db_path=Path(os.environ.get("RAGD_DB_PATH", str(home / "ragd.db"))).expanduser(),
    )
