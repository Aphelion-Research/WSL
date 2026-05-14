# Phase 5 Native Core Final Report

## Summary

Dominion Native Core v1 is implemented as a C++17 library and tool surface under `ragd/`.

Release-ready: no.

Reason: native core build/tests and Python tests pass, but live RAGD is not reachable at `127.0.0.1:7474` and vault integrity remains stale.

## What Changed

- Added `dominion_native` shared C++ library.
- Added native tools: `dominion-native`, `dominion-native-scan`, `dominion-native-manifest`, `dominion-native-doctor`, `dominion-native-vault-doctor`.
- Hardened RAGD CMake with explicit Dominion options, corrected dependency hashes, OpenSSL SHA-256, and multiarch SQLite discovery.
- Added native CTest coverage for policy, paths, classifier, hashing, scan plan, manifest, vault, forbidden tokens, doctor, locks, conflicts, and evidence validation.
- Added Python CLI `native` subcommands and native doctor embedding in `doctor --offline`.
- Added canonical `config/forbidden_tokens.json` and Python/native fingerprint checking.
- Added RAGD query metadata fields: `document_id`, `stable_chunk_id`, `relative_path`, `language`, `score_breakdown`, `source_subsystem`.

## Native C++ Components Added

- Ignore policy parser and fingerprint.
- Path normalizer with outside-repo, Windows-drive, and Wine-path rejection signals.
- File classifier with binary/large/generated detection.
- Real SHA-256 content hashing and stable document/chunk IDs.
- Deterministic scan planner.
- SQLite manifest store with WAL, migrations, transaction-scoped scan commits, and deleted-file marking.
- Native doctor with `pass/warn/fail/skip`.
- Native vault doctor.
- Native Agent OS lock conflict, scope overlap, and evidence validation primitives.

## Python Integration Changes

- `python scripts/dominion_cli.py native scan --json`
- `python scripts/dominion_cli.py native doctor --offline --json`
- `python scripts/dominion_cli.py native manifest scan --root . --db PATH`
- `python scripts/dominion_cli.py native vault-doctor --json`
- `python scripts/dominion_cli.py doctor --offline --json` now includes `native_doctor` when the native binary exists.

## Safety Boundary

- No live trading code added.
- `order-send` remains blocked.
- `python domdata/check_no_trading.py` passes.
- `secrets/` remains blocked by native ignore policy.
- `secrets/mt5.env` contents were not read.
- MT5 diagnostics remained masked.

## Commands Run

### Python Tests

```text
python -m pytest -q
=> 387 passed, 2 deselected in 56.95s

python -m pytest -q -m "not integration"
=> 387 passed, 2 deselected in 58.66s

python -m pytest -q dominion_agent/tests
=> 109 passed in 1.55s

python -m pytest -q dominion_loader/tests/test_doctor.py
=> 4 passed in 53.81s
```

### C++ Build

```text
cmake -S ragd -B ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
=> PASS
=> SQLite detection: find_library:/usr/lib/x86_64-linux-gnu/libsqlite3.so.0
=> nlohmann_json SHA256=d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d
=> cpp_httplib SHA256=8900747bba3dda8007f1876175be699036e09e4a25ceeab51196d9365bf1993a

cmake --build ragd/build -j$(nproc)
=> PASS
```

### CTest

```text
ctest --test-dir ragd/build --output-on-failure
=> 100% tests passed, 0 tests failed out of 24
```

### Trading Scanner

```text
python domdata/check_no_trading.py
=> PASS: no forbidden trading tokens outside allowlist

domdata notice
=> DOMDATA READ-ONLY MODE

domdata order-send || true
=> BLOCKED: domdata is read-only. This command will never execute trades.
```

### Domdata

```text
domdata doctor
=> MetaTrader5 import: OK
=> account masked

domdata xautick
=> tick: null
=> last_error: [-10001, "IPC send failed"]

domdata xaurates --count 5
=> returned 5 bars

domdata xauticks --start 2026-05-11T00:00:00Z --count 5
=> null

python -m domdata notice
=> failed: No module named domdata.__main__
```

### Doctor

```text
python scripts/dominion_cli.py doctor --offline
=> exit 0
=> native_doctor overall=warn
=> platform checks displayed as SKIP in offline mode

python scripts/dominion_cli.py doctor --offline --json
=> overall: ok
=> native_doctor overall: warn

ragd/build/dominion-native-doctor --root . --offline --json
=> exit 0
=> overall: warn
=> RAGD reachability: skip

ragd/build/dominion-native-doctor --root . --live --json
=> exit 1
=> overall: fail
=> RAGD reachability: fail
```

