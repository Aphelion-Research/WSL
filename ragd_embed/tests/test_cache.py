from __future__ import annotations

from ragd_embed.cache import EmbeddingCache


def test_cache_hit_and_provider_miss(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "embed.db"))
    cache = EmbeddingCache(tmp_path / "embed.db")
    cache.put("hash1", [0.1, 0.2], provider="voyage", model="m")
    assert cache.get("hash1", provider="voyage", model="m", dim=2) == [0.10000000149011612, 0.20000000298023224]
    assert cache.get("hash1", provider="openai", model="m", dim=2) is None
    assert cache.get("hash1", provider="voyage", model="other", dim=2) is None
