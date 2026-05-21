---
synced: 2026-05-20 18:19
---
# Feature Completion Matrix

## Agent 1 Scope (Foundation)

| Feature | Status | Evidence | Notes |
|---|---:|---|---|
| F01 Repo discovery | Complete | `test_discover.py` 11 tests | Sorted, deterministic, symlinks followed |
| F02 File classification | Complete | `test_classify.py` 25 parametrized cases | 50+ extensions, name map |
| F03 Content hashing | Complete | `test_hashing.py` 9 tests | Real SHA256, mtime fast-path |
| F04 Incremental manifest | Complete | `test_manifest.py` 12 tests, `test_scan.py` | SQLite WAL, schema v1 |
| F05 RAGD bridge | Complete | `test_ragd_bridge.py` 11 tests | Batched POST /index, retry, feature flag |
| F06 Ignore rules | Complete | `test_ignore.py` 8 tests | Immutable secrets boundary, .dominionignore |
| F07 Observability | Complete | `obs.py` | JSONL traces, thread-local, NullTracer |
| F08 Cache | Complete | `test_cache.py` 10 tests | Fingerprint, quarantine, CacheCorruption |
| F09 Semantic diff | Complete | `test_semantic_diff.py` 12 tests | Conservative bias, 4 levels |
| F10 Scan pipeline | Complete | `test_scan.py` 11 tests | Discover→classify→hash→manifest→RAGD |
| F11 Public API | Complete | `api.py`, `test_contract_loaded_file.py` | INTERFACE(agent-1) v1.0.0 |
| F12 Chunking hooks | Complete | `test_chunking_hooks.py` | Agent 2 registration layer |
| F13 Knowledge graph | Complete | `test_graph.py` 12 tests | kg_nodes, kg_edges, SQLite |
| F14 Ledger | Complete | `test_ledger.py` 8 tests | Multi-agent memory writer |
| F15 Profiler | Complete | `profiler.py` | profile_spans SQLite table |
| F16 Benchmark harness | Complete | `test_bench.py` 9 tests | p50/p95/p99, foundation suite |
| F17 Hardware probe | Complete | `test_hw_probe.py` 7 tests | CPU/RAM/GPU, JSON-serializable |
| F18 CLI extensions | Complete | `dominion scan/cache/manifest/loader-bench` | Additive, no regressions |
| F19 SQL migrations | Complete | `ragd/sql/migrations/0002-0004.sql` | kg_nodes, ledger, profile_spans |

## Agent 2 Scope

| Feature | Status | Evidence | Notes |
|---|---:|---|---|
| F10 Query planner | Complete | `dominion_ai/tests/test_planner.py`; full pytest `42 passed` | Rules-first deterministic planner |
| F11 Hybrid retrieval strategy | Complete | `dominion search "agent handoff" --top-k 3 --json`; `dominion_ai/tests/test_retrieval.py` | Composes RAGD BM25 + vector, no duplicate index |
| F12 Reranking pipeline | Complete | `dominion_ai/tests/test_rerank.py` | Heuristic default only; embedding/LLM rerank deferred |
| F13 Context assembly | Complete | `dominion_ai/tests/test_context.py`; `dominion_ai/tests/test_budget.py` | Budget-aware section packer with citations |
| F14 Local generation provider abstraction | Retired by Agent 6 | `scripts/bin/llm`; `dominion ask --generate --json` | Frontier agents handle generation; RAGD provides retrieval context |
| F15 4 GB VRAM governor | Retired by Agent 6 | `dominion embed stats --json` | Hardware governor removed with local generation subsystem |
| F16 Developer CLI | Complete | `dominion_ai/tests/test_cli.py`; live `dominion ask/search/trace/eval/ledger` | Additive only |
| F17 Trace UX | Complete | `dominion trace ad51518679964fab8b78802762e7d5bd` | A2 spans emitted under `~/.dominion/traces` |
| F18 Bench suites | Partial | `dominion bench --suite retrieval/e2e/generation` | Lightweight suite, not Agent 1 harness registration |
| F19 Retrieval eval harness | Complete | `reports/eval/tiny-20260513-215612.json` | Tiny bundle produced recall@10/MRR/nDCG/citation accuracy |
| F20 Ledger query UX | Complete | `dominion ledger list --kind decision --since 7d --json` | Read/query over RAGD decisions; append delegated |

## Agent 3 Scope (Truth And Integrity)

| Defect | Status | Evidence | Notes |
|---|---:|---|---|
| D01 Deleted files remain active in RAGD | Complete | `ragd/tests/test_storage.cpp`; live delete smoke in `reports/phase-3-truth-final-20260513-232814.md` | `POST /index/delete`; loader scan propagation |
| D02 RAGD query omits identity metadata | Complete | `ragd/tests/test_rag_engine.cpp`; live `/query` metadata sample | Adds `content_hash`, `repo_root`, `status`, `indexed_at`, `modified_at` |
| D03 `dominion_ai` temp identity adapter | Partial | `dominion_ai/tests/test_ragd_client.py` | `content_hash` now producer-owned; `document_id` fallback remains labeled |
| D04 Deep doctor real consistency | Complete | `dominion_loader/tests/test_truth_doctor.py`; `dominion doctor --deep --json` | Actual manifest/cache/RAGD DB checks |
| D05 Ignore policy split | Partial | `dominion_loader/tests/test_ignore.py`; `dominion ignore policy --json` | Python policy hash exported; RAGD hash still unavailable so doctor warns |
| D06 Unsafe safe LLM profile | Retired by Agent 6 | `scripts/bin/llm`; `dominion ask --generate --json` | Local generation profiles removed |
| D07 Report evidence schema | Complete | `docs/agents/TRUTH_CONTRACT.md`; final report | Evidence tables and pass/warn/fail reporting |
| D08 Cache integrity in doctor | Complete | `dominion_loader/tests/test_truth_doctor.py::test_deep_doctor_reports_cache_corruption` | Actual cache verify wired into deep doctor |
| D09 Orphan chunks surfaced | Complete | `dominion doctor --deep --json` | Reports orphan active chunks with sample cap |
| D10 Stale result provenance incomplete | Complete | `dominion search "agent handoff" --top-k 1 --json` | Search JSON exposes RAGD metadata and adapter warnings |
