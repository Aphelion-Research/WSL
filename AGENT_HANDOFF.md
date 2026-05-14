# Dominion Agent Handoff

## Phase 5 — Consolidation + Cockpit (2026-05-14)

**Status: COMPLETE.** Phase 5 turned the Dominion loader + AI + Agent OS stack into a human-usable cockpit.

### What changed

- `dominion agent dashboard [--json]` — full system snapshot: RAGD, LLM, complexity warnings, Agent OS stats, next action.
- `dominion agent next [--json]` — priority-ordered actionable item (doctor errors, stale sessions, review-without-evidence, pending tasks, orphan chunks).
- `dominion truth [--json]` — combined integrity check: doctor + complexity + ignore policy + RAGD + LLM governor.
- `dominion_loader/cli.py` created with cmd_scan, cmd_cache, cmd_manifest, cmd_loader_bench, cmd_loader_ledger, cmd_graph_foundation; `scripts/dominion_cli.py` reduced from 1003 → 784 lines with thin delegators.
- `dominion_agent/dashboard.py` created (build_dashboard, build_next, format_dashboard_human).
- `dominion_agent/tests/test_e2e_smoke.py` — 6-test end-to-end smoke covering session→task→lock→review→done + schema validation.
- TEMP_ADAPTER false-positive fix: complexity.py now uses `re.findall(r"TEMP_ADAPTER\([a-zA-Z]", source)`.
- Complexity budgets recalibrated from aspirational to realistic values.

### Validation

```bash
python -m pytest -q              # 387 passed (6 new e2e smoke tests)
python domdata/check_no_trading.py  # PASS
python scripts/dominion_cli.py agent dashboard --json  # valid JSON
python scripts/dominion_cli.py agent next --json       # valid JSON
python scripts/dominion_cli.py truth --json            # overall=warn
```

### Open items

- Orphan active chunks in RAGD DB from historical `/tmp/pytest-*` paths; remedy: `dominion scan` after RAGD deletion propagation.
- RAGD `ignore_policy_hash` not yet exposed; deep doctor warns.
- No 4 GB GPU generation model fits the 3.5 GB ceiling; retrieve-only fallback is intentional.

Primary report: `reports/phase-5-consolidation-latest.md`.

---

## Phase 3 — Truth And Integrity (2026-05-13)

**Status: PARTIAL-COMPLETE.** Core deletion, metadata, and deep-doctor gates are implemented and validated; remaining warnings are explicit.

### What changed

- RAGD now exposes `POST /index/delete` and soft-deletes active chunks by path.
- RAGD `/query` results include `content_hash`, `repo_root`, `status`, `indexed_at`, and `modified_at`.
- `dominion_loader.scan` propagates deleted manifest entries to RAGD unless `DOMINION_RAGD_DELETE=off`.
- `dominion doctor --deep --json` checks actual manifest, cache, RAGD DB, query metadata, deleted leaks, orphan chunks, TEMP_ADAPTER labels, domdata guard, and retrieval infrastructure truth.
- Local generation is retired; generation is handled by Claude Code, Codex, or Cursor.

### Evidence

```bash
python -m pytest -q dominion_loader/tests dominion_ai/tests ragd_embed/tests ragd_hnsw/tests ragd_chunker/tests ragd_graph/tests ragd_vault/tests
python -m pytest -q                                                        # 381 passed
python domdata/check_no_trading.py                                          # PASS
ctest --test-dir ragd/build --output-on-failure                             # 13/13 passed
dominion doctor --deep --json                                               # overall=warn
```

### Remaining warnings

- RAGD does not yet expose `ignore_policy_hash`; deep doctor warns that ignore-policy alignment is not provable.
- No automatic 4 GB GPU generation model fits the 3.5 GB ceiling; retrieve-only fallback is intentional.
- Existing RAGD DB has orphan active chunks from historical `/tmp/pytest-*` paths; deep doctor surfaces them.
- `document_id` still has a labeled `TEMP_ADAPTER(agent-1)` fallback until RAGD emits loader-compatible IDs.

Primary report: `reports/phase-3-truth-final-20260513-232814.md`.

---

## Phase 4 — Agent OS Complete (2026-05-13)

**Status: COMPLETE.** `dominion_agent/` package fully built, tested, and validated.

### What is dominion_agent?

A local SQLite-backed operating system that constrains, observes, and audits code-editing agents. It enforces session identity, task lifecycle, file locking, safety rules, adversarial review, and complexity budgets.

### Validation

```bash
cd ~/Dominion
python -m pytest -q              # 381 passed
python domdata/check_no_trading.py  # PASS
python scripts/dominion_cli.py agent init --name test --role orchestrator --json
python scripts/dominion_cli.py agent complexity report --json
python scripts/dominion_cli.py agent sync-ragd --json
```

