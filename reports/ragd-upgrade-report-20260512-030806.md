# RAGD Upgrade Report

RUN_ID: `20260511-ragd-upgrade`
Local time: `2026-05-11T23:08:06-0400`
UTC: `2026-05-12T03:08:06Z`

## Summary

RAGD was upgraded from the prior MVP into a broader working C++17 daemon surface. It now has expanded SQLite storage, config loading, structured chunking, inotify watching, hybrid retrieval, REST endpoints, MCP tools, CLI/service scripts, documentation, and 13 passing C++ tests.

## Validation Passed

- `cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo`
- `cmake --build build -j$(nproc)`
- `ctest --test-dir build --output-on-failure`: 13/13 passed
- Live smoke on `127.0.0.1:7474`:
  - `GET /health`
  - `POST /index`
  - `POST /query`
  - `GET /handoff`
  - `POST /mcp` `tools/list` returned 11 tools
  - CLI wrapper through `/tmp/ragd-query`
  - `source scripts/agent-init.sh smoke-agent`
  - `POST /temporal/query`
- Dominion safety validation:
  - `python ~/Dominion/domdata/check_no_trading.py`
  - `domdata notice`
  - `domdata order-send || true`
  - `domdata doctor`
  - `domdata xautick`
  - `domdata xaurates --count 5`
  - `domdata xauticks --start 2026-05-11T00:00:00Z --count 5`
  - `dominion-health`

## Known Gaps

- Native WebSocket `/bus` is not implemented. REST/MCP bus persistence and locks work.
- HNSW, tree-sitter, libgit2 deep history, and external embedding calls are not wired. Current retrieval uses TF cosine fallback.
- `install.sh` was not run, so the systemd user service is not installed.
- `valgrind` is not installed, so leak checking was not run.

## Files Of Interest

- `ragd/PROGRESS.md`
- `ragd/AGENT_HANDOFF.md`
- `ragd/docs/architecture.md`
- `ragd/docs/api_reference.md`
- `ragd/docs/mcp_tools.md`
- `ragd/docs/agent_integration_guide.md`
