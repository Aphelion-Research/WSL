---
synced: 2026-05-19 19:42
---
# Research OS

Research OS is Dominion V2's approved-source evidence collector. It fetches explicit queued URLs, cleans them to markdown, chunks them, stores provenance in SQLite, and prepares bundles for RAGD ingestion.

## Daily Commands

```bash
research init
research status
research doctor
research list-sources
research add-url https://docs.crawl4ai.com/ --source crawl4ai_docs
research run --limit 1
research list
research query "crawler"
research summarize DOCUMENT_ID
research ragd-status
research ingest-ragd
```

## Source Policy

Approved sources live in `research/sources.yaml`. A URL must match the source host and base path before it can be queued. Research OS does not spider arbitrary links.

## Runtime Files

- Database: `research/research.db`.
- Raw HTML: `research/raw/`.
- Markdown: `research/markdown/`.
- RAGD ingest bundle: `research/extracted/ragd_ingest/`.

## Failure Behavior

Fetch failures are recorded on the crawl job. Runs are bounded by `--limit`; there is no infinite crawler loop.
