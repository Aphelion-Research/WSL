# Live-Green Integration Plan — 2026-05-14

## Observed State

### RAGD
- Binary: `ragd/build/ragd` — EXISTS
- Process: NOT RUNNING at plan-write time; started in tmux `ragd` session
- Health after start: `{"ok":true,"active_chunks":997,"chunks":1598}`
- Stale chunks: 262 unique `/tmp/pytest-*` paths still `active` in SQLite
- These cause `orphan_active_chunks` warn in doctor

### Vault
- Total notes: 874
- Broken links: 281 (all in `_index/SYMBOL_INDEX.md`)
  - 278 point to `symbols/tmp/pytest-of-Martin/pytest-XX/...` (missing on disk)
  - 3 point to `symbols/research/extracted|markdown/...` (missing exact hash match)
- Root cause: vault was built when RAGD had stale tmp chunks indexed
- Fix: delete tmp chunks from RAGD, rebuild vault

### Truth / Doctor
- `dominion truth --offline --json` → overall: warn
- Warn sections: complexity (over-budget pkgs), doctor (orphan chunks, no embed key, temp adapters), ragd (not reachable), rag_infra (no embed key)
- No `--live` or `--strict` flags on `truth`
- `dominion native doctor --offline` → overall: warn (only vault 298 broken links)
- `dominion doctor --offline` → overall: ok (no live checks)

### Native Manifest
- Native scan plan: 1277 included files, plan_hash stable
- Native manifest DB: exists at `~/.dominion/native_manifest.db`, 0 active files
- Not integrated into loader ingestion pipeline — split brain exists
- Native scan binary: `ragd/build/dominion-native-scan` exists

### Agent OS / Locks
- Python: `dominion_agent/locks.py` — SQLite-based, BEGIN IMMEDIATE fixed
- Native: `ragd/src/native/agent_locks.cpp` — exists in C++ side
- Alignment: needs audit

### `dominion start`
- Works via tmux (good)
- No graceful fallback if tmux unavailable
- No health poll after RAGD start
- No detailed failure diagnosis

---

## Exact Blockers (live-green)

| Blocker | Root Cause | Fix |
|---|---|---|
| `native_vault: warn` (298 broken links) | SYMBOL_INDEX has stale tmp entries | Delete tmp RAGD chunks + rebuild vault |
| `orphan_active_chunks: warn` | 262 active RAGD chunks for `/tmp/` paths | POST `/index/delete` for all tmp paths |
| `ragd: warn` (unreachable) | RAGD not started | `dominion start` now works; needs auto-wait |
| `truth` has no `--live` flag | Not implemented | Add `--live` and `--strict` |
| `vault repair` missing | Not implemented | Add repair command |
| No `verify_live.sh` | Not implemented | Create script |

---

## Files Likely to Change

- `scripts/dominion_cli.py` — `cmd_start`, `cmd_truth`, `cmd_vault`, native doctor
- `ragd_vault/cli.py` — add `repair` subcommand  
- `ragd_vault/repair.py` — NEW: vault repair logic
- `dominion_loader/ragd_bridge.py` — cleanup / delete helpers
- `scripts/verify_live.sh` — NEW: live verification script
- `ragd/src/native/doctor.cpp` — deeper checks
- `AGENT_HANDOFF.md`, `PROGRESS.md` — docs
- `reports/live-green-integration-latest.md` — NEW: final report

---

## Validation Commands

```bash
# After each phase:
python -m pytest -q
python domdata/check_no_trading.py

# Phase 1 (RAGD live):
curl -s http://127.0.0.1:7474/health
python scripts/dominion_cli.py status --json

# Phase 3 (vault clean):
python scripts/dominion_cli.py vault doctor --json
python scripts/dominion_cli.py native doctor --offline --json

# Phase 4 (truth live):
python scripts/dominion_cli.py truth --live --json
python scripts/dominion_cli.py truth --strict --json; echo $?

# Phase 7 (verify):
./scripts/verify_live.sh
```

---

## Rollback Notes

- RAGD SQLite: no RAGD chunk deletions touch real source files. All deletes are soft-deletes (status='deleted'). Safe to retry.
- Vault rebuild: `vault/` dir is fully generated. Rebuilding replaces all auto-generated content. Hand-written docs are NOT in vault/ (they live in docs/). Safe.
- `scripts/dominion_cli.py`: tested after every change with `python -m pytest`.
- Native code: C++ changes require `cmake --build ragd/build -j$(nproc)`. Rebuild before testing.

---

## Phase Order

1. **RAGD chunk cleanup** (remove 262 tmp active chunks)
2. **Vault rebuild** (fix 281 broken links → 0)
3. **Vault repair command** (add `vault repair` to CLI)
4. **Start/Status improvements** (health poll, better RAGD diagnosis)
5. **Truth --live --strict** (flags + exit codes)
6. **Native doctor deepening** (extend C++ checks)
7. **verify_live.sh** (single truth script)
8. **Documentation + final report**
