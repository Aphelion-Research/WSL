from __future__ import annotations

from dataclasses import replace

from .types import ScoredChunk


PRIORITY = {
    "error": 10,
    "interface": 9,
    "config": 8,
    "test": 8,
    "function": 7,
    "class": 7,
    "section": 6,
    "block": 4,
}


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def chunk_value(query: str, chunk: ScoredChunk) -> float:
    lower = f"{chunk.filepath} {chunk.symbol_name} {chunk.content}".lower()
    terms = [term for term in query.lower().split() if len(term) > 2]
    salience = sum(1 for term in terms if term in lower) / max(1, len(terms))
    return PRIORITY.get(chunk.chunk_type, 5) + (salience * 5) + (chunk.confidence * 2)


def compress_chunk(chunk: ScoredChunk, max_tokens: int) -> ScoredChunk:
    if estimate_tokens(chunk.content) <= max_tokens:
        return chunk
    max_chars = max(40, max_tokens * 4)
    content = chunk.content[:max_chars].rstrip() + "\n...[compressed by budget optimizer]"
    return replace(chunk, content=content)


def optimize(query: str, chunks: list[ScoredChunk], budget: int) -> list[ScoredChunk]:
    if budget <= 0:
        return []
    ranked = sorted(chunks, key=lambda item: chunk_value(query, item) / estimate_tokens(item.content), reverse=True)
    selected: list[ScoredChunk] = []
    used = 0
    for chunk in ranked:
        cost = estimate_tokens(chunk.content) + 30
        candidate = chunk
        if used + cost > budget and chunk.chunk_type not in {"error", "interface", "test", "config"}:
            remaining = budget - used - 30
            if remaining <= 20:
                continue
            candidate = compress_chunk(chunk, remaining)
            cost = estimate_tokens(candidate.content) + 30
        if used + cost <= budget:
            selected.append(candidate)
            used += cost
    return selected