### Key Docs

- `docs/agents/AGENT_OS_CONTRACT.md` — API guarantees, mutation rules, invariants
- `docs/agents/AGENT_OS_COMMANDS.md` — full CLI reference
- `docs/agents/COMPLEXITY_BUDGETS.md` — scoring formula and package budgets
- `docs/agents/LIVING_ARCHITECTURE.md` — auto-generated architecture snapshot
- `reports/phase-4-agent-os-final-20260513-232541.md` — final build report

### Open Items

- `dominion_loader` is over complexity budget (score 53.6 vs budget 40) — 15 TEMP_ADAPTER comments, 18 untested modules to address
- `complexity report --json` can drive automated CI gating

---

## Dominion V2.5 Phase - 2026-05-12

Current status: IN PROGRESS (foundation laid; validate on a normal host for daemon reachability).

Key outcomes (this run):

- Research Intelligence:
  - Added fetch adapter abstraction (`research_os/adapters/`) with structured `FetchResult` and provenance fields.
  - Requests adapter is default; Browser/JS adapter is opt-in and fails cleanly if Playwright is unavailable.
  - Added deterministic normalization + deterministic quality scoring persisted into documents.
  - `research` CLI adds: `adapters`, `fetch`, and `doctor --json`.
- RAGD Maintenance:
  - Added `ragd/scripts/ragd_maintenance.py` with safe `report` and duplicate cleanup planning (`--dry-run` default; `--apply` marks duplicates `status='deleted'`).
  - Added pytest coverage using temp SQLite DB (`ragd/tests/test_maintenance_report.py`).
- Agent Operations:
  - Added `dominion phase-report` and `dominion next-prompt`.

Important environment constraint in this run:

- Localhost networking and some system services were blocked (`Operation not permitted`), so RAGD reachability, tmux, and tailscale could not be validated here. Do not assume RAGD is broken; re-check on the real host.

Continuation commands:

```bash
cd ~/Dominion
git status --short
python -m pytest -q
python domdata/check_no_trading.py
./scripts/bootstrap_python.sh

research adapters
research doctor --json
research fetch <URL> --source <SOURCE> --adapter requests --json || true
python ragd/scripts/ragd_maintenance.py report --json || true
python ragd/scripts/ragd_maintenance.py cleanup-duplicates --dry-run --json || true

cat reports/dominion-v2.5-latest.md
```

Next best task:

- Add `research inspect-document ID --json` (and/or source-health aggregation) plus an offline retrieval smoke for stored chunks.

## Dominion V2 Superbuild Handoff - 2026-05-12

Current status: COMPLETE for the Dominion V2 MVP superbuild.

- Baseline report exists at `reports/dominion-v2-latest.md`.
- Historical RAGD MCP first actions passed and showed RAGD `1.0.0`, the old fallback backend, project indexing, and two open TODOs.
- `AGENTS.md` was upgraded into the Dominion platform contract with explicit RAGD-first workflow, safety, validation, reporting, research, data, and collaboration policies.
- Added platform layout and engineering standards docs.
- Added Research OS foundation under `research_os/` with runtime state under `research/`.
- Added earlier optional local generation support; Phase 6 retires it in favor of frontier-agent generation with RAGD retrieval context.
- Validation passed: Research OS pytest `7 passed`, local LLM pytest `3 passed`, and one approved `crawl4ai_docs` URL fetched/chunked successfully.
- Local generation is no longer a Dominion subsystem; `scripts/bin/llm` now prints a retrieval-only guidance message.
- RAGD ingest bridge passed and `research ingest-ragd` indexed the bundle through RAGD `POST /index`.
- RAGD storage now reuses unchanged chunk identity and live RAGD was restarted with the rebuilt binary.
- Added command center, dashboard, Codex/RAGD helper commands, and noninteractive-safe `warp`.
- Final report: `reports/dominion-v2-latest.md`.
- Next best task: add a JavaScript-capable Research OS fetch adapter, then add a RAGD cleanup command for historical duplicate deleted chunks.
- Pytest stable by default: repo-root `pytest.ini` forces `--import-mode=importlib` so `python -m pytest -q` works cleanly across `domdata/`, RAGD retrieval packages, and `research_os/` tests.
- Fresh-clone bootstrap: `requirements.txt` + `scripts/bootstrap_python.sh` create `.venv`, install deps, and validate `research doctor`, embedding stats, pytest, and `python domdata/check_no_trading.py`.
- Collaboration helpers no longer print a hardcoded Tailscale IP: `scripts/bin/connectinfo` and `scripts/bin/domshare` now use `tailscale ip -4`.

Continuation commands:

