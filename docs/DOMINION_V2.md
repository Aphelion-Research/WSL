# Dominion V2

Dominion V2 is a local operating environment for agent-assisted engineering, research, and read-only market data work.

## Operating Model

1. Codex codes.
2. RAGD remembers code, docs, decisions, TODOs, handoffs, and research bundles.
3. Research OS collects evidence from approved sources only.
4. Local LLM adapters summarize and classify when Ollama is available.
5. `domdata` provides read-only MT5/XAUUSD data.
6. `dominion` and `dominion-ui` expose operational status.
7. tmux/SSH/Tailscale provide shared access for Matin and Dan.

## What Is Automatic

- `research init` creates the SQLite schema and imports approved sources.
- `research run --limit N` processes bounded queued jobs.
- `research ingest-ragd` creates a markdown bundle and calls RAGD `/index`.
- `dominion status` summarizes RAGD, tmux, Codex MCP config, Research OS, local LLM, and domdata safety.

## What Is Not Automatic

- No arbitrary internet crawling.
- No local model downloads.
- No trading execution.
- No secret indexing or reporting.
- No tmux auto-attach from shell startup files.

## Scaling Principles

- Stable commands before ad hoc scripts.
- Explicit runtime directories.
- SQLite schemas with guarded initialization.
- Health and doctor commands for each subsystem.
- Reports that distinguish passed, failed, partial, and untested states.
- RAGD memory updates for decisions that future agents need.

## Current MVP Limits

- Local LLM is optional and currently reports disabled if Ollama is not running.
- RAGD uses TF-IDF fallback retrieval in the current environment.
- Research OS fetches static pages with `requests`; JavaScript-heavy sources may need a future Playwright/crawl4ai adapter.
