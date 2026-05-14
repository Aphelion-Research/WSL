from __future__ import annotations

import re
from typing import Any

from .obs import new_trace_id, span
from .types import RetrievalPlan


INTENT_RULES: list[tuple[str, str, list[str], float]] = [
    ("handoff", "handoff_protocol", ["handoff", "agent handoff", "AGENT_HANDOFF", "RAGD handoff"], 0.9),
    ("trace|why.*chunk|provenance", "trace_explain", ["trace_id", "chunk provenance", "span"], 0.86),
    ("ledger|decision|memory", "agent_memory", ["decisions", "agent memory", "ledger"], 0.84),
    ("embedding|semantic|hnsw|vault|obsidian", "rag_infrastructure", ["ragd_embed", "ragd_hnsw", "ragd_vault"], 0.82),
    ("test|pytest|ctest|validation", "validation", ["tests", "validation", "pytest", "ctest"], 0.8),
    ("domdata|mt5|trading|xau", "data_safety", ["domdata", "read-only", "check_no_trading"], 0.9),
    ("cli|command|dominion", "cli", ["scripts/dominion_cli.py", "command center"], 0.78),
]


def _filters(query: str) -> dict[str, Any]:
    lower = query.lower()
    filters: dict[str, Any] = {}
    if "python" in lower or ".py" in lower:
        filters["lang"] = "python"
    if "markdown" in lower or "docs" in lower:
        filters["lang"] = "markdown"
    if "test" in lower:
        filters["path_contains"] = "test"
    if "recent" in lower or "--recent-changes" in lower:
        filters["recent_changes"] = True
    return filters


def plan(query: str, hints: dict[str, Any] | None = None) -> RetrievalPlan:
    hints = hints or {}
    trace_id = str(hints.get("trace_id") or new_trace_id())
    with span(trace_id, "plan", {"query": query}):
        lower = query.lower()
        intent = "general"
        confidence = 0.62
        expanded = [query]
        for pattern, candidate, terms, rule_confidence in INTENT_RULES:
            if re.search(pattern, lower):
                intent = candidate
                confidence = rule_confidence
                expanded.extend(terms)
                break
        if hints.get("intent"):
            intent = str(hints["intent"])
            confidence = max(confidence, 0.75)
        top_k = int(hints.get("top_k", 10))
        mode = str(hints.get("mode", "hybrid"))
        return RetrievalPlan(
            query=query,
            intent=intent,
            expanded_terms=list(dict.fromkeys(expanded)),
            metadata_filters={**_filters(query), **dict(hints.get("metadata_filters", {}))},
            top_k_bm25=max(top_k, int(hints.get("top_k_bm25", top_k))),
            top_k_vector=max(top_k, int(hints.get("top_k_vector", top_k))),
            rerank_strategy=str(hints.get("rerank_strategy", "heuristic")),
            temporal_constraints=hints.get("temporal_constraints"),
            trace_id=trace_id,
            mode=mode,
            intent_confidence=confidence,
        )
