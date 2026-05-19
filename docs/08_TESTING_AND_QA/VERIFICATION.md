# Dominion Verification Pipeline

This document describes the two-level verification pipeline used to keep the
Dominion platform at **LIVE_GREEN** status.

---

## Quick Reference

| Script | Requires live services? | Status label |
|---|---|---|
| `scripts/verify_source.sh` | No | `SOURCE_GREEN` / `SOURCE_WARN` / `SOURCE_FAIL` |
| `scripts/verify_live.sh`   | Yes (RAGD, MT5 bridge) | `LIVE_GREEN` / `LIVE_WARN` / `LIVE_FAIL` |

---

## scripts/verify_source.sh — Source-Only Gate

**Purpose:** Fast, CI-safe check that validates the repo source code without
requiring any live services (no RAGD daemon, no MT5, no network).

**Checks run:**

1. **Python syntax / compile** via `scripts/compile_source.py`  
   Walks only repo-owned source directories.  
   Returns non-zero if any file has a syntax error.

2. **Safety scanner** — `python domdata/check_no_trading.py`  
   Scans for forbidden trading tokens in all source files.

3. **Unit tests** — `python -m pytest -q --tb=short`  
   Uses `pytest.ini` testpaths (unit-tagged packages only, `not integration`).

4. **Lightweight offline smokes**  
   - `domdata notice` — confirms domdata CLI is importable  
   - `domdata order-send` — confirms trading commands remain blocked  
   - `from dominion_agent import tasks, sessions, safety` — pure import check  
   - Binary presence checks (ragd, dominion-native-scan) as warnings

**Usage:**

```bash
bash scripts/verify_source.sh
```

Expected output when clean:

```
=== Dominion Source-Only Verification  2026-05-19T...Z ===
  PASS  compile-source
  PASS  no-trading-tokens
  PASS  pytest-unit
  ...
  Status: SOURCE_GREEN
```

---

## scripts/compile_source.py — Source Compile Helper

**Purpose:** Replaces any naive `python -m compileall .` invocation.
`compileall .` from the repo root would walk `.venv/` (thousands of
third-party files), `apps/mt5/` (Wine prefix Python stdlib), `vault/files/`
(Markdown/binary vault mirrors), and `data/` (generated Parquet/DuckDB), all
of which are irrelevant noise and may contain stale `.pyc` files that report
false errors.

**Allowed source roots** (defined in `SOURCE_ROOTS` list inside the script):

```
asset_graph       causal_engine     data_pipeline
domdata           dominion_agent    dominion_ai
dominion_loader   exec_features     exec_sim
lob               ragd_bus          ragd_chunker
ragd_embed        ragd_graph        ragd_hnsw
ragd_vault        research_os       reservoir
tca               toxicity
scripts/*.py (top-level only)
```

**To add a new source package:** append its name to `SOURCE_ROOTS` in
`scripts/compile_source.py`.

---

## scripts/verify_live.sh — Full WSL Runtime Gate

**Purpose:** Full integration check on the real WSL VM.  Requires:

- RAGD daemon running on `http://127.0.0.1:7474`
- Native build artifacts under `ragd/build/`
- domdata / MT5 bridge available

**Checks run:**

- Build artifact presence (ragd binary, native-doctor, native-scan, native-vault-doctor)
- RAGD health endpoint
- RAGD query smoke
- Native doctor (live JSON)
- Python truth (live)
- Vault doctor (broken links)
- domdata safety (notice, order-blocked, doctor)
- Agent OS imports
- Forbidden-token scanner

**Usage:**

```bash
bash scripts/verify_live.sh
```

**Exit codes:**

| Code | Status | Meaning |
|------|--------|---------|
| 0 | `LIVE_GREEN` | All checks pass, no warnings |
| 1 | `LIVE_WARN`  | No failures, but warnings present |
| 2 | `LIVE_FAIL`  | One or more hard failures |

---

## What LIVE_GREEN Means

`LIVE_GREEN` indicates:

- All source code compiles without syntax errors.
- The forbidden trading-token scanner finds no violations.
- The full unit-test suite passes (435+ tests).
- The RAGD daemon is reachable and returns valid query results.
- Native build artifacts are present and healthy.
- domdata is read-only and trading commands remain blocked.
- The vault has no broken links.

It does **not** mean the ML models are trained, market data is fresh, or that
live trading is possible (live trading is permanently disabled per platform
safety rules).

---

## Intentional Exclusions

The following are **never** compiled or tested as repo source:

| Path | Reason |
|------|--------|
| `.venv/` | Third-party dependencies managed by pip; not repo code |
| `apps/mt5/`, `apps/mt5-official/`, `apps/wine-python/` | Wine prefix / Windows EXE; not Python source |
| `vault/files/`, `vault/symbols/` | Mirror of Markdown/binary content; not Python |
| `data/` | Generated Parquet, DuckDB, CSV files; no Python source |
| `tmp/` | Transient working files |
| `__pycache__/`, `.pytest_cache/`, `.git/` | Build/cache artifacts |
| `build/`, `dist/` | CMake / wheel outputs |
| `ragd/vendor/` | Vendored C++ dependencies |

### Why .venv must not be compiled as source

`.venv/` contains pre-built third-party packages.  Running `compileall` on it:

1. Is slow (thousands of files, many already have `.pyc` from installation).
2. May fail on `.py` stubs generated for the installed Python version.
3. Produces false positives that obscure real repo errors.
4. Inflates test output noise by orders of magnitude.

The correct approach (enforced by `scripts/compile_source.py`) is to compile
only the explicitly allowlisted source roots.

### Why vault mirrors must not be compiled as source

`vault/files/` contains arbitrary Markdown and binary content ingested from
the filesystem into the RAGD knowledge base.  It is read by the vault indexer,
not executed as Python.  `vault/symbols/` contains structured symbol-index
JSON/binary files.  Neither is Python source.

---

## Running the Full Validation Suite

Recommended order (matches AGENTS.md validation policy):

```bash
python domdata/check_no_trading.py
bash scripts/verify_source.sh
python -m pytest -q
bash scripts/verify_live.sh   # requires live services
```

For RAGD C++ changes:

```bash
cmake -S ~/Dominion/ragd -B ~/Dominion/ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ~/Dominion/ragd/build -j$(nproc)
cd ~/Dominion/ragd/build && ctest --output-on-failure
```
