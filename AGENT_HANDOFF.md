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
- Pytest stable by default: repo-root `pytest.ini` forces `--import-mode=importlib` so `python -m pytest -q` works cleanly across `domdata/`, `local_llm/`, and `research_os/` tests.
- Fresh-clone bootstrap: `requirements.txt` + `scripts/bootstrap_python.sh` create `.venv`, install deps, and validate `research doctor`, `llm doctor`, pytest, and `python domdata/check_no_trading.py`.
- Collaboration helpers no longer print a hardcoded Tailscale IP: `scripts/bin/connectinfo` and `scripts/bin/domshare` now use `tailscale ip -4`.

Continuation commands:

```bash
cd ~/Dominion
./scripts/bootstrap_python.sh
research status || true
llm doctor || true
research ragd-status || true
dominion status || true
dominion-ui --once || true
cat reports/dominion-v2-latest.md
```

RUN_ID: `20260511-ragd-upgrade`

Dominion remains read-only for market data operations. No secrets were read or printed.

## Dominion V2 Cleanup - 2026-05-12

Portability cleanup after GitHub push: removed hardcoded Tailscale IPs, made paths configurable via env, and tightened repo hygiene. No secrets were read or printed.

RAGD-first notes:

- `ragd_handoff_read` shell command was not found in this environment (`command not found`).
- Attempting `ragd_handoff_read` via `python -c "from ragd.scripts.ragd_mcp_stdio import ragd_handoff_read; ..."` failed to connect to `http://127.0.0.1:7474/mcp` with `[Errno 1] Operation not permitted` (RAGD HTTP unreachable in this run). No RAGD writes were performed.

Commands run (this cleanup):

```bash
cd ~/Dominion
git status --short
grep -RInE '100\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|ssh Martin@100\\.' README.md QUICKSTART.md PROGRESS.md AGENT_HANDOFF.md docs reports scripts 2>/dev/null
python -m pytest -q
python domdata/check_no_trading.py
./scripts/bootstrap_python.sh
```

Pass/fail:

- Hardcoded collaboration IP scan: PASS (no matches).
- `python -m pytest -q`: PASS (16 passed).
- `python domdata/check_no_trading.py`: PASS.
- `./scripts/bootstrap_python.sh`: PASS (pip attempted network access but proceeded with installed deps; `llm doctor` reports localhost unreachable as expected).

## Dominion V2 Final Polish - 2026-05-12

Tiny correctness pass:

- `docs/DAN_SETUP_CMD.md`: Windows CMD block now contains only Windows-available commands; `connectinfo` is explicitly Matin-side inside WSL/Dominion.
- Removed `connectinfo` from Windows CMD blocks in reports.
- `scripts/home-files/dominionrc`: no literal `<tailscale-ip>` placeholder export; now respects pre-set `DOMINION_SSH_HOST` without forcing a value.
- `scripts/dominion_cli.py`: clarified that `dominion start` only manages local default RAGD `127.0.0.1:7474` even if `RAGD_URL` points elsewhere.

Commands run (final polish):

```bash
cd ~/Dominion
grep -RInE '100\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|ssh Martin@100\\.' README.md QUICKSTART.md PROGRESS.md AGENT_HANDOFF.md docs reports scripts 2>/dev/null
grep -RIn 'connectinfo' docs reports PROGRESS.md AGENT_HANDOFF.md scripts
grep -RIn 'DOMINION_SSH_HOST=\"<tailscale-ip>\"' scripts
python -m pytest -q
python domdata/check_no_trading.py
./scripts/bootstrap_python.sh
git status --short
```

Pass/fail:

- Hardcoded IP scan: PASS (no matches).
- `connectinfo` scan: PASS (no Windows CMD blocks tell Dan to run it; Matin-side only).
- Placeholder scan: PASS (no `DOMINION_SSH_HOST=\"<tailscale-ip>\"`).
- `python -m pytest -q`: PASS.
- `python domdata/check_no_trading.py`: PASS.
- `./scripts/bootstrap_python.sh`: PASS (same optional localhost/DNS notes as prior run).

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
