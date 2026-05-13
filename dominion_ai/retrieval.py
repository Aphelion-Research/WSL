from __future__ import annotations

from dataclasses import replace

from .obs import span
from .ragd_client import RagdClient, parse_chunks
from .types import RetrievalPlan, ScoredChunk


def _matches_filters(chunk: ScoredChunk, filters: dict) -> bool:
    lang = filters.get("lang")
    if lang and chunk.lang and chunk.lang != lang:
        return False
    contains = filters.get("path_contains")
    if contains and contains not in chunk.filepath:
        return False
    return True


def _rrf(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def retrieve(plan: RetrievalPlan, client: RagdClient | None = None) -> list[ScoredChunk]:
    client = client or RagdClient()
    with span(plan.trace_id, "retrieve_bm25", {"top_k": plan.top_k_bm25}):
        bm25 = parse_chunks(client.query(plan.query, mode="bm25", top_k=plan.top_k_bm25), source="bm25")
    with span(plan.trace_id, "retrieve_vector", {"top_k": plan.top_k_vector}):
        vector = parse_chunks(client.query(plan.query, mode="vector", top_k=plan.top_k_vector), source="vector")
    merged: dict[str, ScoredChunk] = {}
    with span(plan.trace_id, "rrf", {"bm25": len(bm25), "vector": len(vector)}):
        for rank, chunk in enumerate(bm25, start=1):
            merged[chunk.chunk_id] = replace(chunk, bm25_score=chunk.bm25_score or chunk.score, rrf_score=_rrf(rank))
        for rank, chunk in enumerate(vector, start=1):
            existing = merged.get(chunk.chunk_id)
            contribution = _rrf(rank)
            if existing is None:
                merged[chunk.chunk_id] = replace(chunk, vector_score=chunk.vector_score or chunk.score, rrf_score=contribution)
            else:
                merged[chunk.chunk_id] = replace(
                    existing,
                    vector_score=max(existing.vector_score, chunk.vector_score or chunk.score),
                    rrf_score=existing.rrf_score + contribution,
                )
    with span(plan.trace_id, "retrieve_filter", {"filters": plan.metadata_filters}):
        filtered = [chunk for chunk in merged.values() if _matches_filters(chunk, plan.metadata_filters)]
    ranked = [
        replace(
            chunk,
            score=chunk.rrf_score + min(max(chunk.bm25_score, 0.0), 50.0) * 0.001 + min(max(chunk.vector_score, 0.0), 1.0) * 0.05,
            confidence=min(1.0, max(0.0, chunk.rrf_score * 10 + min(chunk.vector_score, 1.0) * 0.2)),
        )
        for chunk in filtered
    ]
    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked[: max(plan.top_k_bm25, plan.top_k_vector)]
