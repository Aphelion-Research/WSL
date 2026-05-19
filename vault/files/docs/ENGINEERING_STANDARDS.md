---
synced: 2026-05-19 19:42
---
# Dominion V2 Engineering Standards

These standards keep Dominion operable as it grows from one workstation to a team-managed local platform.

## CLI Conventions

- Commands use short stable names: `dominion`, `research`, `llm`, `codexrag`, and `dominion-ui`.
- Commands should support human-readable output by default.
- Machine-readable output should be available with `--json` when practical.
- Failures should include the failing component and an actionable next step.
- Long-running commands must accept an explicit limit, interval, or quit path.

## Configuration Conventions

- Default paths are rooted at `/home/Martin/Dominion`.
- Runtime state belongs under the package runtime directory, not hidden in random locations.
- Environment overrides are allowed for host/model/service addresses.
- Secrets are loaded only by the component that needs them and are never printed.

## Test Conventions

- Package tests live under `PACKAGE/tests/`.
- Tests for offline adapters must pass without network services.
- Crawler tests must not depend on live internet.
- RAGD C++ changes require CMake build and `ctest`.
- domdata changes require the forbidden-token scanner.

## Documentation Conventions

- Every subsystem needs a daily-use doc and a troubleshooting path.
- Reports must say what passed, what failed, and what was not tested.
- Stubs and partial implementations must be labeled as such.
- Include exact continuation commands in handoff docs.

## Health And Doctor Conventions

- `status` commands summarize current state quickly.
- `doctor` commands perform deeper checks and explain fixes.
- Health checks must not expose secrets or trigger trading behavior.
- Missing optional dependencies should degrade cleanly.

## Report Conventions

- Current report: `reports/dominion-v2-latest.md`.
- Timestamped report: `reports/dominion-v2-YYYYMMDD-HHMMSS.md`.
- Include baseline, changed files, tests, failures, risks, and next steps.

## Security Rules

- Never read or print `secrets/mt5.env`; existence and permissions checks are allowed.
- Never commit `secrets/`, `data/raw/`, `data/normalized/`, `.venv/`, logs with secrets, Wine folders, local model files, or backups.
- Mask account, password, token, cookie, and API key material in diagnostics.
- Prefer allowlists over blocklists for crawler source control.

## Idempotency And Recovery

- Re-running initialization should not duplicate sources, jobs, chunks, or reports unnecessarily.
- Re-running indexing should not grow active chunks for unchanged content.
- Schema changes should be versioned or guarded by migrations.
- Commands that mutate persistent state should be explicit about what changed.

## Migration And Versioning

- SQLite schemas should use `CREATE TABLE IF NOT EXISTS` plus clear migration points.
- Backward compatibility matters for CLI output used by scripts.
- Breaking changes require docs and handoff notes.
