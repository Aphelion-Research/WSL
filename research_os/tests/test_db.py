from __future__ import annotations

from research_os import db
from research_os.models import Source


def test_db_sources_jobs_documents(tmp_path):
    conn = db.connect(tmp_path / "research.db")
    db.initialize(conn)
    db.upsert_source(conn, Source("docs", "https://example.com/docs", "high"))
    db.add_job(conn, "https://example.com/docs/a", "docs")
    assert len(db.list_sources(conn)) == 1
    assert len(db.next_jobs(conn, 10)) == 1
    document_id = db.upsert_document(
        conn,
        url="https://example.com/docs/a",
        source_name="docs",
        title="A",
        fetched_at=db.utc_now(),
        status_code=200,
        content_hash="abc",
        raw_path="/tmp/a.html",
        markdown_path="/tmp/a.md",
        text_length=3,
        trust="high",
    )
    assert document_id > 0
    assert db.counts(conn)["documents"] == 1
