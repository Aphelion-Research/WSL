# Dominion V2 Superbuild Report

Run timestamp: `2026-05-12T16:47:03-04:00`

## 1. Executive Summary

Dominion V2 now has a stronger platform contract, a working Research OS MVP, optional local LLM adapter, RAGD research ingestion, RAGD unchanged-content indexing idempotency, command center CLI, terminal dashboard, Codex/RAGD helpers, and improved tmux workflow. Trading remains blocked and no secret files were read.

## 2. Major Systems Built

- Platform contract: `AGENTS.md` now defines RAGD-first workflow, safety, validation, reporting, research, data, and collaboration policies.
- Research OS: `research_os/` package plus `research` CLI, SQLite schema, approved source registry, fetch/extract/chunk pipeline, and RAGD ingest bundle.
- Local LLM: `local_llm/` package plus `llm` CLI with graceful disabled behavior when Ollama is unavailable.
- RAGD bridge: `research ingest-ragd` writes provenance markdown under `research/extracted/ragd_ingest/` and calls RAGD `POST /index`.
- RAGD idempotency: unchanged chunks now reuse `filepath + line_start + line_end + content_hash` instead of growing storage forever.
- Command center: `dominion`, `dominion-ui`, `codexrag`, `codexstatus`, `codexprompt`, `codexstart`, and `warp`.

## 3. Files Changed

- Updated: `.gitignore`, `AGENTS.md`, `README.md`, `QUICKSTART.md`, `PROGRESS.md`, `AGENT_HANDOFF.md`.
- Updated docs: `docs/CODEX_WORKFLOW.md`, `docs/COLLABORATION.md`, `docs/RUNBOOK.md`, `docs/SECURITY.md`.
- Added docs: `docs/DOMINION_V2.md`, `docs/RESEARCH_OS.md`, `docs/LOCAL_LLM.md`, `docs/RAGD_CODEX_WORKFLOW.md`, `docs/COMMAND_CENTER.md`, `docs/TMUX_WORKFLOW.md`, `docs/PLATFORM_LAYOUT.md`, `docs/ENGINEERING_STANDARDS.md`.
- Added packages: `research_os/`, `local_llm/`.
- Added scripts: `scripts/dominion_cli.py`, `scripts/dominion_ui.py`, `scripts/codexrag.py`, and wrappers under `scripts/bin/`.
- Updated RAGD: `ragd/src/storage.cpp`, `ragd/tests/test_indexer.cpp`.
- Added runtime registry: `research/README.md`, `research/sources.yaml`.

## 4. New Commands Added

```bash
research
llm
dominion
dominion-ui
codexrag
codexstatus
codexstart
codexprompt
warp
```

Wrappers were installed to `~/.local/bin`.

## 5. Tests Passed

- RAGD: `cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo`, `cmake --build build -j$(nproc)`, `ctest --test-dir build --output-on-failure`: 13/13 passed.
- Research OS: `.venv/bin/python -m pytest research_os/tests -q`: 7 passed.
- Local LLM: `.venv/bin/python -m pytest local_llm/tests -q`: 3 passed.
- Research CLI: init/status/list-sources/add-url/run/list/doctor passed for one approved `crawl4ai_docs` URL.
- Command center: `dominion status`, `dominion doctor`, `dominion ragd`, `dominion research`, `dominion data`, `dominion llm`, `dominion start` passed.
- Codex helpers: `codexstatus`, `codexprompt`, `codexrag "domdata read only safety"` passed.
- TUI: `dominion-ui --help` and `dominion-ui --once` passed.
- tmux workflow: `warp list` and noninteractive `warp matin || true` passed.
- domdata safety: forbidden-token scanner, notice, blocked order-send, doctor, xautick, xaurates, xauticks, and collect-status passed.

## 6. Tests Failed

- No validation command failed in the final pass.
- Ollama is unavailable at `http://127.0.0.1:11434`; this is expected optional-disabled behavior, not a failure.

## 7. RAGD Status

