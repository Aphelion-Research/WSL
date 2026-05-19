from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ragd_embed.providers.ollama import OllamaProvider


def test_ollama_provider_init():
    provider = OllamaProvider(model="nomic-embed-text")
    assert provider.name == "ollama"
    assert provider.model == "nomic-embed-text"
    assert provider.dim == 768
    assert provider.base_url == "http://localhost:11434"


def test_ollama_provider_custom_base_url():
    provider = OllamaProvider(model="nomic-embed-text", base_url="http://custom:8080")
    assert provider.base_url == "http://custom:8080"


def test_ollama_api_key_ignored():
    provider = OllamaProvider(api_key="should-be-ignored", model="nomic-embed-text")
    assert provider.name == "ollama"


@patch("ragd_embed.providers.ollama.requests.post")
def test_ollama_embed_batch_single_text(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_post.return_value = mock_response

    provider = OllamaProvider()
    result = provider.embed_batch(["hello world"])

    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]
    mock_post.assert_called_once_with(
        "http://localhost:11434/api/embed",
        json={"model": "nomic-embed-text", "input": ["hello world"]},
        timeout=300,
    )


@patch("ragd_embed.providers.ollama.requests.post")
def test_ollama_embed_batch_multiple_texts(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"embeddings": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]}
    mock_post.return_value = mock_response

    provider = OllamaProvider()
    result = provider.embed_batch(["text1", "text2", "text3"])

    assert len(result) == 3
    assert result[0] == [0.1, 0.2]
    assert result[1] == [0.3, 0.4]
    assert result[2] == [0.5, 0.6]


@patch("ragd_embed.providers.ollama.requests.get")
def test_ollama_health_success(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "nomic-embed-text:latest"},
            {"name": "llama3:latest"},
        ]
    }
    mock_get.return_value = mock_response

    provider = OllamaProvider()
    health = provider.health()

    assert health["ok"] is True
    assert health["provider"] == "ollama"
    assert health["model"] == "nomic-embed-text"
    assert health["dim"] == 768


@patch("ragd_embed.providers.ollama.requests.get")
def test_ollama_health_model_not_found(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "llama3:latest"},
        ]
    }
    mock_get.return_value = mock_response

    provider = OllamaProvider()
    health = provider.health()

    assert health["ok"] is False
    assert "not found" in health["error"].lower()


@patch("ragd_embed.providers.ollama.requests.get")
def test_ollama_health_connection_error(mock_get):
    mock_get.side_effect = Exception("Connection refused")

    provider = OllamaProvider()
    health = provider.health()

    assert health["ok"] is False
    assert "Connection refused" in health["error"]
