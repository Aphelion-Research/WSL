# Dominion Overnight Summary

RUN_ID: `20260511-221153`

## Dominion V2 Superbuild - 2026-05-12

Status: COMPLETE for Dominion V2 MVP superbuild.

- Pytest stabilized: added repo-root `pytest.ini` so `python -m pytest -q` runs all Python tests without `--import-mode=importlib`.
- Added minimal Python bootstrap: `requirements.txt` (only in-repo third-party imports) and `scripts/bootstrap_python.sh` to create `.venv`, install deps, and run the validation set (`research doctor`, `llm doctor`, pytest, `domdata/check_no_trading.py`).
- Removed accidental root junk: deleted empty `ssh` file.
- De-hardcoded Tailscale IP output: `scripts/bin/connectinfo` and `scripts/bin/domshare` now use `tailscale ip -4` instead of printing a fixed IP.

- Baseline captured in `reports/dominion-v2-latest.md`.
- RAGD MCP first actions passed: `ragd_handoff_read`, task-specific `ragd_query`, and `ragd_todo_list`.
- `AGENTS.md` now defines the Dominion platform contract and RAGD-first workflow.
- Added `docs/PLATFORM_LAYOUT.md` and `docs/ENGINEERING_STANDARDS.md`.
- RAGD decisions stored for the RAGD-first workflow and platform layout.
- `dominion` command was missing at baseline and remains a target for the command center phase.
- Added Research OS package, runtime source registry, CLI wrapper, docs, and tests.
- Added optional Ollama-compatible local LLM package, CLI wrapper, docs, and offline-safe tests.
- Research validation passed: `research init`, `research status`, `research list-sources`, `research add-url`, `research run --limit 1`, `research list`, `research doctor`.
- Local LLM validation passed in disabled mode: `llm doctor`, local LLM pytest.
- RAGD research ingest passed and RAGD MCP query can retrieve the new context.
- RAGD unchanged-content reindex idempotency fixed in storage and validated with CMake/ctest.
- Added `dominion`, `dominion-ui`, `codexrag`, `codexstatus`, `codexstart`, `codexprompt`, and `warp` wrappers.
- Final validation passed; see `reports/dominion-v2-latest.md`.

Status: PASS with documented RAGD production-surface limitations.

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
- Native WebSocket/HNSW/tree-sitter/libgit2 deep history: deferred and documented.

## Remaining Risks

- Persistent collector service is not installed yet.
- RAGD systemd user service is written but not enabled because user systemd/sudo flow was not validated.
- RAGD native WebSocket bus is not implemented; REST/MCP bus persistence is working.
- RAGD vector store is TF cosine fallback, not HNSW.
- RAGD chunking is structured regex fallback, not tree-sitter.
- GitHub push may require credentials/token.

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
- bootstrap: PASS (pip showed DNS warnings; continued using installed deps; `llm doctor` reports localhost unreachable as expected).

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
