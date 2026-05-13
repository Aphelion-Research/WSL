from __future__ import annotations

from collections import defaultdict

from .budget import estimate_tokens, optimize
from .obs import span
from .types import AssembledContext, ContextSection, RetrievalPlan, ScoredChunk


def assemble(plan: RetrievalPlan, chunks: list[ScoredChunk], budget: int = 4096) -> AssembledContext:
    with span(plan.trace_id, "assemble", {"budget": budget, "candidate_chunks": len(chunks)}):
        selected = optimize(plan.query, chunks, budget)
        grouped: dict[str, list[ScoredChunk]] = defaultdict(list)
        seen: set[str] = set()
        for chunk in selected:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            grouped[chunk.filepath].append(chunk)
        sections: list[ContextSection] = []
        for filepath, file_chunks in grouped.items():
            parts = [f"## {filepath}"]
            for chunk in file_chunks:
                parts.append(f"[{chunk.chunk_id}] lines {chunk.line_start}-{chunk.line_end} hash={chunk.content_hash}\n{chunk.content}")
            text = "\n\n".join(parts)
            sections.append(ContextSection(filepath=filepath, chunks=file_chunks, token_estimate=estimate_tokens(text), text=text))
        token_estimate = sum(section.token_estimate for section in sections)
        return AssembledContext(
            sections=sections,
            token_estimate=token_estimate,
            budget=budget,
            citations=[chunk.citation() for section in sections for chunk in section.chunks],
            trace_id=plan.trace_id,
        )