### Vault Doctor

```text
python -m ragd_vault.cli doctor --json
=> ok=false
=> broken_links=281
=> total_notes=874

ragd/build/dominion-native-vault-doctor --root . --json
=> status=warn
=> notes=874
=> broken_links=298
=> stale_links=278
=> outside_repo_links=278
=> secret_reference_count=0
```

## Benchmark Results

```text
ragd/build/dominion-native bench --root . --json
=> scan_files_per_sec: 1150.72
=> hash_mb_per_sec: 1.72
=> cold_scan_wall_ms: 1108
=> seen: 1481
=> included: 1275
=> ignored: 62
=> errors: 0
```

No Python scan speedup is claimed; a direct Python-vs-native benchmark was not added.

## Before / After

Before:

- CMake configure failed on dependency hash mismatch.
- Native policy/path/hash/manifest/doctor surfaces did not exist.
- RAGD used `std::hash` behind `sha256ish`.
- Python was the only command-facing doctor/manifest path.

After:

- CMake configure/build passes with pinned dependency hashes.
- Native C++ tests pass.
- Native scan/manifest/doctor/vault tools work offline.
- RAGD emits stable native metadata in query results.
- Python can call native tools without making native availability silent.

## Remaining Failures

- `ragd/build/dominion-native-doctor --root . --live --json`: fail because RAGD is not reachable at `127.0.0.1:7474`.
- `python -m domdata ...`: fail because `domdata` has no `__main__`; use the supported `domdata ...` CLI.
- `ragd_handoff_read`, `ragd_query`, and `ragd_remember`: failed because RAGD MCP at `127.0.0.1:7474` refused connections.

## Skipped Checks

- Offline native doctor skips live RAGD reachability by design.
- No live RAGD deletion-propagation smoke was run because RAGD was not reachable.
- No Python-vs-native scan benchmark was produced.
- RAGD memory write was attempted and failed due to the same RAGD MCP connection refusal.

## Files Changed

Primary changed/added paths:

- `ragd/CMakeLists.txt`
- `ragd/include/dominion_native/`
- `ragd/src/native/`
- `ragd/tools/`
- `ragd/tests/native/`
- `ragd/src/storage.cpp`
- `ragd/src/rag_engine.cpp`
- `ragd/tests/test_rag_engine.cpp`
- `scripts/dominion_cli.py`
- `config/forbidden_tokens.json`
- `domdata/domdata_pkg/forbidden_tokens.py`
- `docs/NATIVE_CORE.md`
- `docs/RAGD_NATIVE_CONTRACT.md`
- `docs/DOCTOR_CONTRACT.md`
- `docs/CPP_BUILD.md`

Pre-existing dirty files preserved:

- `dominion_agent/safety.py`
- `reports/phase-5-consolidation-latest.md`

## Risk Register

- Native vault doctor is stricter than Python vault doctor and currently reports more broken links.
- Native manifest exists as a parallel substrate; loader/RAGD ingestion are not yet fully backed by it.
- FetchContent remains network-dependent on a clean machine unless the pinned archives are cached.
- `doctor --offline` is slower because it invokes native scan/vault checks.

## Rollback Instructions

To roll back Phase 5 native core only:

```bash
rm -rf ragd/include/dominion_native ragd/src/native ragd/tools ragd/tests/native
rm -f config/forbidden_tokens.json
rm -f docs/NATIVE_CORE.md docs/RAGD_NATIVE_CONTRACT.md docs/DOCTOR_CONTRACT.md docs/CPP_BUILD.md
git restore ragd/CMakeLists.txt ragd/src/storage.cpp ragd/src/rag_engine.cpp ragd/tests/CMakeLists.txt ragd/tests/test_rag_engine.cpp scripts/dominion_cli.py domdata/domdata_pkg/forbidden_tokens.py
cmake -S ragd -B ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ragd/build -j$(nproc)
```

Do not restore unrelated pre-existing user edits unless explicitly requested.

## Next Recommended Phase

1. Start or repair RAGD on `127.0.0.1:7474` and run native live doctor.
2. Regenerate or repair vault notes to clear stale `/tmp/pytest-*` links.
3. Wire native manifest scan commits into the loader/RAGD ingestion path.
4. Add a measured Python-vs-native scan benchmark if speedup claims are needed.
