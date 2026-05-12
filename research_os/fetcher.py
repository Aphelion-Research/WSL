from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from urllib.parse import urlparse

import requests

from .config import USER_AGENT
from .models import FetchResult, Source


class FetchError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_name(url: str, suffix: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}{suffix}"


def validate_url_for_source(url: str, source: Source) -> None:
    parsed = urlparse(url)
    base = urlparse(source.base_url)
    if parsed.scheme not in {"http", "https"}:
        raise FetchError(f"unsupported URL scheme: {parsed.scheme}")
    if parsed.netloc != base.netloc:
        raise FetchError(f"URL host {parsed.netloc} is outside approved source {base.netloc}")
    if base.path and not parsed.path.startswith(base.path.rstrip("/")):
        raise FetchError(f"URL path {parsed.path} is outside approved base path {base.path}")


def fetch(url: str, source: Source, timeout: float = 15.0) -> FetchResult:
    validate_url_for_source(url, source)
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    if response.status_code >= 400:
        raise FetchError(f"HTTP {response.status_code} for {url}")
    text = response.text
    return FetchResult(
        url=url,
        source_name=source.name,
        status_code=response.status_code,
        content=text,
        content_hash=content_hash(text),
        fetched_at=utc_now(),
    )
