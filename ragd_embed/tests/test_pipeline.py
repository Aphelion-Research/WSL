from __future__ import annotations

from ragd_embed.cache import EmbeddingCache
from ragd_embed.config import EmbedConfig
from ragd_embed.pipeline import ChunkInput, run_embedding_pipeline


class FakeProvider:
    name = "voyage"
    model = "voyage-code-2"
    dim = 2

    def __init__(self) -> None:
        self.calls = 0

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[float(index), 1.0] for index, _ in enumerate(texts)]

    def health(self) -> dict:
        return {"ok": True}


def _cfg(tmp_path):
    return EmbedConfig(
        provider="voyage",
        model="voyage-code-2",
        dim=2,
        api_key_env="RAGD_EMBED_API_KEY",
        api_key="key",
        batch_size=128,
        cache_path=tmp_path / "cache.db",
        ragd_db_path=tmp_path / "missing.db",
    )


def test_unchanged_chunks_produce_zero_api_calls(tmp_path):
    cache = EmbeddingCache(tmp_path / "cache.db")
    cache.put("h1", [0.0, 1.0], provider="voyage", model="voyage-code-2")
    provider = FakeProvider()
    stats = run_embedding_pipeline(
        [ChunkInput(1, "same", "h1")],
        cfg=_cfg(tmp_path),
        provider=provider,
        cache=cache,
        ragd_db_path=tmp_path / "missing.db",
        show_progress=False,
    )
    assert stats.cache_hits == 1
    assert stats.api_batches == 0
    assert provider.calls == 0


def test_changed_chunks_call_provider_once(tmp_path):
    provider = FakeProvider()
    stats = run_embedding_pipeline(
        [ChunkInput(1, "new", "h2")],
        cfg=_cfg(tmp_path),
        provider=provider,
        cache=EmbeddingCache(tmp_path / "cache.db"),
        ragd_db_path=tmp_path / "missing.db",
        show_progress=False,
    )
    assert stats.cache_misses == 1
    assert stats.api_batches == 1
    assert provider.calls == 1
