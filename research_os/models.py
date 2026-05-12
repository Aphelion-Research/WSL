from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    base_url: str
    trust: str
    rate_limit_sec: float = 2.0
    enabled: bool = True


@dataclass(frozen=True)
class FetchResult:
    url: str
    source_name: str
    status_code: int
    content: str
    content_hash: str
    fetched_at: str


@dataclass(frozen=True)
class ExtractedDocument:
    title: str
    markdown: str
    text_length: int


@dataclass(frozen=True)
class DocumentChunk:
    chunk_index: int
    heading: str
    content: str
    content_hash: str
    token_estimate: int
