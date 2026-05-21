---
synced: 2026-05-20 18:19
---
# Dominion V2 Platform Layout

Dominion V2 is organized as a local operating environment, not a loose script directory. New systems should land in the canonical locations below unless there is a clear reason to extend this contract.

```text
/home/Martin/Dominion/
├── AGENTS.md
├── README.md
├── QUICKSTART.md
├── PROGRESS.md
├── AGENT_HANDOFF.md
├── docs/
├── reports/
├── scripts/
├── prompts/
├── research/
├── research_os/
├── ragd_embed/
├── ragd_hnsw/
├── ragd_chunker/
├── ragd_graph/
├── ragd_vault/
├── ragd/
├── domdata/
├── tests/
├── data/
│   ├── raw/
│   ├── normalized/
│   └── dominion.duckdb
└── secrets/
```

## Canonical Responsibilities

- `AGENTS.md`: platform contract for agents and humans.
- `docs/`: stable operator and developer documentation.
- `reports/`: run reports, validation logs, and handoff summaries.
- `scripts/bin/`: source-controlled command wrappers copied or linked into `~/.local/bin`.
- `prompts/`: reusable prompts and workflow templates.
- `research/`: Research OS runtime state, database, fetched documents, extracted markdown, logs, cache, and reports.
- `research_os/`: Python package for the approved-source crawler, document processing, and RAGD ingestion bridge.
- `ragd_embed/`: external embedding provider wrappers, cache, and embedding pipeline.
- `ragd_hnsw/`: persistent semantic index sync and query service.
- `ragd_chunker/`: AST-aware source chunking service consumed by RAGD.
- `ragd_graph/`: symbol/import/call graph derived from RAGD chunks.
- `ragd_vault/`: Obsidian vault generator and vault doctor.
- `ragd/`: C++ RAGD daemon, MCP bridge, docs, and tests.
- `domdata/`: read-only MT5/XAUUSD data CLI and safety scanner.
- `tests/`: top-level platform smoke tests when a test does not belong to a package.
- `data/`: raw and normalized market data; not committed.
- `secrets/`: local secrets; never indexed, printed, logged, copied into reports, or committed.

## Runtime State

Runtime files should be deterministic and recoverable:

- Research DB: `research/research.db`.
- Research raw HTML: `research/raw/`.
- Research markdown: `research/markdown/`.
- Research RAGD bundles: `research/extracted/ragd_ingest/`.
- Operational reports: `reports/`.
- RAGD persistent DB: `~/.ragd/ragd.db` unless overridden by service configuration.

## Extension Rules

- Add a package when behavior needs tests or imports.
- Add a command wrapper when humans or agents run it directly.
- Add docs when behavior affects daily operation, safety, onboarding, or recovery.
- Keep generated caches and large artifacts out of Git.
