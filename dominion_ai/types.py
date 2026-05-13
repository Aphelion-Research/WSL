from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class RetrievalPlan:
    query: str
    intent: str
    expanded_terms: list[str]
    metadata_filters: dict[str, Any]
    top_k_bm25: int
    top_k_vector: int
    rerank_strategy: str
    temporal_constraints: dict[str, Any] | None
    trace_id: str
    mode: str = "hybrid"
    intent_confidence: float = 0.65


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    filepath: str
    line_start: int
    line_end: int
    content_hash: str

    def label(self) -> str:
        return f"{self.filepath}:{self.line_start}-{self.line_end} [{self.chunk_id}]"


@dataclass(frozen=True)
class ScoredChunk:
    chunk_id: str
    document_id: str
    filepath: str
    line_start: int
    line_end: int
    content: str
    score: float
    bm25_score: float
    vector_score: float
    rerank_score: float
    rrf_score: float
    confidence: float
    content_hash: str
    citations: list[str]
    lang: str = ""
    chunk_type: str = ""
    symbol_name: str = ""

    def citation(self) -> Citation:
        return Citation(self.chunk_id, self.filepath, self.line_start, self.line_end, self.content_hash)


@dataclass(frozen=True)
class ContextSection:
    filepath: str
    chunks: list[ScoredChunk]
    token_estimate: int
    text: str


@dataclass(frozen=True)
class AssembledContext:
    sections: list[ContextSection]
    token_estimate: int
    budget: int
    citations: list[Citation]
    trace_id: str

    @property
    def text(self) -> str:
        return "\n\n".join(section.text for section in self.sections)


@dataclass(frozen=True)
class Confidence:
    score: float
    factors: dict[str, float]
    decision: Literal["ok", "escalate", "refuse"]
    reason: str


@dataclass(frozen=True)
class AskResult:
    ok: bool
    query: str
    answer: str
    trace_id: str
    confidence: Confidence
    citations: list[Citation]
    chunks: list[ScoredChunk]
    generated: bool = False
    generation_status: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["citations"] = [asdict(citation) | {"label": citation.label()} for citation in self.citations]
        return data
