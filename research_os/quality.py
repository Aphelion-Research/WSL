from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityReport:
    score: int
    fields: dict[str, object]


def assess_quality(
    *,
    fetch_ok: bool,
    source_allowed: bool,
    text_length: int,
    has_title: bool,
    chunk_count: int,
    duplicate_content_hash: bool,
    adapter_used: str,
    error_class: str | None,
) -> QualityReport:
    fields: dict[str, object] = {
        "fetch_ok": fetch_ok,
        "source_allowed": source_allowed,
        "text_length": text_length,
        "has_title": has_title,
        "chunk_count": chunk_count,
        "duplicate_content_hash": duplicate_content_hash,
        "adapter_used": adapter_used,
        "error_class": error_class,
    }

    score = 0
    score += 30 if fetch_ok else 0
    score += 15 if source_allowed else 0
    score += 15 if text_length >= 400 else 5 if text_length >= 100 else 0
    score += 10 if has_title else 0
    score += 10 if chunk_count >= 1 else 0
    score += 10 if not duplicate_content_hash else 0
    score += 10 if adapter_used in {"requests", "browser"} else 0
    if error_class:
        score = max(0, score - 20)
    return QualityReport(score=int(score), fields=fields)

