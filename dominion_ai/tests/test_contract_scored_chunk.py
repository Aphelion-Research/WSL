from __future__ import annotations

from dataclasses import fields

from dominion_ai.types import ScoredChunk


def test_scored_chunk_schema_stable():
    names = [field.name for field in fields(ScoredChunk)]
    assert names[:13] == ["chunk_id", "document_id", "filepath", "line_start", "line_end", "content", "score", "bm25_score", "vector_score", "rerank_score", "rrf_score", "confidence", "content_hash"]
