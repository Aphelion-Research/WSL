# Dominion Research OS Runtime

This directory stores approved-source research state for Dominion V2.

- `sources.yaml`: approved source registry.
- `research.db`: SQLite queue, document, chunk, note, run, and health database.
- `raw/`: fetched HTML.
- `markdown/`: cleaned markdown documents.
- `extracted/`: derived bundles, including RAGD ingest bundles.
- `reports/`: research reports.
- `logs/`: research command logs.
- `cache/`: local fetch/cache state.

Research OS does not crawl arbitrary internet locations. Add approved sources first, then enqueue explicit URLs.
