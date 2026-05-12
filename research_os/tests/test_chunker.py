from __future__ import annotations

from research_os.chunker import chunk_markdown


def test_chunk_markdown_by_heading():
    chunks = chunk_markdown("# One\nText\n\n## Two\nMore text")
    assert len(chunks) == 2
    assert chunks[0].heading == "One"
    assert chunks[1].heading == "Two"
