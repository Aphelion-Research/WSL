from __future__ import annotations

import pytest

from research_os.fetcher import validate_url_for_source
from research_os.models import Source


def test_validate_url_blocks_outside_host():
    source = Source("docs", "https://example.com/docs", "high")
    with pytest.raises(ValueError):
        validate_url_for_source("https://evil.example/docs", source)


def test_validate_url_allows_source_path():
    source = Source("docs", "https://example.com/docs", "high")
    validate_url_for_source("https://example.com/docs/page", source)
