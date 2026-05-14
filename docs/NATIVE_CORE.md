# Dominion Native Core v1

Dominion Native Core v1 lives under `ragd/` and provides the C++ substrate for deterministic local checks:

- `dominion_native`: shared C++17 library for policy, paths, classification, hashing, scan planning, manifest storage, doctor checks, vault integrity, forbidden-token policy, and Agent OS primitives.
- `dominion-native-scan`: builds a deterministic scan plan without requiring live RAGD.
- `dominion-native-manifest`: initializes, scans into, and doctors the native SQLite manifest.
- `dominion-native-doctor`: aggregates offline/live native platform checks with `pass`, `warn`, `fail`, and `skip`.
- `dominion-native-vault-doctor`: reports stale vault links, outside-repo links, temp pytest links, and secret references.
- `dominion-native bench`: reports local scan/hash throughput from the native path.

Python remains the CLI and compatibility layer. `scripts/dominion_cli.py native ...` shells out to the compiled native tools and reports explicit fallback if a binary is missing.

Safety boundaries:

- `secrets/` is always ignored by native scan policy.
- MT5 trading tokens are centralized in `config/forbidden_tokens.json`.
- Native and Python forbidden-token fingerprints are compared by the native doctor.
- No native component reads `secrets/mt5.env` contents.
- Offline doctor skips live RAGD reachability instead of failing it.

Current known limitation:

- Native vault doctor is stricter than the Python vault doctor and may report additional broken links. Treat vault as stale until regenerated or repaired.

