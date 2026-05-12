from __future__ import annotations

from research_os.adapters.browser_adapter import BrowserAdapter
from research_os.adapters.base import FetchConfig
from research_os.models import Source


def test_browser_adapter_unavailable_returns_actionable_error():
    adapter = BrowserAdapter()
    source = Source("docs", "https://example.com/docs", "high")
    result = adapter.fetch("https://example.com/docs/page", source, FetchConfig(timeout_s=0.1))
    assert result.ok is False
    assert result.adapter_name == "browser"
    assert result.error_class in {"missing_dependency", "browser_error"}

