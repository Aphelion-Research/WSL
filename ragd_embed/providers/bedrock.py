from __future__ import annotations

from typing import Any

from ragd_embed.config import BEDROCK_MODEL


class BedrockProvider:
    name = "bedrock"
    dim = 1024

    def __init__(self, *, api_key: str, model: str = BEDROCK_MODEL) -> None:
        # Bedrock uses boto3 session, not direct API key - api_key param kept for interface compat
        self.model = model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import boto3
        import json

        client = boto3.client("bedrock-runtime")
        embeddings = []
        for text in texts:
            body = json.dumps({"inputText": text})
            response = client.invoke_model(
                modelId=self.model,
                body=body,
                accept="application/json",
                contentType="application/json",
            )
            result = json.loads(response["body"].read())
            embeddings.append(result["embedding"])
        return embeddings

    def health(self) -> dict[str, Any]:
        try:
            import boto3  # noqa: F401
        except Exception as exc:
            return {"ok": False, "provider": self.name, "model": self.model, "error": str(exc)}
        return {"ok": True, "provider": self.name, "model": self.model, "dim": self.dim}
