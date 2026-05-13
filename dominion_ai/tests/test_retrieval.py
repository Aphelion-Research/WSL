from __future__ import annotations

from dominion_ai.planner import plan
from dominion_ai.retrieval import retrieve


class FakeClient:
    def query(self, q, *, mode, top_k):
        if mode == "bm25":
            return {"results": [{"chunk_id": 1, "filepath": "/repo/a.py", "content": "handoff", "score": 4, "bm25_score": 4}]}
        return {"results": [{"chunk_id": 1, "filepath": "/repo/a.py", "content": "handoff", "score": 0.5, "vector_score": 0.5}, {"chunk_id": 2, "filepath": "/repo/b.md", "content": "other", "score": 0.4}]}


def test_retrieve_rrf_merges_sources():
    chunks = retrieve(plan("handoff", {"trace_id": "t"}), FakeClient())
    assert chunks[0].chunk_id == "1"
    assert chunks[0].bm25_score == 4
    assert chunks[0].vector_score == 0.5
