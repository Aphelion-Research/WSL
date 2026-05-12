from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    base_url: str
    trust: str
    rate_limit_sec: float = 2.0
    enabled: bool = True
    adapter_preference: str = "requests"


@dataclass(frozen=True)
class FetchResult:
    ok: bool
    url: str
    final_url: str | None
    source_name: str
    adapter_name: str
    fetched_at_utc: str
    status_code: int | None = None
    content_type: str | None = None
    text: str = ""
    content_hash: str | None = None
    error: str | None = None
    error_class: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExtractedDocument:
    title: str
    markdown: str
    text_length: int
    normalization: dict[str, Any]


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    heading: str
    content: str
    content_hash: str
    token_estimate: int
