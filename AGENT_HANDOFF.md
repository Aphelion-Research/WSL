# Dominion Agent Handoff

## Dominion V2 Superbuild Handoff - 2026-05-12

Current status: COMPLETE for the Dominion V2 MVP superbuild.

- Baseline report exists at `reports/dominion-v2-latest.md`.
- RAGD MCP first actions passed and showed RAGD `1.0.0`, TF-IDF backend, project indexing, and two open TODOs.
- `AGENTS.md` was upgraded into the Dominion platform contract with explicit RAGD-first workflow, safety, validation, reporting, research, data, and collaboration policies.
- Added platform layout and engineering standards docs.
- Added Research OS foundation under `research_os/` with runtime state under `research/`.
- Added optional Ollama-compatible local LLM adapter under `local_llm/`.
- Validation passed: Research OS pytest `7 passed`, local LLM pytest `3 passed`, and one approved `crawl4ai_docs` URL fetched/chunked successfully.
- Ollama is not running on `127.0.0.1:11434`; `llm doctor` reports disabled cleanly.
- RAGD ingest bridge passed and `research ingest-ragd` indexed the bundle through RAGD `POST /index`.
- RAGD storage now reuses unchanged chunk identity and live RAGD was restarted with the rebuilt binary.
- Added command center, dashboard, Codex/RAGD helper commands, and noninteractive-safe `warp`.
- Final report: `reports/dominion-v2-latest.md`.
- Next best task: add a JavaScript-capable Research OS fetch adapter, then add a RAGD cleanup command for historical duplicate deleted chunks.

Continuation commands:

```bash
cd ~/Dominion
research status || true
llm doctor || true
research ragd-status || true
dominion status || true
dominion-ui --once || true
cat reports/dominion-v2-latest.md
```

RUN_ID: `20260511-ragd-upgrade`

Dominion remains read-only for market data operations. No secrets were read or printed.

## Current State

- RAGD was upgraded substantially from the prior MVP.
- RAGD now builds with CMake and passes 13/13 C++ tests.
- Live smoke on `127.0.0.1:7474` passed health, index, query, handoff, MCP tools/list, CLI wrapper, agent-init, bus persistence, and temporal query.
- Dominion validation passed: `check_no_trading.py`, `domdata notice`, blocked `domdata order-send`, `domdata doctor`, `domdata xautick`, `domdata xaurates --count 5`, `domdata xauticks --start 2026-05-11T00:00:00Z --count 5`, and `dominion-health`.

## Most Important RAGD Notes

- Native WebSocket `/bus` is still not implemented. Bus messages, locks, replay-style reads, warnings, and MCP broadcast are persisted over REST/MCP.
- HNSW, tree-sitter, libgit2 history backfill, and external embedding APIs are not wired; the daemon uses structured regex chunking and TF cosine fallback.
- `install.sh` was not run, so `systemctl --user status ragd` reports the unit is not installed.
- `valgrind` is not installed, so leak checking was not run.

## Next Agent Should Do First

Read `ragd/AGENT_HANDOFF.md`, then decide whether WebSocket same-port support is required before installing the service.

## Useful Commands

```bash
cd ~/Dominion/ragd
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j$(nproc)
ctest --test-dir build --output-on-failure
./build/ragd --db /tmp/ragd-smoke.db --host 127.0.0.1 --port 7474 --path docs --daemon
```
