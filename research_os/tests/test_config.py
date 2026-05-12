from __future__ import annotations

from research_os.config import DEFAULT_SOURCES, load_sources, write_default_sources


def test_default_sources_roundtrip(tmp_path):
    path = tmp_path / "sources.yaml"
    write_default_sources(path)
    sources = load_sources(path)
    assert len(sources) == len(DEFAULT_SOURCES)
    assert sources[0].name == "crawl4ai_docs"
