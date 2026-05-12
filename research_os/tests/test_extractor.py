from __future__ import annotations

from research_os.extractor import extract


def test_extract_markdown_metadata():
    doc = extract(
        "<html><head><title>Title</title></head><body><nav>x</nav><h1>Hello</h1><p>Body</p></body></html>",
        url="https://example.com/docs",
        final_url="https://example.com/docs",
        source_name="docs",
        fetched_at_utc="2026-05-12T00:00:00Z",
        content_hash="abc",
        trust="high",
        adapter_name="requests",
        content_type="text/html",
    )
    assert "source_name: docs" in doc.markdown
    assert "adapter: requests" in doc.markdown
    assert "# Title" in doc.markdown
    assert "Body" in doc.markdown
