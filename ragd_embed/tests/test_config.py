from __future__ import annotations

import pytest

from ragd_embed.config import load_config


def test_provider_resolved_from_env(monkeypatch, tmp_path):
    monkeypatch.delenv("RAGD_EMBED_MODEL", raising=False)
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "openai")
    monkeypatch.setenv("RAGD_EMBED_API_KEY", "test-key")
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))
    cfg = load_config()
    assert cfg.provider == "openai"
    assert cfg.model == "text-embedding-3-small"
    assert cfg.dim == 1536


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="RAGD_EMBED_API_KEY"):
        load_config(require_key=True)


def test_bedrock_provider_config(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "bedrock")
    monkeypatch.setenv("RAGD_EMBED_API_KEY", "test-key")
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))
    cfg = load_config()
    assert cfg.provider == "bedrock"
    assert cfg.model == "amazon.titan-embed-text-v2:0"
    assert cfg.dim == 1024
