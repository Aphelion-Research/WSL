# Dominion Overnight Summary

RUN_ID: `20260511-221153`

## Agent Live-Green Sprint — 2026-05-14

Status: **LIVE_GREEN** — verify_live.sh 14/14 PASS.

What changed this sprint:

- **RAGD**: Started in tmux session `ragd`. 262 stale `/tmp/pytest-*` file paths deleted (278 chunks soft-deleted). Active chunks: 997 → 719.
- **Vault**: Rebuilt (0 broken links). Verified against Python vault doctor.
- **`ragd_vault/repair.py`**: New module to strip stale `/tmp/` wikilinks from SYMBOL_INDEX.md.
- **`ragd_vault/cli.py`**: Added `repair` subcommand (`--dry-run`/`--apply`/`--json`).
- **`scripts/dominion_cli.py`**:
  - Added `_ragd_start_in_tmux()` and `_ragd_diagnose()` helpers.
  - Rewrote `cmd_start` to use helpers with structured diagnostics.
  - Added `--live` and `--strict` flags to `truth` subcommand.
  - `cmd_truth`: RAGD live smoke query, native doctor section, false-positive detection for C++ `.md` extension bug, mode field, strict exit code.
  - `cmd_vault`: Added `repair` passthrough with `--apply`.
- **`scripts/verify_live.sh`**: New 14-check integration script. Outputs: LIVE_GREEN / LIVE_WARN / LIVE_FAIL.

Known remaining warns (not blockers):

