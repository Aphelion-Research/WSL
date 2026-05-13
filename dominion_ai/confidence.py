from __future__ import annotations

from .obs import emit_span
from .types import Confidence, RetrievalPlan, ScoredChunk


def score_confidence(plan: RetrievalPlan, chunks: list[ScoredChunk]) -> Confidence:
    if not chunks:
        factors = {"intent": plan.intent_confidence, "coverage": 0.0, "score_shape": 0.0, "citation": 0.0}
        decision = "refuse"
        reason = "No RAGD chunks survived retrieval and safety filtering."
        result = Confidence(0.0, factors, decision, reason)
        emit_span(plan.trace_id, "confidence", {"score": result.score, "decision": result.decision, "factors": factors})
        return result
    terms = [term for term in plan.query.lower().split() if len(term) > 2]
    joined_top = " ".join(f"{chunk.filepath} {chunk.symbol_name} {chunk.content}" for chunk in chunks[:3]).lower()
    coverage = sum(1 for term in terms if term in joined_top) / max(1, len(terms))
    scores = [chunk.score for chunk in chunks[:5]]
    top = scores[0]
    variance = max(scores) - min(scores) if len(scores) > 1 else top
    score_shape = min(1.0, max(0.0, top / (variance + top + 1e-9)))
    citation = min(1.0, len([chunk for chunk in chunks if chunk.citations]) / min(3, len(chunks)))
    score = max(0.0, min(1.0, 0.30 * plan.intent_confidence + 0.35 * coverage + 0.20 * score_shape + 0.15 * citation))
    if score < 0.25:
        decision = "refuse"
        reason = "No strong evidence after retrieval."
    elif score < 0.45:
        decision = "escalate"
        reason = "Evidence is thin; use broader retrieval before generation."
    else:
        decision = "ok"
        reason = "Retrieved evidence covers the query."
    factors = {"intent": plan.intent_confidence, "coverage": coverage, "score_shape": score_shape, "citation": citation}
    result = Confidence(score, factors, decision, reason)
    emit_span(plan.trace_id, "confidence", {"score": score, "decision": decision, "factors": factors})
    return result
