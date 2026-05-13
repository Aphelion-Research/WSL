from __future__ import annotations

from .confidence import score_confidence
from .context import assemble
from .planner import plan
from .retrieval import retrieve
from .rerank import rerank
from .types import AskResult, AssembledContext, Confidence, RetrievalPlan, ScoredChunk


def _retrieve_pipeline(query: str, hints: dict | None = None, budget: int = 4096) -> tuple[RetrievalPlan, list[ScoredChunk], AssembledContext, Confidence]:
    retrieval_plan = plan(query, hints)
    chunks = rerank(retrieval_plan, retrieve(retrieval_plan))
    confidence = score_confidence(retrieval_plan, chunks)
    if confidence.decision == "escalate":
        widened = {
            **(hints or {}),
            "trace_id": retrieval_plan.trace_id,
            "top_k": max(retrieval_plan.top_k_bm25, retrieval_plan.top_k_vector) * 2,
            "metadata_filters": {},
        }
        retrieval_plan = plan(query, widened)
        chunks = rerank(retrieval_plan, retrieve(retrieval_plan))
        confidence = score_confidence(retrieval_plan, chunks)
    context = assemble(retrieval_plan, chunks, budget)
    return retrieval_plan, chunks, context, confidence


def _retrieve_only_answer(query: str, context: AssembledContext, confidence: Confidence) -> str:
    if confidence.decision == "refuse":
        return f"No strong RAGD evidence found for: {query}"
    lines = [f"RAGD retrieve-only answer for: {query}", "", "Evidence:"]
    for index, citation in enumerate(context.citations[:8], start=1):
        lines.append(f"{index}. {citation.label()}")
    lines.append("")
    lines.append(f"Confidence: {confidence.score:.2f} ({confidence.decision}) - {confidence.reason}")
    return "\n".join(lines)


def ask(query: str, *, generate: bool = False, budget: int | None = None) -> AskResult:
    retrieval_plan, chunks, context, confidence = _retrieve_pipeline(query, {"top_k": 10}, budget or 4096)
    generation_status: dict = {"requested": generate, "used": False}
    answer = _retrieve_only_answer(query, context, confidence)
    generated = False
    if generate and confidence.decision != "refuse":
        from local_llm.governor import Governor
        from local_llm.registry import GenerateRequest, provider_for_plan

        governor = Governor.default()
        execution = governor.choose(Governor.probe(), "ask")
        generation_status = {"requested": True, "used": False, "plan": execution.to_dict()}
        if execution.mode == "generate":
            provider = provider_for_plan(execution)
            health = provider.health()
            generation_status["provider_health"] = health.to_dict()
            if health.ok:
                prompt = f"Answer only from this evidence. Cite chunk ids. If insufficient, refuse.\n\n{context.text}\n\nQuestion: {query}\nAnswer:"
                tokens = provider.generate(GenerateRequest(prompt=prompt, model_id=execution.model_id, timeout_s=execution.timeout_s, stream=True))
                answer = "".join(token.text for token in tokens).strip() or answer
                generated = True
                generation_status["used"] = True
            else:
                generation_status["reason"] = health.message
        else:
            generation_status["reason"] = execution.reason
    return AskResult(
        ok=confidence.decision != "refuse",
        query=query,
        answer=answer,
        trace_id=retrieval_plan.trace_id,
        confidence=confidence,
        citations=context.citations,
        chunks=chunks,
        generated=generated,
        generation_status=generation_status,
    )
