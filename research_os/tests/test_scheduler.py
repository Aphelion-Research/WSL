from __future__ import annotations

from research_os import db
from research_os.models import Source


def test_next_jobs_respects_limit(tmp_path):
    conn = db.connect(tmp_path / "research.db")
    db.initialize(conn)
    db.upsert_source(conn, Source("docs", "https://example.com/docs", "high"))
    db.add_job(conn, "https://example.com/docs/a", "docs")
    db.add_job(conn, "https://example.com/docs/b", "docs")
    assert len(db.next_jobs(conn, 1)) == 1
