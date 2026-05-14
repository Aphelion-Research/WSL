# Dominion Doctor Contract

Native doctor check statuses:

- `pass`: invariant or check succeeded.
- `warn`: non-blocking problem or stale advisory.
- `fail`: required invariant failed.
- `skip`: check intentionally not run in the selected mode.

Native doctor modes:

- `--offline`: live service reachability is skipped. Static invariants can still fail.
- `--live`: required live services such as RAGD reachability fail when unavailable.
- `--strict`: warnings produce a nonzero exit code.
- `--json`: stable machine-readable JSON output.

Python integration:

- `python scripts/dominion_cli.py doctor --offline` invokes `ragd/build/dominion-native-doctor` when present and embeds its JSON under `native_doctor`.
- `python scripts/dominion_cli.py native doctor --offline --json` directly returns the native doctor JSON.
- If a native binary is missing, native subcommands report `native_fallback: true`.

Offline success can still report `overall: warn` when advisory checks such as vault integrity are stale.

