# Live-Green Integration Sprint — 2026-05-14

**Final Status: LIVE_GREEN — 14/14 checks pass**

```
bash scripts/verify_live.sh  →  LIVE_GREEN  14/14 PASS
```

## What Was Done

### Phase 1 — Assessment
- RAGD was not running. 281 broken vault links. `truth --offline` reported vault broken.
- Created `reports/live-green-plan.md` with full state inventory.

### Phase 2 — RAGD Cleanup
- Started RAGD in tmux session `ragd` at `127.0.0.1:7474`.
- Deleted 262 stale `/tmp/pytest-*` file paths via `POST /index/delete` (278 chunks soft-deleted).
- Active chunks: 997 → 719. RAGD health: ok.

### Phase 3 — Vault Repair
- Rebuilt vault via `dominion vault build`: 154 files, 719 symbols.
- Python vault doctor: **0 broken links** (was 281).
- Created `ragd_vault/repair.py`: strips stale `/tmp/` wikilinks from SYMBOL_INDEX.md.
- Added `vault repair` subcommand to `ragd_vault/cli.py` and `scripts/dominion_cli.py`.

### Phase 4 — CLI Enhancements
- `scripts/dominion_cli.py`:
  - `_ragd_start_in_tmux()`: polls RAGD health up to 8s after tmux start, returns structured dict.
  - `_ragd_diagnose()`: categorizes RAGD failures (binary_missing / process_not_running / unhealthy / healthy).
  - `cmd_start`: rewritten with helpers, `--json` flag, structured diagnostics on failure.
  - `truth --live`: requires live RAGD, runs smoke query, includes native doctor, annotates false positives.
  - `truth --strict`: exits 1 on warn (useful for CI).
  - `cmd_truth` now has `mode: live|offline` in JSON output and shows `[LIVE]`/`[OFFLINE]` in human output.
  - `vault repair`: passthrough with `--apply` support.

### Phase 5 — Native Doctor Integration
- Native doctor C++ binary (`ragd/build/dominion-native-doctor`) now called from `truth --live`.
- False-positive detection: native vault doctor has a known bug (doesn't append `.md` on wikilink resolution). All 17 "broken" links confirmed to have `.md` targets. Annotated as `known_issue` in output.

### Phase 6 — Verification Script
- Created `scripts/verify_live.sh` with 14 checks:
  - Build presence (4): ragd, native-doctor, native-scan, native-vault-doctor
  - RAGD health (2): health endpoint, query smoke
  - Native doctor (1): live mode (warn accepted, known bug)
  - Python truth (1): `truth --live --json`
  - Vault doctor (1): 0 broken links
  - domdata safety (3): notice, order-send blocked, domdata doctor
  - Agent OS (1): imports smoke
  - Safety scanner (1): no-trading-tokens

## Test Results

```
python -m pytest -q          → 387 passed, 2 deselected
python domdata/check_no_trading.py → PASS
bash scripts/verify_live.sh  → LIVE_GREEN 14/14
```

## Known Remaining Warns (Non-Blockers)

| Warn | Details | Priority |
|------|---------|---------|
| complexity over budget | dominion_agent (471/350), scripts (404/200), domdata (209/155), research_os (196/175), dominion_loader (83/50) | Medium |
| temp_adapters | doctor shows `temp_adapters: warn` | Low |
| native vault doctor `.md` bug | false positives; all targets exist | Low (fix in C++) |
| no embed key | `rag_infra` warns without embed API key | External |

## Files Changed

- `scripts/dominion_cli.py` — cmd_start, cmd_truth, cmd_vault, helpers
- `scripts/verify_live.sh` — NEW: 14-check live-green script
- `ragd_vault/repair.py` — NEW: stale wikilink stripper
- `ragd_vault/cli.py` — repair subcommand
- `PROGRESS.md` — sprint summary added
- `AGENT_HANDOFF.md` — updated with live-green status and next tasks
- `reports/live-green-plan.md` — plan (existing)
- `reports/live-green-integration-latest.md` — this file

## Next Best Tasks

1. Fix complexity over budget (biggest wins: refactor `dominion_agent` scheduler, split `scripts/dominion_cli.py`)
2. Fix C++ native vault doctor `.md` extension bug in `ragd/src/native/vault_doctor.cpp`
3. Wire native scan → RAGD live ingestion pipeline
4. Remove temp adapters (find via `doctor --offline --json | jq .sections.doctor.checks.temp_adapters`)
5. Agent OS lock consolidation audit
