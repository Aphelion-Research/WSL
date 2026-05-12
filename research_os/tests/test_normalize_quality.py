from __future__ import annotations

from research_os.normalize import normalize_raw_text
from research_os.quality import assess_quality


def test_normalize_html_deterministic():
    raw = "<html><body><h1>Hi</h1><script>nope</script><p>Body</p></body></html>"
    n1 = normalize_raw_text(raw, content_type="text/html")
    n2 = normalize_raw_text(raw, content_type="text/html")
    assert n1.text == n2.text
    assert "nope" not in n1.text


def test_quality_score_basic_cases():
    q_ok = assess_quality(
        fetch_ok=True,
        source_allowed=True,
        text_length=1200,
        has_title=True,
        chunk_count=3,
        duplicate_content_hash=False,
        adapter_used="requests",
        error_class=None,
    )
    q_bad = assess_quality(
        fetch_ok=False,
        source_allowed=False,
        text_length=0,
        has_title=False,
        chunk_count=0,
        duplicate_content_hash=True,
        adapter_used="requests",
        error_class="timeout",
    )
    assert q_ok.score > q_bad.score