- Health: `ok`.
- Live metrics after final validation: `active_chunks=691`, `chunks=1202`, `todos=5`, `embed_backend=tfidf`; final RAGD decisions were recorded.
- MCP tools/list works over HTTP.
- Live daemon was restarted in the `ragd` tmux session after rebuilding so the idempotency fix is active.
- Research ingest re-run showed stable RAGD chunk counts before and after: `chunks=1202`, `active_chunks=691`.

## 8. Research OS Status

- Sources: 5 approved sources loaded from `research/sources.yaml`.
- Queue: 1 crawl job.
- Documents: 1 fetched `crawl4ai_docs` document.
- Chunks: 17 Research OS document chunks.
- RAGD ingest: one markdown bundle file written and indexed.

## 9. Local LLM Status

- `llm doctor` works.
- Ollama is disabled/unreachable locally.
- No models were installed automatically.
- Manual setup remains documented in `docs/LOCAL_LLM.md`.

## 10. Codex/RAGD Workflow Status

- `AGENTS.md` requires `ragd_handoff_read`, task-specific `ragd_query`, local file inspection, validation, `ragd_remember`, and report updates.
- `codexrag` produces a prompt preamble plus top RAGD chunks.
- Codex config paths both contain RAGD MCP config.

## 11. Dominion Command Center Status

- `dominion status` summarizes Tailscale, SSH, tmux, RAGD, Codex MCP config, domdata read-only status, Research OS, and local LLM.
- `dominion doctor` passed all checks.
- `dominion-ui --once` prints a dashboard with Overview, RAGD, Research, Data, Codex, tmux, and Local LLM sections.

## 12. Security Status

- No secret files were read.
- `.gitignore` excludes Research OS runtime DB/raw/markdown/cache/logs/ingest output.
- `domdata` remains read-only and blocked trading commands remain blocked.
- Research OS only accepts URLs under approved source host/base paths.

## 13. domdata Read-only Status

- `domdata notice`: PASS.
- `domdata order-send || true`: PASS, blocked.
- `python domdata/check_no_trading.py`: PASS.
- MT5 read commands returned XAUUSD tick/rate/tick data.

## 14. Remaining Risks

- Historical deleted duplicate chunks created before the idempotency fix are not cleaned up yet.
- Research OS uses `requests` only; JavaScript-heavy docs need a future Playwright/crawl4ai adapter.
- RAGD still uses TF-IDF fallback retrieval in this environment.
- Command center JSON output is only complete for status/health.
- Local LLM remains disabled until Ollama is started and models are manually pulled.

## 15. Best Next Codex Prompt

```text
Use RAGD first. Inspect the new Research OS and command center. Add a JavaScript-capable fetch adapter for approved sources, then add a RAGD cleanup/migration command for historical duplicate chunks. Preserve domdata read-only safety and update reports.
```

## 16. Daily Commands For Matin

```bash
cd ~/Dominion
dominion start
dominion status
dominion-ui --once
warp matin
```

## 17. Daily Commands For Dan

```cmd
tailscale status
tailscale ping 100.95.35.80
ssh Martin@100.95.35.80
```

Inside SSH:

```bash
cd ~/Dominion
warp dan
dominion status
```

## 18. Before Scaling To More Users

- Add user/role docs and shared session naming policy beyond Matin/Dan.
- Add structured JSON for all command center subcommands.
- Add Research OS source health checks and rate-limit audit logs.
- Add RAGD maintenance commands for schema migration and historical cleanup.
- Decide whether RAGD should run as a user service instead of a tmux-managed process.

## 19. Intentionally Deferred

- Installing Ollama models.
- Building a JavaScript/browser crawler.
- Cleaning old duplicate RAGD chunk rows.
- Adding enterprise auth, permissions, or remote multi-node coordination.
- Committing pre-existing untracked files: `ragd/scripts/ragd_mcp_stdio.py` and `tmp/`.

## Commit

Safe files were committed with message `v2: build Dominion research OS and RAGD-native workflow`.
