# RAGD BUILD PROGRESS

## Completed

- [x] Existing MVP audited; original 8 tests passed under `ctest --test-dir build`.
- [x] CMake updated to project version `1.0.0`, vendor FetchContent cache, install target, and warning-free FetchContent timestamps.
- [x] Config loader expanded for `~/.ragd/config.json`, first-run default creation, `--config`, `--daemon`, and `RAGD_` environment overrides.
- [x] SQLite storage migrated additively for chunks, FTS, sessions, touches, decisions, TODOs, bus messages, locks, dead zones, chunk history, symbol edges, and kv metrics.
- [x] Hybrid retrieval upgraded with intent routing, BM25, TF cosine vector fallback, reciprocal-rank fusion, metadata enrichment, and query metrics.
- [x] Indexer upgraded to mark prior chunks deleted, chunk Markdown/config/code structurally, record git/root metadata where available, and extract TODOs on every pass.
- [x] Linux inotify watcher implemented with recursive directory registration, 300 ms debounce, delete handling, overflow rescan, and polling fallback.
- [x] REST API expanded for query, index, sessions, decisions, TODOs, handoff, temporal, dead-zone, bus, graph, metrics, and MCP endpoints.
- [x] MCP endpoint expanded for initialize, tools/list, tools/call, prompts/list, prompts/get, resources/list, and all 11 required tool names.
- [x] Scripts rewritten: install, uninstall, profile hook, CLI wrapper, agent init, default config, and systemd user unit.
- [x] Documentation rewritten: README, architecture, API reference, MCP tools, agent integration guide, and examples.
- [x] Added tests for intent router, session bus, temporal API, dead-zone report, and watcher.
- [x] Current test status: 13/13 passing.
- [x] Live smoke passed health, index, query, handoff, MCP tools/list, CLI wrapper, agent-init, bus persistence, and temporal query.
- [x] Dominion validation passed: forbidden-token scanner, domdata read-only notice, blocked order-send command, doctor, XAU tick/rates/ticks reads, and `dominion-health`.
- [x] `AGENT_HANDOFF.md`, top-level handoff/progress, and report files updated.

## In Progress

- [ ] Native WebSocket transport decision and implementation.

## Blocked

- Native WebSocket transport on the same HTTP port is not implemented in this build because `cpp-httplib` does not expose WebSocket upgrade handling. Bus persistence, locks, replay, and REST publish/read endpoints are functional.
- HNSW, tree-sitter grammars, libgit2 deep history backfill, and Ollama/OpenAI embedding calls remain pluggable design targets; the shipped fallback path is pure C++ structured chunking plus TF cosine vectors.
- `valgrind` is not installed on this host, so leak checking was not run.
- `install.sh` was not run, so the user systemd unit is not installed yet.

## Decisions Made

1. Preserve the existing MVP API and tests while adding richer fields and endpoints additively.
2. Keep SQLite IDs as integer primary keys for compatibility with the current codebase; expose them as `chunk_id`/`todo_id` in JSON.
3. Use TF cosine as the always-available vector backend so ragd works on a fresh WSL host without model services.
4. Use inotify directly on Linux and retain polling as a fallback.
5. Keep session bus persistence and advisory locks in SQLite, with REST surfaces until a native WebSocket stack is selected.

## Next Steps (if context limit hit)

1. Run `cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo && cmake --build build -j$(nproc) && ctest --test-dir build --output-on-failure`.
2. Start `./build/ragd --db /tmp/ragd-smoke.db --host 127.0.0.1 --port 7474 --path docs --daemon` and smoke `/health`, `/index`, `/query`, `/handoff`, and `/mcp`.
3. Run Dominion validation commands from `AGENTS.md`.
4. Update `AGENT_HANDOFF.md`, top-level `PROGRESS.md`, and a current report under `reports/`.
