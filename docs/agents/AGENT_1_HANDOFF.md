# Agent 1 Phase 1 Handoff

**Status:** COMPLETE  
**Phase:** Core Foundation and System Spine  
**Agent:** Agent 1  
**Completed:** 2026-05-13 (UTC)

---

## What Was Built

The `dominion_loader/` Python package — the deterministic, observable, measurable foundation of the Dominion engineering intelligence platform.

### Core Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `ignore.py` | Centralized ignore rules with immutable secrets boundary | ✓ |
| `classify.py` | File classification → (FileClass, language) | ✓ |
| `discover.py` | Deterministic sorted directory walker | ✓ |
| `hashing.py` | Real SHA256 + mtime/size fast-path | ✓ |
| `obs.py` | JSONL trace spans (thread-local, offline-safe) | ✓ |
| `manifest.py` | SQLite WAL manifest at `~/.dominion/manifest.db` | ✓ |
| `cache.py` | Content-addressed cache with fingerprint validation | ✓ |
| `semantic_diff.py` | Format-only vs functional change classifier | ✓ |
| `ragd_bridge.py` | RAGD `/index` producer bridge (batched, retrying) | ✓ |
| `scan.py` | Full pipeline: discover→classify→hash→manifest→RAGD | ✓ |
| `api.py` | Stable public API surface for Agent 2 | ✓ |
| `chunking_hooks.py` | Hook registration layer for Agent 2 chunkers | ✓ |
| `graph.py` | SQLite knowledge graph (kg_nodes, kg_edges) | ✓ |
| `ledger.py` | Multi-agent memory ledger writer | ✓ |
| `profiler.py` | Self-profiling span recorder | ✓ |
| `bench.py` | Benchmark harness with foundation suite | ✓ |
| `hw_probe.py` | Hardware profile (CPU/RAM/GPU) | ✓ |

### CLI Extensions (`scripts/dominion_cli.py`)

New subcommands added (additive, no existing commands broken):

| Command | Description |
|---------|-------------|
| `dominion scan [--dry-run] [--repo PATH] [--json]` | Run incremental repo scan |
| `dominion cache stats\|verify\|nuke` | Cache management |
| `dominion manifest list\|stats` | Manifest inspection |
| `dominion loader-bench --suite foundation` | Run benchmarks |
| `dominion loader-ledger append --kind KIND --payload JSON` | Append ledger entries |
| `dominion gstats stats\|build` | Knowledge graph stats/build |
| `dominion doctor --json` | Extended with foundation checks |

### SQL Migrations

- `ragd/sql/migrations/0002_kg_nodes_edges.sql`
- `ragd/sql/migrations/0003_ledger_entries.sql`
- `ragd/sql/migrations/0004_profile_spans.sql`

### Test Suite

17 test files in `dominion_loader/tests/`:
- test_ignore.py, test_classify.py, test_discover.py
- test_hashing.py, test_manifest.py, test_cache.py
- test_semantic_diff.py, test_scan.py
- test_ragd_bridge.py, test_graph.py, test_ledger.py
- test_bench.py, test_hw_probe.py, test_chunking_hooks.py
- test_contract_loaded_file.py, test_contract_ragd_ingestion.py, test_doctor.py

---

## Critical Invariants for Agent 2

### Secrets are always blocked
`Ignore._BUILTIN_DIR_DENY` includes `secrets`. This is a frozenset — immutable. `.dominionignore` cannot override it.

### `sha256ish()` in RAGD is NOT real SHA256
RAGD C++ uses `std::hash<string>` for chunk hashing. The loader uses `hashlib.sha256` for all IDs. These are separate ID spaces. Agent 2 must NOT assume loader `document_id` == RAGD internal chunk hash.

### RAGD bridge is producer-only
`RagdBridge.ingest_paths()` submits file paths to RAGD `/index`. RAGD owns chunking strategy (see `ragd/src/indexer.cpp`). The bridge reports `chunks_indexed` from RAGD's response.

### LoadedFile is frozen at v1
`LoadedFile` dataclass (in `scan.py`) has these fields — do NOT remove or rename:
- `path`, `relative_path`, `repo_root`, `size`, `mtime_ns`
- `file_class`, `language`, `content_hash`, `document_id`, `trace_id`
- `is_new`, `is_changed`

### IngestResult.ok is derived
`IngestResult.ok = (error is None)`. `paths_failed` is derived from error count. `elapsed_s = duration_ms / 1000`.

### Manifest is rebuildable
The manifest is not a source of truth for chunk content. A full scan rebuilds it from scratch. On `~/.dominion/` doesn't exist yet — `Manifest.__init__()` creates it.

### Feature flags
All modules respect feature flags:
- `DOMINION_LOADER=new|legacy`
- `DOMINION_RAGD_BRIDGE=on|off`
- `DOMINION_TRACE=on|off`
- `DOMINION_CACHE=on|off`
- `DOMINION_HASH=full` (forces SHA256 even when fast-path would apply)
- `DOMINION_PROFILER=on|off`
- `DOMINION_CHUNKER_HOOKS=on|off`

---

## What Agent 2 Should Know

1. Call `from dominion_loader import iter_files, get_manifest_entry, list_changed_since, semantic_diff, hw_probe, cache_get, cache_put` for the stable API.
2. Register custom chunkers via `register_chunker(language, fn)` before calling `iter_files()`.
3. Read hardware profile via `hw_probe()` to decide which local model to load.
4. Use `list_changed_since(epoch)` to get only files that changed since a given time.
5. `cache_get` / `cache_put` use namespace + fingerprint pattern — fingerprint should be content_hash.
6. Query ledger via `Ledger().query_kind("decision")` — no Agent 2 write API needed (write via `Ledger.append()`).
7. Knowledge graph is built by `ingest_from_ragd(kg, ragd_db_path)` — call this after a scan.

---

## Next Best Tasks for Agent 2

1. Implement retrieval layer: query RAGD for context (use `ragd_query` MCP tool)
2. Build model selection logic using `hw_probe()` output
3. Implement context window packing using `list_changed_since()` + chunking hooks
4. Build evaluation harness against `reports/benchmarks/`