- `dominion truth --live overall: WARN` — due to complexity over budget, temp adapters, no embed key. These are pre-existing architectural warns, not regressions.
- Native vault doctor reports 17 broken links (false positives: C++ binary doesn't append `.md` when resolving wikilinks — all targets exist with `.md` extension). Annotated as `known_issue` in truth output.
- `query_chunks` for RAGD smoke shows live results from 719 active chunks.

Validation:

```bash
python -m pytest -q                               # 387 passed, 2 deselected
python domdata/check_no_trading.py                # PASS
bash scripts/verify_live.sh                       # LIVE_GREEN 14/14
python scripts/dominion_cli.py truth --live --json # overall: warn, mode: live, ragd: ok
python scripts/dominion_cli.py vault doctor --json # 0 broken links
```

Reports: `reports/live-green-plan.md`.

## Agent 5 Phase 5 Native Core — 2026-05-14

Status: PARTIAL-COMPLETE / OFFLINE-GREEN. Dominion now has a compiled C++ native core under `ragd/` for policy, path normalization, classification, SHA-256 hashing, deterministic scan planning, SQLite manifest primitives, native doctor checks, native vault integrity, forbidden-token policy fingerprints, Agent OS lock/scope/evidence primitives, and native benchmark output.

What changed:

- Added `dominion_native` C++17 library and native tools: `dominion-native`, `dominion-native-scan`, `dominion-native-manifest`, `dominion-native-doctor`, and `dominion-native-vault-doctor`.
- Hardened `ragd/CMakeLists.txt` with native build options, corrected `URL_HASH` values, OpenSSL SHA-256 support, and multiarch SQLite detection.
- Replaced RAGD `sha256ish()` internals with real SHA-256.
- Added RAGD query metadata fields: `document_id`, `stable_chunk_id`, `relative_path`, `language`, `score_breakdown`, and `source_subsystem`.
- Added `config/forbidden_tokens.json`; Python `domdata_pkg/forbidden_tokens.py` now reads the canonical JSON and exposes a fingerprint.
- Added Python CLI native commands under `python scripts/dominion_cli.py native ...`; `doctor --offline` invokes native doctor when the binary exists.
- Added docs: `docs/NATIVE_CORE.md`, `docs/RAGD_NATIVE_CONTRACT.md`, `docs/DOCTOR_CONTRACT.md`, and `docs/CPP_BUILD.md`.

Validation:

```bash
cmake -S ragd -B ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo  # PASS
cmake --build ragd/build -j$(nproc)                            # PASS
ctest --test-dir ragd/build --output-on-failure                 # 24/24 passed
python -m pytest -q                                             # 387 passed, 2 deselected
python -m pytest -q -m "not integration"                        # 387 passed, 2 deselected
python domdata/check_no_trading.py                              # PASS
domdata notice                                                  # READ-ONLY notice
domdata order-send || true                                      # BLOCKED
domdata doctor                                                  # PASS, account masked
domdata xaurates --count 5                                      # PASS
domdata xauticks --start 2026-05-11T00:00:00Z --count 5          # returned null
domdata xautick                                                 # tick null, IPC send failed
python scripts/dominion_cli.py doctor --offline                 # exit 0, native_doctor overall=warn
ragd/build/dominion-native-doctor --root . --offline --json      # exit 0, overall=warn
ragd/build/dominion-native-doctor --root . --live --json         # exit 1, RAGD unreachable
ragd/build/dominion-native-vault-doctor --root . --json          # warn, 298 broken links
ragd/build/dominion-native bench --root . --json                 # scan_files_per_sec≈1150.7
```

Known blockers / warnings:

- Release-ready: no. Native core is implemented and tested, but vault remains stale and live RAGD is not reachable on `127.0.0.1:7474`.
- Python vault doctor reports 281 broken links; native vault doctor reports 298 broken links, including 278 `/tmp/pytest-*` stale/outside-repo links.
- `domdata xautick` returned `tick: null` with MT5 IPC send failed; historical rates still returned data.
- `python -m domdata ...` is not a supported command form in this checkout; use `domdata ...`.

Reports: `reports/phase-5-native-core-start-latest.md` and `reports/phase-5-native-core-latest.md`.

---

## Dominion V2 Superbuild - 2026-05-12

Status: COMPLETE for Dominion V2 MVP superbuild.

- Pytest stabilized: added repo-root `pytest.ini` so `python -m pytest -q` runs all Python tests without `--import-mode=importlib`.
- Added minimal Python bootstrap: `requirements.txt` (only in-repo third-party imports) and `scripts/bootstrap_python.sh` to create `.venv`, install deps, and run the validation set (`research doctor`, `dominion embed stats`, pytest, `domdata/check_no_trading.py`).
- Removed accidental root junk: deleted empty `ssh` file.
- De-hardcoded Tailscale IP output: `scripts/bin/connectinfo` and `scripts/bin/domshare` now use `tailscale ip -4` instead of printing a fixed IP.

- Baseline captured in `reports/dominion-v2-latest.md`.
- RAGD MCP first actions passed: `ragd_handoff_read`, task-specific `ragd_query`, and `ragd_todo_list`.
- `AGENTS.md` now defines the Dominion platform contract and RAGD-first workflow.
- Added `docs/PLATFORM_LAYOUT.md` and `docs/ENGINEERING_STANDARDS.md`.
- RAGD decisions stored for the RAGD-first workflow and platform layout.
- `dominion` command was missing at baseline and remains a target for the command center phase.
- Added Research OS package, runtime source registry, CLI wrapper, docs, and tests.
- Added an optional local generation package in an earlier phase; Phase 6 retires that path in favor of frontier-agent generation with RAGD retrieval context.
- Research validation passed: `research init`, `research status`, `research list-sources`, `research add-url`, `research run --limit 1`, `research list`, `research doctor`.
- Historical local generation validation passed in disabled mode; Phase 6 replaces it with embedding/vault checks.
- RAGD research ingest passed and RAGD MCP query can retrieve the new context.
- RAGD unchanged-content reindex idempotency fixed in storage and validated with CMake/ctest.
- Added `dominion`, `dominion-ui`, `codexrag`, `codexstatus`, `codexstart`, `codexprompt`, and `warp` wrappers.
- Final validation passed; see `reports/dominion-v2-latest.md`.

Status: PASS with documented RAGD production-surface limitations.

## Phase 3 — Truth And Integrity (2026-05-13)

RAGD deletion, query metadata, loader delete propagation, deep doctor, ignore-policy hash export, and LLM registry truth are implemented.

| Item | Status |
|---|---|
| RAGD `/index/delete` | PASS |
| Deleted sentinel retrieval after delete | PASS |
| RAGD query metadata | PASS |
| Loader delete propagation tests | PASS |
| Deep doctor | PASS with warnings |
| LLM 4 GB truth | PASS; retrieve-only fallback explicit |
| Ignore policy | PARTIAL; Python hash exported, RAGD hash unavailable |
| Full pytest | PASS (`381 passed`) |
| Trading guard | PASS |

Remaining warnings: RAGD ignore policy hash unavailable, historical orphan active chunks in RAGD DB, labeled `document_id` adapter.

## Phase 5 — Consolidation + Cockpit (2026-05-14)

`dominion agent dashboard`, `dominion agent next`, `dominion truth`, CLI thinning, e2e smoke tests, complexity fixes.

| Item | Status |
|---|---|
| `agent dashboard` command | PASS |
| `agent next` command | PASS |
| `dominion truth` command | PASS |
| `dominion_loader/cli.py` (delegate module) | PASS |
| `dominion_cli.py` thinned (1003→784 lines) | PASS |
| `dominion_agent/dashboard.py` | PASS |
| `test_e2e_smoke.py` (6 tests) | PASS |
| TEMP_ADAPTER false-positive fix | PASS |
| Complexity budget recalibration | PASS |
| Full test suite | PASS (`387 passed`) |
| `check_no_trading.py` | PASS |

---

## Audit + Stabilization — 2026-05-14

Two-cycle external audit fixed all critical/high/medium correctness and validation issues.

| Item | Status |
|---|---|
| `acquire_lock()` BEGIN IMMEDIATE (race fix) | PASS |
| `dangerous` flag bypass (`not payload.get`) | PASS |
| Dangerous term scan covers `title` + `description` | PASS |
| Field-specific dangerous-term error messages | PASS |
| `end_session()` accepts `idle` status | PASS |
| `abandon_session()` rowcount check | PASS |
| `_has_pytest_evidence` wired in adversary | PASS |
| Adversary score: continuous penalty formula | PASS |
| Canonical `domdata_pkg/forbidden_tokens.py` | PASS |
| `adversary.py` imports from canonical token file | PASS |
| `doctor --offline` skips platform checks | PASS |
| `doctor --offline` exit code consistent (0) | PASS |
| CLI `ROOT` inferred from script location | PASS |
| Integration tests gated by default (`-m "not integration"`) | PASS |
| `test_unreadable_directory` skips on root/WSL | PASS |
| `test_doctor_runs_without_crash` uses `--offline` | PASS |
| CMake `URL_HASH` pinned for nlohmann_json + cpp-httplib | PASS |
| CMake SQLite: multiarch discovery via pkg-config | PASS |
| Complexity score: test credit capped (cannot erase debt) | PASS |
| TEMP_ADAPTER(agent-1) debt cleared in `ragd_client.py` | PASS |
| `complexity.py` `add_parser` dedup hack removed | PASS |
| `WINE_WSL_DRIVE` env var in `collector.py` | PASS |
| pytest markers: `requires_hnsw`, `requires_treesitter` | PASS |
| Full test suite | PASS (`387 passed, 2 deselected`) |
| `check_no_trading.py` | PASS |
| `doctor --offline` | PASS (exit 0) |

Vault has 281 broken links from stale committed notes — rebuild with `dominion vault rebuild` after RAGD is stable.  
`dominion_agent` complexity is over budget (430.2/350.0) — technical debt, not a blocker.

---

## Audit + Stabilization — 2026-05-14

Two-cycle external audit fixed all critical/high/medium correctness and validation issues.

| Item | Status |
|---|---|
| `acquire_lock()` BEGIN IMMEDIATE (race fix) | PASS |
| `dangerous` flag bypass (`not payload.get`) | PASS |
| Dangerous term scan covers `title` + `description` | PASS |
| Field-specific dangerous-term error messages | PASS |
| `end_session()` accepts `idle` status | PASS |
| `abandon_session()` rowcount check | PASS |
| `_has_pytest_evidence` wired in adversary | PASS |
| Adversary score: continuous penalty formula | PASS |
| Canonical `domdata_pkg/forbidden_tokens.py` | PASS |
| `adversary.py` imports from canonical token file | PASS |
| `doctor --offline` skips platform checks | PASS |
| `doctor --offline` exit code consistent (0) | PASS |
| CLI `ROOT` inferred from script location | PASS |
| Integration tests gated by default (`-m "not integration"`) | PASS |
| `test_unreadable_directory` skips on root/WSL | PASS |
| `test_doctor_runs_without_crash` uses `--offline` | PASS |
| CMake `URL_HASH` pinned for nlohmann_json + cpp-httplib | PASS |
| CMake SQLite: multiarch discovery via pkg-config | PASS |
| Complexity score: test credit capped (cannot erase debt) | PASS |
| TEMP_ADAPTER(agent-1) debt cleared in `ragd_client.py` | PASS |
| `complexity.py` `add_parser` dedup hack removed | PASS |
| `WINE_WSL_DRIVE` env var in `collector.py` | PASS |
| pytest markers: `requires_hnsw`, `requires_treesitter` | PASS |
| Full test suite | PASS (`387 passed, 2 deselected`) |
| `check_no_trading.py` | PASS |
| `doctor --offline` | PASS (exit 0) |

Vault has 281 broken links from stale committed notes — rebuild with `dominion vault rebuild` after RAGD is stable.  
`dominion_agent` complexity is over budget (430.2/350.0) — technical debt, not a blocker.

---

## Phase 4 — Agent OS (2026-05-13)

`dominion_agent/` package complete and validated.

| Item | Status |
|---|---|
| 20 source modules | PASS |
| 10 test files (103 tests) | PASS |
| CLI (`dominion agent ...`) wired | PASS |
| TUI panels wired | PASS |
| Full test suite (381 tests) | PASS |
| `check_no_trading.py` | PASS |
| Docs (`docs/agents/`) | PASS |
| Final report | `reports/phase-4-agent-os-final-20260513-232541.md` |

---

## Executive Summary

Dominion shell, helpers, domdata, collector, Parquet/DuckDB normalization, health dashboard, collaboration docs, Codex prompts, and an expanded/tested RAGD C++ daemon are in place. No secrets were read or printed. Trading remains blocked.

## PASS/FAIL Table

| Phase | Status | Notes |
|---|---:|---|
| 0 Baseline audit | PASS | MT5, SSH, Tailscale, tmux, toolchains validated. |
| 1 Git baseline | PASS | Local baseline commit created; GitHub push deferred to final safe state/credentials. |
| 2 Shell foundation | PASS | No auto-tmux; `.bashrc` sources `.dominionrc` once. |
| 3 Global helpers | PASS | mt5/domshare/connectinfo/Codex helpers installed. |
| 4 domdata | PASS | Compile/tests/scanner/MT5 reads pass. |
| 5 Collector | PASS | Raw tick/bar/health JSONL written. |
| 6 Parquet/DuckDB | PASS | Parquet and DuckDB summary work. |
| 7 Health dashboard | PASS | `dominion-health` text and JSON work. |
| 8 Docs | PASS | README, quickstart, runbooks, setup docs, prompts created. |
| 9-21 RAGD daemon | PASS/PARTIAL | Expanded storage/API/MCP/indexer/watcher/tests pass; native WebSocket/HNSW/tree-sitter/libgit2 remain documented gaps. |
| 22 Final gauntlet | PASS | Noninteractive sudo unavailable; non-sudo service fallback worked. |

## Files Changed

- ` M .gitignore`
- ` M PROGRESS.md`
- ` M domdata/domdata_pkg/cli.py`
- ` M domdata/domdata_pkg/convert.py`
- ` M reports/overnight-report-20260511-221153.md`
- ` M scripts/bin/connectinfo`
- ` M scripts/bin/mt5start`
- `?? .claude/`
- `?? .cursor/`
- `?? AGENTS.md`
- `?? QUICKSTART.md`
- `?? README.md`
- `?? docs/`
- `?? prompts/`
- `?? ragd/`
- `?? scripts/bin/domdata`
- `?? scripts/bin/dominion-health`
- `?? scripts/dominion_health.py`

## Backups Created

- `backups/20260511-221153`

## Commands Run

Baseline audit, git init/config/commit, shell validation, helper validation, domdata py_compile/pytest/scanner, MT5 read commands, collector, convert-xau, duckdb-init, duckdb-summary, dominion-health, CMake build, ctest, RAGD HTTP/MCP smoke, docs/prompts listing, git status/diff.

## Tests Passed

- domdata pytest: 6 passed.
- domdata forbidden-token scanner: PASS.
- MT5 account/select/tick/rates/ticks: PASS.
- collector bounded run: PASS.
- Parquet/DuckDB summary: PASS.
- dominion-health: PASS.
- RAGD ctest: 13/13 passed.
- RAGD HTTP/MCP/CLI/agent-init smoke: PASS.

## Tests Failed And Why

- Initial DuckDB summary failed due missing `pytz`; fixed by integer minute buckets.
- Initial RAGD configure failed due absent sqlite3 dev symlink; fixed by linking installed runtime library directly.
- Initial MCP test failed on JSON id typing; fixed.
- `sudo -n service ssh status` failed because noninteractive sudo needs a password; non-sudo `service ssh status` passed.

## Security Status

- Secrets not printed: PASS.
- Secrets permissions: `secrets/` 700, `secrets/mt5.env` 600.
- domdata read-only status: PASS.
- Blocked trading commands: `domdata order-send` prints BLOCKED and exits nonzero.

## Data Status

- account-info works: PASS.
- xautick works: PASS.
- xaurates works: PASS.
- xauticks works: PASS.
- collector wrote files: PASS.
- DuckDB/parquet status: PASS.

## Collaboration Status

- SSH active: PASS.
- Tailscale IP: dynamic via `tailscale ip -4` (see `connectinfo`).
- tmux sessions: `matin`, `dan`, `dominion`.
- Dan command: `ssh Martin@<tailscale-ip>`; VS Code: `code --remote ssh-remote+dominion /home/Martin/Dominion`.

## Codex Workflow Status

`AGENTS.md`, prompt library, `CODEX_WORKFLOW.md`, and `codexmatin/codexdan/codexsend/codexls/codexkill/codexnew` helpers exist.

## RAGD Status

- Project structure created: PASS.
- Builds: PASS.
- Tests: 13/13 PASS after RAGD upgrade.
- HTTP health: PASS.
- MCP: PASS.
- Indexing: PASS.
- Retrieval: PASS.
- TODO engine: PASS.
- Agent memory: PASS.
- Inotify watcher: PASS.
- Intent router: PASS.
- REST bus persistence/locks: PASS.
- Temporal chunk-history surfaces: PASS.
- Dead-zone heuristic report: PASS.
- Native WebSocket/libgit2 deep history: deferred and documented.

## Remaining Risks

- Persistent collector service is not installed yet.
- RAGD systemd user service is written but not enabled because user systemd/sudo flow was not validated.
- RAGD native WebSocket bus is not implemented; REST/MCP bus persistence is working.
- Semantic HNSW query requires `RAGD_EMBED_API_KEY` and an embedding run before it can return results.
- RAGD chunking uses the AST service when it is running and falls back for unsupported languages.
- GitHub push may require credentials/token.

## Dominion V2.5 Phase Start - 2026-05-12

Goal: begin capability expansion into “research intelligence OS” with provenance, maintenance, and agent operations.

Completed (this run):

- Research OS:
  - Added adapter abstraction and structured `FetchResult` with provenance fields.
  - Added optional browser fetch adapter that fails cleanly if Playwright is unavailable.
  - Added deterministic normalization and deterministic quality scoring (persisted in document metadata/frontmatter).
  - CLI: `research adapters`, `research fetch`, `research doctor --json`.
- RAGD maintenance:
  - Added `ragd/scripts/ragd_maintenance.py` with `report` and safe `cleanup-duplicates` dry-run plan (`--apply` marks duplicates deleted).
  - Added pytest coverage with temp SQLite DB.
- Agent operations:
  - Added `dominion phase-report` and `dominion next-prompt`.

Validation (run 2026-05-12):

- `python -m pytest -q`: PASS (16 passed)
- `python -m pytest -q research_os/tests`: PASS (10 passed)
- `python -m pytest -q ragd/tests/test_maintenance_report.py`: PASS (3 passed)
- `python domdata/check_no_trading.py`: PASS
- `./scripts/bootstrap_python.sh`: PASS (pip network DNS unavailable; proceeded with installed deps)

Known constraint (this run):

- Localhost networking and system services were blocked (`Operation not permitted`), so RAGD daemon reachability checks could not be validated here.

## Exact Next Commands For Matin

```bash
cd ~/Dominion
mt5start
domshare status
dominion-health
domdata collect-status
matin
```

## Exact Next Commands For Dan

```cmd
tailscale status
tailscale ip -4
tailscale ping <tailscale-ip>
ssh Martin@<tailscale-ip>
```

Inside SSH:

```bash
tmux attach -t dan
```

VS Code:

```cmd
code --remote ssh-remote+dominion /home/Martin/Dominion
```

## Next Codex Session

```bash
cd ~/Dominion
cat AGENT_HANDOFF.md
cat ragd/AGENT_HANDOFF.md
git status --short
```

## Dominion V2 Cleanup - 2026-05-12

Goal: make collaboration + scripts portable after GitHub push (remove hardcoded Tailscale IPs, portable `DOMINION_ROOT`, bootstrap robustness, repo hygiene).

Changes:

- Removed all hardcoded Tailscale IPs from `docs/`, `reports/`, and setup notes; replaced with `<tailscale-ip>` + `tailscale ip -4` (Matin can use `connectinfo` inside WSL/Dominion).
- `scripts/dominion_cli.py`: `DOMINION_ROOT` (default `~/Dominion`) and `RAGD_URL` (default `http://127.0.0.1:7474`).
- `scripts/dominion_health.py`: `DOMINION_ROOT` (default `~/Dominion`).
- `scripts/bootstrap_python.sh`: detects missing venv support and prints exact fix `sudo apt update && sudo apt install -y python3-venv`.
- `.gitignore`: added common caches/build/db artifacts (`.ruff_cache/`, `.coverage`, `htmlcov/`, `dist/`, `build/`, `*.sqlite*`, `*.db*`, `*.egg-info/`).

Validation (run 2026-05-12):

```bash
cd ~/Dominion
git status --short
grep -RInE '100\\.[0-9]{1,3}\\.[0-9]{1,3}\\.[0-9]{1,3}|ssh Martin@100\\.' README.md QUICKSTART.md PROGRESS.md AGENT_HANDOFF.md docs reports scripts 2>/dev/null
python -m pytest -q
python domdata/check_no_trading.py
./scripts/bootstrap_python.sh
```

Results:

- IP scan: PASS (no matches).
- Pytest: PASS (16 passed).
- domdata forbidden-token scan: PASS.
- bootstrap: PASS (pip showed DNS warnings; continued using installed deps; embedding stats are offline-safe).

## Dominion V2 Final Polish - 2026-05-12

Goal: tiny correctness pass (Dan Windows CMD docs, `DOMINION_SSH_HOST` placeholder removal, `RAGD_URL` start clarity).

Validation (run 2026-05-12):

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

Results:

- Hardcoded IP scan: PASS (no matches).
- `connectinfo` scan: PASS (no Windows CMD instructions tell Dan to run it).
- Placeholder scan: PASS.
- Pytest: PASS.
- domdata forbidden-token scan: PASS.
- bootstrap: PASS.

## Agent 2 Phase 2 RAGD Intelligence - 2026-05-13

Goal: complete fewer gates fully for the retrieval cockpit and RAGD-first developer workflow.

Completed:

- Added `dominion_ai/` with RAGD REST client, query planner, BM25/vector RRF composition, heuristic rerank, confidence scoring, budgeted context assembly, trace explorer, eval harness, ledger query layer, lightweight bench runner, and CLI handlers.
- Added additive commands: `dominion ask`, `dominion search`, `dominion explain`, `dominion trace`, `dominion eval`, `dominion ledger`, `dominion graph`, `dominion bench`, and `dominion hw probe`.
- Retired the local generation package; RAGD now focuses on retrieval infrastructure for frontier agents.
- Extended `dominion-ui --once` with Latest queries and Latest decisions panels.
- Wrote Agent 2 docs under `docs/agents/` and final report `reports/agent-2-phase-2-20260513-214949.md`.

Evidence captured:

```bash
python -m pytest -q dominion_ai/tests ragd_embed/tests ragd_hnsw/tests ragd_chunker/tests ragd_graph/tests ragd_vault/tests
python -m pytest -q
dominion search "agent handoff" --top-k 3 --json
dominion ask "how does the handoff protocol work" --json
dominion ask "how does the handoff protocol work" --generate --json
dominion trace ad51518679964fab8b78802762e7d5bd
dominion eval --bundle dominion_ai/tests/eval_fixtures/tiny --top-k 10 --json
dominion ledger list --kind decision --since 7d --json
dominion embed stats --json
dominion vault status --json
dominion-ui --once
```

Results:

- Focused pytest: PASS (`26 passed`).
- Full configured pytest: PASS (`42 passed`).
- Trading guard: PASS (`python ~/Dominion/domdata/check_no_trading.py`).
- Tiny eval: PASS (`recall@10=1.0`, `MRR=1.0`, `nDCG@10=1.0`, `citation_accuracy=1.0`).
- Generation: retired from Dominion; `--generate` now returns retrieve-only context and tells the caller that Claude Code, Codex, or Cursor handles generation.
- Existing smoke: PASS for `dominion status`, `research status`, `domdata notice`, `warp list`, and `codexrag "agent handoff"`.

Deferred honestly:

- Full Agent 1 benchmark harness registration is not implemented; `dominion bench` is a lightweight local suite.
- RAGD `/query` does not expose `content_hash`; Agent 2 uses `TEMP_ADAPTER(agent-1)` until Agent 1 adds the field.
- Agent 2 consumes `dominion_loader.api.hw_probe` for `dominion hw probe --json`; a `TEMP_ADAPTER(agent-1)` fallback remains for older checkouts.

## Agent 6 Phase 6 RAG Intelligence Overhaul - 2026-05-14

Status: PARTIAL-COMPLETE. The local generation subsystem is removed, RAGD no longer rebuilds a per-query vector corpus, retrieval metadata/AST/vault infrastructure is wired and tested, and semantic embedding runs fail closed until an explicit external API key is configured.

Completed:

- Deleted the retired local generation package and removed Python imports from `scripts/`, `dominion_ai/`, `dominion_agent/`, `dominion_loader/`, and `research_os/`.
- Added `ragd_embed/`, `ragd_hnsw/`, `ragd_chunker/`, `ragd_graph/`, and `ragd_vault/` with tests.
- Updated RAGD C++ storage/query results with AST metadata fields and removed the old per-query vector rebuild from `RagEngine`.
- Added `/query/semantic` proxy and `/query/hybrid`; semantic service returns a clear error when `RAGD_EMBED_API_KEY` is missing.
- Built the Obsidian vault at `vault/` from the live RAGD index: 1,418 notes, 0 broken links, 0 invalid frontmatter.
- Rebuilt graph stats: 1,025 nodes, 1,174 edges (`defines`, `imports`, `calls`).

Evidence:

```bash
python -m pytest -q                                      # 389 passed
cmake --build ragd/build -j$(nproc)                      # PASS
ctest --test-dir ragd/build --output-on-failure           # 13/13 passed
python domdata/check_no_trading.py                        # PASS
domdata notice                                            # READ-ONLY
domdata order-send || true                                # BLOCKED
dominion embed run --changed-only --json                  # fails closed without RAGD_EMBED_API_KEY
dominion vault doctor --json                              # ok=true, broken_links=0, invalid_frontmatter=0
dominion graph stats --json                               # nodes=1055, edges=1215
dominion doctor --deep --json                             # overall=warn; no fail
llm                                                       # compatibility note exits 0
```

Known warnings:

- `RAGD_EMBED_API_KEY` is not set, so no external embeddings were generated and no semantic recall lift is claimed.
- `dominion doctor --deep` warns on old orphan chunks under `/tmp/pytest-*`, missing RAGD ignore policy hash, and labeled TEMP_ADAPTER debt.
- `hnswlib` and `tree_sitter` are listed in requirements but not installed in the current venv; code has tested fallbacks and the final report records this honestly.

Report: see `reports/agent-6-phase-6-*.md` and validation log `reports/agent-6-validation-20260514-031442.log`.

## Repo Weight Cleanup - 2026-05-14

Status: COMPLETE. Removed tracked generated pytest snapshot mirrors under `vault/files/tmp/` and `vault/symbols/tmp/` and added ignore rules so they do not re-enter the tree.

Evidence:

```bash
python - <<'PY'
from ragd.scripts.ragd_mcp_stdio import ragd_handoff_read, ragd_query
print(ragd_handoff_read())
print(ragd_query('repo size reduction compression large files docs generated assets', top_k=8))
PY
git rm -r vault/files/tmp vault/symbols/tmp
```

Notes:

- `ragd_handoff_read` and `ragd_query` failed closed with `Operation not permitted` against `http://127.0.0.1:7474/mcp`; no RAGD writes were performed.
- The repo now ignores future `vault/files/tmp/` and `vault/symbols/tmp/` snapshots.
