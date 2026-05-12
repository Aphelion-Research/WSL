# HANDOFF NOTE

Session ID: local-codex-ragd-upgrade-20260511
Agent: codex
Started: 2026-05-11 late evening America/Toronto
Ended: 2026-05-11 late evening America/Toronto
Git Branch: main
Git Commit: 2b5b18a069c9301c013c2dd3190dbc79028ff315

## What I Did

Upgraded `ragd` from the prior MVP into a broader working C++17 daemon surface:

- Expanded config loading, default config creation, CLI flags, and `RAGD_` env overrides.
- Added additive SQLite migrations for chunks, FTS, sessions, touches, decisions, TODOs, bus messages, locks, dead zones, chunk history, symbol edges, and metrics.
- Implemented structural chunking for Markdown, config files, Python, and C-like code, plus TODO extraction and git metadata capture.
- Implemented Linux inotify watcher with debounce and polling fallback.
- Expanded HTTP endpoints for query, index, session, decisions, TODOs, handoff, temporal, dead-zone, bus, graph, metrics, and MCP.
- Implemented all 11 requested MCP tool names plus initialize, tools/list, tools/call, prompts/list, prompts/get, and resources/list.
- Rewrote install/service/profile/CLI/agent-init scripts and docs.
- Added tests for intent routing, session bus, temporal surfaces, dead-zone reporting, and watcher behavior.

## What I Intentionally Left Unfinished (and Why)

- Native WebSocket transport on `ws://localhost:7474/bus` is not implemented. `cpp-httplib` in this tree does not expose WebSocket upgrade handling; current bus functionality is persisted and available over REST plus MCP broadcast.
- HNSW, tree-sitter grammar compilation, libgit2 in-memory commit backfill, and Ollama/OpenAI embedding calls are not wired. The shipped path is pure C++ structured chunking and TF cosine retrieval so the daemon works without external model services.
- `systemctl --user status ragd` was not active because `install.sh` was not run in this session.
- `valgrind` was not run because it is not installed on this WSL image.

## The Most Dangerous Thing I Know Right Now

The daemon is functional, but callers expecting a real WebSocket upgrade at `/bus` will not get one. Do not advertise the bus as native WebSocket until websocketpp/uWebSockets is integrated or the HTTP server is replaced.

## What the Next Agent Should Do FIRST

Decide whether native WebSocket same-port support is mandatory. If yes, replace the HTTP serving layer with websocketpp/Boost.Asio or add a documented second WebSocket port, then add an integration test using a real WebSocket client.

## TODOs I Created This Session

- [ ] Add production WebSocket transport for `/bus`.
- [ ] Replace TF cosine fallback with HNSW plus pluggable embedding calls when Ollama/OpenAI endpoints are available.
- [ ] Replace regex chunking with tree-sitter grammars for the requested languages.
- [ ] Add libgit2 deep history backfill for the last N commits.
- [ ] Run valgrind after installing it.

## TODOs I Resolved This Session

- [x] Expanded the original 8-test MVP to 13 passing tests.
- [x] Added default config, install, service, shell hook, CLI, MCP configs, docs, and examples.
- [x] Fixed CMake FetchContent developer warnings.

## Files I Modified

- `ragd/src/*`, `ragd/include/ragd/*`: config, storage, indexing, watcher, retrieval, API, MCP, temporal, bus, dead-zone logic.
- `ragd/tests/*`: five new feature tests and CMake registration.
- `ragd/scripts/*`, `ragd/install.sh`, `ragd/uninstall.sh`: installation and agent workflow scripts.
- `ragd/docs/*`, `ragd/README.md`, `ragd/examples/*`: operator and integration documentation.
- `.claude/mcp_config.json`, `.cursor/mcp.json`: added explicit HTTP MCP transport.

## Key Decisions Made

1. Preserve integer primary keys for compatibility with the existing MVP and tests.
2. Use additive schema migration so existing `~/.ragd` databases are not destroyed.
3. Keep the fallback vector store dependency-free so fresh WSL installs can query immediately.
4. Treat WebSocket support as a known gap instead of faking protocol compliance.

## Open Questions (things I don't know)

- Whether the deployment should prefer same-port WebSocket support or a separate bus port.
- Whether the target host will have Ollama available by default.
- Whether `install.sh` should be run now or left to the human because it uses `sudo apt-get` and writes `/usr/local/bin` plus `/etc/profile.d`.
