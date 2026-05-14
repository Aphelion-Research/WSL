# Dominion Truth Contract

Version: `agent-3.20260513`

## Deletion Truth

- RAGD deletion is soft delete only: active chunks are marked `status='deleted'`; rows are never hard-deleted.
- `POST /index/delete` accepts `path` or `paths` and returns submitted paths, files marked deleted, chunks marked deleted, and per-path errors.
- RAGD query paths must filter `status='active'` for BM25, keyword, vector, and hybrid results.
- Loader scans propagate deleted manifest paths to RAGD unless `DOMINION_RAGD_DELETE=off`.
- Rollback: set `DOMINION_RAGD_DELETE=off`; deep doctor reports propagation risk.

## Query Metadata Truth

- RAGD `/query` results must include `chunk_id`, `filepath`, `content_hash`, `repo_root`, `status`, `indexed_at`, and `modified_at`.
- Existing fields are additive-only; no legacy JSON keys are renamed.
- `dominion_ai` consumes producer `content_hash`, `repo_root`, `status`, and timestamps when present.
- `document_id` remains a labeled compatibility adapter until RAGD exposes loader-compatible document IDs.

## Doctor Truth

- `dominion doctor` remains shallow and compatible.
- `dominion doctor --deep --json` inspects actual state and returns `pass`, `warn`, `fail`, or `skip` per check.
- Unreachable dependencies are never reported as pass; they are `fail` when required or `skip` under `--offline`.
- Deep doctor checks RAGD reachability, query metadata, manifest readability, deleted chunk leaks, active manifest chunk coverage, cache integrity, ignore policy alignment, domdata guard, LLM governor truth, TEMP_ADAPTER labels, duplicate active chunks, and orphan active chunks.

## Cache Truth

- Cache entries remain fingerprint-checked by the loader cache.
- Deep doctor runs actual cache verification and reports corrupt or quarantined entries.
- Corrupt entries are ignored or quarantined, not silently served.

## Ignore Policy Truth

- Python loader exports `export_policy()` and `policy_hash()`.
- `dominion ignore policy --json` emits the policy and hash.
- `config/dominion_ignore_policy.json` records the generated policy snapshot.
- RAGD does not yet consume or expose the policy hash; deep doctor warns instead of passing alignment.

## Model Safety Truth

- A model profile with `safe` in the name must never exceed the 3.5 GB VRAM safety ceiling.
- 4 GB class GPUs default to explicit retrieve-only when no automatic safe generation model exists.
- Risky 4 GB profiles must be manual-only via `DOMINION_GOVERNOR=manual` and `DOMINION_LLM_MODEL`.

## Evidence Rules

- A completion claim needs a changed file, command output, and pass/fail status.
- Warnings and skips must include a reason and remedy.
- Reports must distinguish tested code behavior from live daemon behavior.
