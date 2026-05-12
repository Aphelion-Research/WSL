from __future__ import annotations

from datetime import UTC, datetime

from ..fetcher import content_hash, validate_url_for_source
from ..models import FetchResult, Source
from .base import FetchConfig


class BrowserAdapter:
    name = "browser"

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
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as exc:
            return FetchResult(
                ok=False,
                url=url,
                final_url=None,
                source_name=source.name,
                adapter_name=self.name,
                fetched_at_utc=_utc_now(),
                error=f"Playwright unavailable: {exc}",
                error_class="missing_dependency",
                metadata={"hint": "Install playwright and browsers, then re-run with --adapter browser."},
            )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=config.user_agent)
                response = page.goto(url, wait_until="networkidle", timeout=int(config.timeout_s * 1000))
                html = page.content() or ""
                final_url = page.url
                status = int(response.status) if response is not None else None
                ct = response.headers.get("content-type") if response is not None else None
                browser.close()
                ok = status is None or status < 400
                return FetchResult(
                    ok=ok,
                    url=url,
                    final_url=final_url,
                    source_name=source.name,
                    adapter_name=self.name,
                    fetched_at_utc=_utc_now(),
                    status_code=status,
                    content_type=ct,
                    text=html,
                    content_hash=content_hash(html) if html else None,
                    error=None if ok else f"HTTP {status}",
                    error_class=None if ok else "http_error",
                    metadata={"rendered": True},
                )
        except Exception as exc:
            return FetchResult(
                ok=False,
                url=url,
                final_url=None,
                source_name=source.name,
                adapter_name=self.name,
                fetched_at_utc=_utc_now(),
                error=str(exc),
                error_class="browser_error",
            )


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

