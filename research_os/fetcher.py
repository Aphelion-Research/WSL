from __future__ import annotations

import hashlib
from urllib.parse import urlparse

from .models import Source


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_name(url: str, suffix: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{digest}{suffix}"


def validate_url_for_source(url: str, source: Source) -> None:
    parsed = urlparse(url)
    base = urlparse(source.base_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported URL scheme: {parsed.scheme}")
    if parsed.netloc != base.netloc:
        raise ValueError(f"URL host {parsed.netloc} is outside approved source {base.netloc}")
    if base.path and not parsed.path.startswith(base.path.rstrip("/")):
        raise ValueError(f"URL path {parsed.path} is outside approved base path {base.path}")
