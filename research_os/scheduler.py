from __future__ import annotations

import time
from pathlib import Path

from . import db
from .chunker import chunk_markdown
from .config import ResearchPaths, ensure_dirs, paths
from .extractor import extract
from .fetcher import FetchError, fetch, safe_name
from .models import Source


def _source_from_row(row) -> Source:
    return Source(
        name=row["name"],
        base_url=row["base_url"],
        trust=row["trust"],
        rate_limit_sec=float(row["rate_limit_sec"]),
        enabled=bool(row["enabled"]),
    )


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return str(path)


def run(limit: int, p: ResearchPaths | None = None) -> dict[str, int]:
    p = p or paths()
    ensure_dirs(p)
    conn = db.connect(p.db)
    db.initialize(conn)
    run_id = db.create_run(conn)
    jobs = db.next_jobs(conn, limit)
    processed = succeeded = failed = 0
    last_fetch_by_source: dict[str, float] = {}

    for job in jobs:
        processed += 1
        source_row = db.get_source(conn, job["source_name"])
        if not source_row:
            db.mark_job(conn, job["id"], "failed", "source not found")
            failed += 1
            continue
        source = _source_from_row(source_row)
        if not source.enabled:
            db.mark_job(conn, job["id"], "failed", "source disabled")
            failed += 1
            continue
        elapsed = time.monotonic() - last_fetch_by_source.get(source.name, 0)
        if elapsed < source.rate_limit_sec:
            time.sleep(source.rate_limit_sec - elapsed)
        try:
            result = fetch(job["url"], source)
            raw_path = _write(p.raw / source.name / safe_name(result.url, ".html"), result.content)
            extracted = extract(
                result.content,
                url=result.url,
                source_name=source.name,
                fetched_at=result.fetched_at,
                content_hash=result.content_hash,
                trust=source.trust,
            )
            markdown_path = _write(p.markdown / source.name / safe_name(result.url, ".md"), extracted.markdown)
            document_id = db.upsert_document(
                conn,
                url=result.url,
                source_name=source.name,
                title=extracted.title,
                fetched_at=result.fetched_at,
                status_code=result.status_code,
                content_hash=result.content_hash,
                raw_path=raw_path,
                markdown_path=markdown_path,
                text_length=extracted.text_length,
                trust=source.trust,
                metadata={"user_agent": "DominionResearchOS/0.1"},
            )
            db.replace_chunks(conn, document_id, result.url, source.name, chunk_markdown(extracted.markdown))
            db.mark_job(conn, job["id"], "succeeded")
            last_fetch_by_source[source.name] = time.monotonic()
            succeeded += 1
        except (FetchError, OSError, RuntimeError) as exc:
            db.mark_job(conn, job["id"], "failed", str(exc))
            failed += 1

    db.finish_run(conn, run_id, processed, succeeded, failed)
    return {"run_id": run_id, "processed": processed, "succeeded": succeeded, "failed": failed}
