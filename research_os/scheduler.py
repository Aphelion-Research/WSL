from __future__ import annotations

import time
from pathlib import Path

from . import db
from .chunker import chunk_markdown
from .config import ResearchPaths, ensure_dirs, paths
from .extractor import extract
from .adapters.registry import default_config, resolve_adapter
from .fetcher import safe_name, validate_url_for_source
from .models import Source
from .quality import assess_quality


def _source_from_row(row) -> Source:
    return Source(
        name=row["name"],
        base_url=row["base_url"],
        trust=row["trust"],
        rate_limit_sec=float(row["rate_limit_sec"]),
        enabled=bool(row["enabled"]),
        adapter_preference=str(row["adapter_preference"] or "requests"),
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
    _MAX_JOB_ATTEMPTS = 5

    for job in jobs:
        processed += 1
        if job["attempts"] >= _MAX_JOB_ATTEMPTS:
            db.mark_job(conn, job["id"], "failed", f"max attempts ({_MAX_JOB_ATTEMPTS}) reached")
            failed += 1
            continue
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
            validate_url_for_source(job["url"], source)
        except Exception as exc:
            db.mark_job(conn, job["id"], "failed", f"url not allowed for source: {exc}")
            failed += 1
            continue
        try:
            adapter = resolve_adapter(source.adapter_preference) or resolve_adapter("requests")
            if adapter is None:
                raise RuntimeError("no fetch adapters available")
            result = adapter.fetch(job["url"], source, default_config())
            if not result.ok:
                db.mark_job(conn, job["id"], "failed", result.error or "fetch failed")
                failed += 1
                last_fetch_by_source[source.name] = time.monotonic()
                continue

            raw_path = _write(p.raw / source.name / safe_name(result.final_url or result.url, ".html"), result.text)
            extracted = extract(
                result.text,
                url=result.url,
                final_url=result.final_url,
                source_name=source.name,
                fetched_at_utc=result.fetched_at_utc,
                content_hash=result.content_hash,
                trust=source.trust,
                adapter_name=result.adapter_name,
                content_type=result.content_type,
            )
            markdown_path = _write(p.markdown / source.name / safe_name(result.final_url or result.url, ".md"), extracted.markdown)
            chunks = chunk_markdown(extracted.markdown)
            dup = conn.execute("SELECT 1 FROM documents WHERE content_hash = ? LIMIT 1", (result.content_hash or "",)).fetchone() is not None
            quality = assess_quality(
                fetch_ok=True,
                source_allowed=True,
                text_length=extracted.text_length,
                has_title=bool(extracted.title and extracted.title != "Untitled"),
                chunk_count=len(chunks),
                duplicate_content_hash=dup,
                adapter_used=result.adapter_name,
                error_class=result.error_class,
            )
            document_id = db.upsert_document(
                conn,
                url=result.url,
                source_name=source.name,
                title=extracted.title,
                fetched_at=result.fetched_at_utc,
                status_code=int(result.status_code or 0),
                content_hash=str(result.content_hash or ""),
                raw_path=raw_path,
                markdown_path=markdown_path,
                text_length=extracted.text_length,
                trust=source.trust,
                metadata={
                    "user_agent": default_config().user_agent,
                    "adapter": result.adapter_name,
                    "final_url": result.final_url,
                    "content_type": result.content_type,
                    "normalization": extracted.normalization,
                    "quality": {"score": quality.score, "fields": quality.fields},
                },
            )
            db.replace_chunks(conn, document_id, result.url, source.name, chunks)
            db.mark_job(conn, job["id"], "succeeded")
            last_fetch_by_source[source.name] = time.monotonic()
            succeeded += 1
        except (OSError, RuntimeError, ValueError) as exc:
            db.mark_job(conn, job["id"], "failed", str(exc))
            failed += 1

    db.finish_run(conn, run_id, processed, succeeded, failed)
    return {"run_id": run_id, "processed": processed, "succeeded": succeeded, "failed": failed}
