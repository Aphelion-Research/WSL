from __future__ import annotations

from dataclasses import replace

from .obs import span
from .types import RetrievalPlan, ScoredChunk


HIGH_VALUE_TYPES = {"function", "class", "section", "config", "test", "error", "interface"}


def _term_hits(query: str, chunk: ScoredChunk) -> float:
    haystack = f"{chunk.filepath} {chunk.symbol_name} {chunk.content}".lower()
    terms = [term for term in query.lower().replace("_", " ").split() if len(term) > 2]
    if not terms:
        return 0.0
    return sum(1 for term in terms if term in haystack) / len(terms)


def rerank(plan: RetrievalPlan, chunks: list[ScoredChunk]) -> list[ScoredChunk]:
    if plan.rerank_strategy == "off":
        return chunks
    with span(plan.trace_id, "rerank", {"strategy": plan.rerank_strategy, "candidates": len(chunks)}):
        reranked: list[ScoredChunk] = []
        for chunk in chunks:
            type_boost = 0.08 if chunk.chunk_type in HIGH_VALUE_TYPES else 0.0
            path_boost = 0.06 if any(term.lower() in chunk.filepath.lower() for term in plan.expanded_terms[1:]) else 0.0
            symbol_boost = 0.08 if chunk.symbol_name and chunk.symbol_name.lower() in plan.query.lower() else 0.0
            hit_score = _term_hits(plan.query, chunk) * 0.25
            rerank_score = type_boost + path_boost + symbol_boost + hit_score
            reranked.append(replace(chunk, rerank_score=rerank_score, score=chunk.score + rerank_score))
        reranked.sort(key=lambda item: item.score, reverse=True)
        return reranked
