from __future__ import annotations

from dominion_ai.ragd_client import parse_chunk


def test_parse_chunk_filters_secrets():
    assert parse_chunk({"chunk_id": 1, "filepath": "/x/secrets/a", "content": "pw"}) is None


def test_parse_chunk_fallback_hashes_missing_content_hash():
    chunk = parse_chunk({"chunk_id": 1, "filepath": "/repo/a.py", "content": "def x(): pass", "score": 0.2})
    assert chunk is not None
    assert chunk.content_hash
    assert chunk.metadata_source == "fallback"
    assert chunk.metadata_warnings == []


def test_parse_chunk_redacts_secret_mentions_in_content():
    chunk = parse_chunk({"chunk_id": 1, "filepath": "/repo/docs.md", "content": "never index secrets/ data", "score": 0.2})
    assert chunk is not None
    assert "secrets/" not in chunk.content


def test_parse_chunk_uses_real_content_hash():
    chunk = parse_chunk({"chunk_id": 1, "filepath": "/repo/a.py", "content_hash": "realhash", "content": "x", "score": 0.2})
    assert chunk is not None
    assert chunk.content_hash == "realhash"
    assert chunk.metadata_source == "ragd"


def test_parse_chunk_uses_real_document_id():
    chunk = parse_chunk({"chunk_id": 1, "document_id": "doc-1", "filepath": "/repo/a.py", "content_hash": "realhash", "content": "x"})
    assert chunk is not None
    assert chunk.document_id == "doc-1"
    assert chunk.metadata_source == "ragd"
    assert chunk.metadata_warnings == []


def test_parse_chunk_fallback_is_labeled():
    chunk = parse_chunk({"chunk_id": 1, "filepath": "/repo/a.py", "content": "x"})
    assert chunk is not None
    assert chunk.metadata_source == "fallback"
    assert chunk.metadata_warnings == []


def test_secret_path_still_filtered():
    assert parse_chunk({"chunk_id": 1, "filepath": "/repo/secrets/fake.env", "content_hash": "hash", "content": "x"}) is None


def test_parse_chunk_preserves_query_metadata():
    chunk = parse_chunk(
        {
            "chunk_id": 1,
            "document_id": "doc-1",
            "filepath": "/repo/a.py",
            "content_hash": "realhash",
            "repo_root": "/repo",
            "status": "active",
            "indexed_at": 123,
            "modified_at": 456,
            "content": "x",
        }
    )
    assert chunk is not None
    assert chunk.repo_root == "/repo"
    assert chunk.status == "active"
    assert chunk.indexed_at == 123
    assert chunk.modified_at == 456
