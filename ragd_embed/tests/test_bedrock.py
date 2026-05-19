from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from ragd_embed.providers.bedrock import BedrockProvider


def test_bedrock_provider_init():
    provider = BedrockProvider(api_key="", model="amazon.titan-embed-text-v2:0")
    assert provider.name == "bedrock"
    assert provider.model == "amazon.titan-embed-text-v2:0"
    assert provider.dim == 1024


def test_bedrock_health_checks_boto3():
    provider = BedrockProvider(api_key="")
    health = provider.health()
    try:
        import boto3  # noqa: F401
        assert health["ok"] is True
    except Exception:
        assert health["ok"] is False


def test_bedrock_embed_batch():
    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    mock_response = {
        "body": MagicMock()
    }
    mock_response["body"].read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]})
    mock_client.invoke_model.return_value = mock_response

    sys.modules["boto3"] = mock_boto3

    try:
        provider = BedrockProvider(api_key="")
        result = provider.embed_batch(["hello world"])

        assert len(result) == 1
        assert result[0] == [0.1, 0.2, 0.3]
        mock_boto3.client.assert_called_once_with("bedrock-runtime")
        mock_client.invoke_model.assert_called_once()
    finally:
        sys.modules.pop("boto3", None)


def test_bedrock_embed_batch_multiple_texts():
    mock_boto3 = MagicMock()
    mock_client = MagicMock()
    mock_boto3.client.return_value = mock_client

    def mock_invoke(modelId, body, accept, contentType):
        return {
            "body": MagicMock(
                read=MagicMock(return_value=json.dumps({"embedding": [0.1, 0.2, 0.3]}))
            )
        }

    mock_client.invoke_model.side_effect = mock_invoke

    sys.modules["boto3"] = mock_boto3

    try:
        provider = BedrockProvider(api_key="")
        result = provider.embed_batch(["text1", "text2"])

        assert len(result) == 2
        assert all(vec == [0.1, 0.2, 0.3] for vec in result)
        assert mock_client.invoke_model.call_count == 2
    finally:
        sys.modules.pop("boto3", None)
