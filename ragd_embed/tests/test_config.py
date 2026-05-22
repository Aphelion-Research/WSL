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
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "openai")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="RAGD_EMBED_API_KEY"):
        load_config(require_key=True)


def test_ollama_provider_config(monkeypatch, tmp_path):
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "ollama")
    monkeypatch.delenv("RAGD_EMBED_MODEL", raising=False)
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))
    cfg = load_config()
    assert cfg.provider == "ollama"
    assert cfg.model == "nomic-embed-text"
    assert cfg.dim == 768
    assert cfg.batch_size == 128


def test_ollama_does_not_require_api_key(monkeypatch, tmp_path):
    """Ollama provider should NOT require RAGD_EMBED_API_KEY."""
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "ollama")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("RAGD_EMBED_CACHE", str(tmp_path / "cache.db"))
    # Should NOT raise even with require_key=True
    cfg = load_config(require_key=True)
    assert cfg.provider == "ollama"
    assert cfg.api_key == ""


def test_external_provider_requires_api_key(monkeypatch):
    """OpenAI/Voyage providers MUST have RAGD_EMBED_API_KEY."""
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "openai")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    # Should raise for external provider
    with pytest.raises(RuntimeError, match="RAGD_EMBED_API_KEY"):
        load_config(require_key=True)


def test_voyage_provider_requires_api_key(monkeypatch):
    """Voyage provider MUST have RAGD_EMBED_API_KEY."""
    monkeypatch.setenv("RAGD_EMBED_PROVIDER", "voyage")
    monkeypatch.delenv("RAGD_EMBED_API_KEY", raising=False)
    # Should raise for external provider
    with pytest.raises(RuntimeError, match="RAGD_EMBED_API_KEY"):
        load_config(require_key=True)
