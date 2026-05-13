from __future__ import annotations

from dominion_ai.ragd_client import TEMP_ADAPTER_NOTE, parse_chunk


def test_parse_chunk_filters_secrets():
    assert parse_chunk({"chunk_id": 1, "filepath": "/x/secrets/a", "content": "pw"}) is None


def test_parse_chunk_temp_adapter_hashes_missing_content_hash():
    chunk = parse_chunk({"chunk_id": 1, "filepath": "/repo/a.py", "content": "def x(): pass", "score": 0.2})
    assert chunk is not None
    assert chunk.content_hash
    assert "TEMP_ADAPTER(agent-1)" in TEMP_ADAPTER_NOTE


def test_parse_chunk_redacts_secret_mentions_in_content():
    chunk = parse_chunk({"chunk_id": 1, "filepath": "/repo/docs.md", "content": "never index secrets/ data", "score": 0.2})
    assert chunk is not None
    assert "secrets/" not in chunk.content
