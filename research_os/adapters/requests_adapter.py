from __future__ import annotations

from datetime import UTC, datetime

import requests

from ..fetcher import content_hash, validate_url_for_source
from ..models import FetchResult, Source
from .base import FetchConfig


class RequestsAdapter:
    name = "requests"

    def fetch(self, url: str, source: Source, config: FetchConfig) -> FetchResult:
        try:
            validate_url_for_source(url, source)
        except Exception as exc:
            return FetchResult(
                ok=False,
                url=url,
                final_url=None,
                source_name=source.name,
                adapter_name=self.name,
                fetched_at_utc=_utc_now(),
                error=str(exc),
                error_class="source_rejected",
            )

        try:
            response = requests.get(url, headers={"User-Agent": config.user_agent}, timeout=config.timeout_s)
            status_code = int(response.status_code)
            if status_code >= 400:
                return FetchResult(
                    ok=False,
                    url=url,
                    final_url=str(response.url) if getattr(response, "url", None) else None,
                    source_name=source.name,
                    adapter_name=self.name,
                    fetched_at_utc=_utc_now(),
                    status_code=status_code,
                    content_type=response.headers.get("Content-Type"),
                    error=f"HTTP {status_code}",
                    error_class="http_error",
                    metadata={"headers": {"content_type": response.headers.get("Content-Type")}},
                )

            text = response.text or ""
            return FetchResult(
                ok=True,
                url=url,
                final_url=str(response.url) if getattr(response, "url", None) else None,
                source_name=source.name,
                adapter_name=self.name,
                fetched_at_utc=_utc_now(),
                status_code=status_code,
                content_type=response.headers.get("Content-Type"),
                text=text,
                content_hash=content_hash(text),
                metadata={"headers": {"content_type": response.headers.get("Content-Type")}},
            )
        except requests.Timeout as exc:
            return FetchResult(
                ok=False,
                url=url,
                final_url=None,
                source_name=source.name,
                adapter_name=self.name,
                fetched_at_utc=_utc_now(),
                error=str(exc) or "timeout",
                error_class="timeout",
            )
        except requests.RequestException as exc:
            return FetchResult(
                ok=False,
                url=url,
                final_url=None,
                source_name=source.name,
                adapter_name=self.name,
                fetched_at_utc=_utc_now(),
                error=str(exc),
                error_class="request_error",
            )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

