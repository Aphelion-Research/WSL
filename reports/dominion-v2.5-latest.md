# Dominion V2.5 Report

## Summary

Dominion V2.5 begins with real capability expansion in three pillars:

- Research Intelligence: introduced a fetch adapter abstraction with structured `FetchResult`, added optional browser/JS fetch adapter that fails cleanly when Playwright is unavailable, and added deterministic normalization + quality scoring persisted into document metadata/frontmatter.
- RAGD Maintenance: added non-destructive RAGD maintenance tooling (`ragd/scripts/ragd_maintenance.py`) with schema-aware reporting and safe duplicate cleanup planning (dry-run by default; `--apply` only marks duplicates `status='deleted'`).
- Agent Operations: extended `dominion` CLI with `phase-report` and `next-prompt` to support disciplined future sessions.

This run was executed in a restricted environment where localhost networking, `tmux`, and `tailscale` were blocked (`Operation not permitted`). RAGD daemon reachability could not be validated here; unit tests and offline tooling still pass.

## What Changed

### Research OS (provenance-first pipeline foundation)

- Added `research_os/adapters/` with:
  - `FetchAdapter` protocol + config (`FetchConfig`)
  - `requests` adapter as default (structured failure, bounded timeout, explicit UA)
  - `browser` adapter (Playwright-based) that returns actionable errors if Playwright/browsers are missing
- Upgraded provenance captured in markdown frontmatter and stored document metadata:
  - `final_url`, `adapter`, `content_type`, `fetched_at_utc`, `content_hash`, `normalization`, `quality`
- Added deterministic normalization (`research_os/normalize.py`) and deterministic quality scoring (`research_os/quality.py`)
- Extended `research` CLI:
  - `research adapters`
  - `research fetch URL --source NAME [--adapter requests|browser] [--json]`
  - `research doctor --json`

### RAGD Maintenance (safe tooling)

- Added `ragd/scripts/ragd_maintenance.py`:
  - `report` (schema-aware; counts; duplicate hash groups; top files)
  - `cleanup-duplicates` dry-run plan by default; `--apply` marks duplicates `status='deleted'` (no hard deletes)
- Added pytest coverage with temp SQLite DB (`ragd/tests/test_maintenance_report.py`)

### Agent Operations

- Added `dominion phase-report` and `dominion next-prompt`

## Files Changed

- `research_os/models.py` (FetchResult/provenance model upgrade)
- `research_os/fetcher.py` (approved-source validation kept; moved fetch into adapters)
- `research_os/extractor.py` (frontmatter/provenance fields; normalization metadata)
- `research_os/config.py` + `research_os/db.py` (source adapter preference + safe migration)
- `research_os/scheduler.py` (adapter selection; persisted normalization/quality)
- `research_os/cli.py` (new commands: `adapters`, `fetch`, `doctor --json`)
- `ragd/scripts/ragd_maintenance.py` (maintenance report + cleanup planning/apply)
- `scripts/dominion_cli.py` (agent-ops commands: `phase-report`, `next-prompt`)
- Tests:
  - `research_os/tests/test_adapters.py`
  - `research_os/tests/test_normalize_quality.py`
  - `ragd/tests/test_maintenance_report.py`

## Commands Run

```bash
cd /home/Martin/Dominion
git status --short
cat AGENT_HANDOFF.md
cat PROGRESS.md | tail -n 120
ragd_handoff_read || true
codexrag "Dominion V2.5 research intelligence RAGD maintenance agent operations" || true
research ragd-status || true
dominion status || true

python -m pytest -q
python -m pytest -q research_os/tests
python -m pytest -q ragd/tests/test_maintenance_report.py
python domdata/check_no_trading.py
./scripts/bootstrap_python.sh

python ragd/scripts/ragd_maintenance.py --db /tmp/nonexistent-ragd.db report --json || true
dominion phase-report --phase v2.5 || true
dominion next-prompt --focus "Continue Dominion V2.5: Research adapters + provenance + RAGD maintenance" | head
```

## Tests Passed

- `python -m pytest -q`: PASS (16 passed)
- `python -m pytest -q research_os/tests`: PASS (10 passed)
- `python -m pytest -q ragd/tests/test_maintenance_report.py`: PASS (3 passed)

## Tests Failed / Skipped

- None in this run.

## Safety Status

- `python domdata/check_no_trading.py`: PASS
- No secrets were read or printed.
- No trading execution tokens were added.

## Research OS Status

- Adapter abstraction exists; requests is default; browser adapter is opt-in and fails cleanly if Playwright is unavailable.
- Approved-source enforcement remains host/path strict via `validate_url_for_source`.
- Provenance and quality are deterministic and stored in both markdown frontmatter and DB metadata JSON.

## RAGD Maintenance Status

- Maintenance tooling is safe-by-default and schema-aware.
- Duplicate cleanup is non-destructive by default and only marks duplicates as deleted on `--apply`.

## Agent Operations Status

- `dominion phase-report` and `dominion next-prompt` exist for disciplined next runs.

## Limitations

- This environment blocks localhost networking and some system services (`Operation not permitted`), so:
  - RAGD daemon health checks were unreachable here.
  - `tmux` and `tailscale` commands were not usable here.
  - Playwright adapter cannot be verified end-to-end here (and may not be installed on the host).

## Next Best Task

- Add `research inspect-document ID --json` and/or source-health aggregation (last fetch status, error counts) using existing DB tables.
- Add a safe “retrieval smoke” bundle that does an offline query against stored chunks (no internet, no RAGD required).
- If Playwright is desired, decide on a clean optional dependency story and add `research doctor` adapter checks with actionable install commands.