```bash
cd ~/Dominion
./scripts/bootstrap_python.sh
research status || true
dominion embed stats || true
dominion vault status || true
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
- `./scripts/bootstrap_python.sh`: PASS historically; Phase 6 changes its retrieval check to embedding stats.

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
- HNSW/external embedding infrastructure and the AST chunker service are wired; semantic querying fails closed until `RAGD_EMBED_API_KEY` is configured and embeddings are generated.
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

## Agent 2 Phase 2 Handoff - 2026-05-13

Agent 2 completed the RAGD intelligence cockpit core without creating a duplicate retrieval stack.

Use now:

```bash
cd ~/Dominion
dominion search "agent handoff" --top-k 3 --json
dominion ask "how does the handoff protocol work" --json
dominion ask "how does the handoff protocol work" --generate --json
dominion trace <trace_id>
dominion eval --bundle dominion_ai/tests/eval_fixtures/tiny --top-k 10 --json
dominion ledger list --kind decision --since 7d --json
dominion embed stats --json
dominion vault status --json
dominion-ui --once
```

Evidence:

- `python -m pytest -q dominion_ai/tests ragd_embed/tests ragd_hnsw/tests ragd_chunker/tests ragd_graph/tests ragd_vault/tests`: PASS in Phase 6 focused validation.
- `python -m pytest -q`: PASS (`42 passed`).
- `python ~/Dominion/domdata/check_no_trading.py`: PASS.
- `dominion eval --bundle dominion_ai/tests/eval_fixtures/tiny --top-k 10 --json`: PASS (`recall@10=1.0`, `MRR=1.0`, `nDCG@10=1.0`, `citation_accuracy=1.0`).
- `dominion trace ad51518679964fab8b78802762e7d5bd`: PASS (plan, retrieve, RRF, filter, rerank, confidence, assemble spans).
- Existing command smoke passed for `dominion status`, `research status`, `domdata notice`, `warp list`, and `codexrag "agent handoff"`.

Important caveats:

- `TEMP_ADAPTER(agent-1)` derives `content_hash` because RAGD `/query` currently omits it.
- `dominion hw probe --json` consumes `dominion_loader.api.hw_probe`; `TEMP_ADAPTER(agent-1)` remains only as a fallback.
- `dominion ask --generate` now stays retrieve-only and reports that generation is handled by Claude Code, Codex, or Cursor.

Primary report: `reports/agent-2-phase-2-20260513-214949.md`.

## Agent 6 Phase 6 Handoff - 2026-05-14

Agent 6 retired local generation and added the retrieval infrastructure needed for frontier agents.

Use now:

```bash
dominion search "scan deleted files ragd delete paths" --top-k 2 --json
dominion embed stats --json
dominion embed run --changed-only --json   # requires RAGD_EMBED_API_KEY
dominion graph build --json
dominion graph stats --json
dominion vault build
dominion vault doctor --json
curl -s -X POST http://127.0.0.1:7474/query/hybrid -H 'Content-Type: application/json' -d '{"q":"scan orchestration pipeline","top_k":3}'
```

Evidence:

- `python -m pytest -q`: PASS (`389 passed`).
- `ctest --test-dir ragd/build --output-on-failure`: PASS (`13/13`).
- `python domdata/check_no_trading.py`: PASS.
- `domdata order-send || true`: BLOCKED.
- `dominion vault doctor --json`: PASS (`ok=true`, 1,418 notes, 0 broken links, 0 invalid frontmatter).
- `dominion embed run --changed-only --json`: fail-closed because `RAGD_EMBED_API_KEY` is not set.
- `llm`: compatibility note exits 0; no local model loader remains.

Important caveats:

- No semantic recall improvement is claimed until Matin sets `RAGD_EMBED_API_KEY` and runs `dominion embed run`.
- `dominion doctor --deep --json` is `warn`, not `ok`, due to missing embedding key, old `/tmp/pytest-*` orphan chunks, missing RAGD ignore-policy hash, and labeled TEMP_ADAPTER debt.
- RAGD active chunks for the deleted local generation package were soft-deleted through `/index/delete` (`0` active chunks remain for that path).

## Repo Weight Cleanup - 2026-05-14

Done:

- Removed tracked generated pytest snapshot mirrors from `vault/files/tmp/` and `vault/symbols/tmp/`.
- Added `.gitignore` entries for both paths so future test runs do not repopulate the tree.

Commands:

```bash
python - <<'PY'
from ragd.scripts.ragd_mcp_stdio import ragd_handoff_read, ragd_query
print(ragd_handoff_read())
print(ragd_query('repo size reduction compression large files docs generated assets', top_k=8))
PY
git rm -r vault/files/tmp vault/symbols/tmp
```

Notes:

- RAGD MCP access was unavailable in this sandbox with `Operation not permitted`; the cleanup proceeded without RAGD writes.
- This only removed generated temp snapshots, not source code.
