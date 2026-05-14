# RAG Baseline Before Phase 6

Captured UTC: 2026-05-14T02:43:16+00:00

## Git Status
```text
 M domdata/domdata_pkg/collector.py
 M dominion_agent/locks.py
 M dominion_agent/migrations.py
 M dominion_loader/cli.py
 M dominion_loader/truth_doctor.py
 M [retired local generation path]/governor.py
 M ragd/include/ragd/rag_engine.h
 M ragd/src/http_api.cpp
 M ragd/src/rag_engine.cpp
 M research_os/scheduler.py
?? docs/agents/RAG_BASELINE_BEFORE_PHASE_6.md
```

## Query Latency Baseline
```text
{
  "elapsed_ms": 48,
  "result_count": 10
}
wall_seconds=0.09
```

## Index Size
```text
active_chunks=959
active_files=406
```

## BM25-only Retrieval Sample
Query: how does incremental scan detect deleted files

```json
{
  "elapsed_ms": 41,
  "results": [
    {
      "rank": null,
      "filepath": "/home/Martin/Dominion/ragd/README.md",
      "symbol_name": "## Quick Start",
      "chunk_type": "section",
      "line_start": 7,
      "line_end": 25,
      "score": 8.163916796542296,
      "content_hash": "34b63a5ea749f3b8"
    },
    {
      "rank": null,
      "filepath": "/home/Martin/Dominion/ragd/tests/test_intent_router.cpp",
      "symbol_name": "main",
      "chunk_type": "function",
      "line_start": 7,
      "line_end": 35,
      "score": 7.164867215575672,
      "content_hash": "e0fbdf28b3a3f405"
    },
    {
      "rank": null,
      "filepath": "/home/Martin/Dominion/ragd/src/intent_router.cpp",
      "symbol_name": "route_intent",
      "chunk_type": "function",
      "line_start": 9,
      "line_end": 26,
      "score": 6.3118729723744185,
      "content_hash": "c273b71c21c47c73"
    },
    {
      "rank": null,
      "filepath": "/home/Martin/Dominion/AGENT_HANDOFF.md",
      "symbol_name": "## Agent 2 Phase 2 Handoff - 2026-05-13",
      "chunk_type": "section",
      "line_start": 170,
      "line_end": 203,
      "score": 6.293401638925436,
      "content_hash": "47898293e5cdd7ab"
    },
    {
      "rank": null,
      "filepath": "/home/Martin/Dominion/domdata/domdata_pkg/collector.py",
      "symbol_name": "latest_file",
      "chunk_type": "function",
      "line_start": 210,
      "line_end": 216,
      "score": 5.862486082474335,
      "content_hash": "646c84ea665c8ec4"
    }
  ]
}
```

## After Phase 6

Measured after rebuilding and restarting RAGD, indexing `dominion_loader/scan.py` through the chunker service, building graph, and syncing the vault.

### Query Latency: /query/hybrid
```json
{
  "elapsed_ms": 7,
  "retrieval_strategy": "hybrid_rrf_bm25_keyword_hnsw_external",
  "result_count": 10,
  "first": {
    "filepath": "/home/Martin/Dominion/docs/DATA_PIPELINE.md",
    "symbol_name": "# Data Pipeline",
    "qualified_name": ""
  }
}
{'wall_seconds': 0.0324}
```

### Query Latency: /query/semantic
```json
{
  "ok": false,
  "error": "RAGD_EMBED_API_KEY is required before code embeddings are sent to an external provider"
}
```

### Index Size
```text
active_chunks=971
active_files=413
```

### AST Metadata Sample
```json
{
  "filepath": "/home/Martin/Dominion/dominion_loader/scan.py",
  "symbol_name": "ScanStats",
  "qualified_name": "dominion_loader.scan.ScanStats",
  "parent_symbol": "",
  "imports_count": 13,
  "calls_count": 0,
  "content_hash": "796d1f4c52df9f567f25ea8566cbed573afc147c14b270073d675e2e64b75baf",
  "status": "active"
}
{
  "filepath": "/home/Martin/Dominion/dominion_loader/scan.py",
  "symbol_name": "scan",
  "qualified_name": "dominion_loader.scan.scan",
  "parent_symbol": "",
  "imports_count": 13,
  "calls_count": 40,
  "content_hash": "0ef1f80d70c0b6c72a85d794960429deb8a14202da071e38ec7e5ed3d7c48b33",
  "status": "active"
}
```

### Graph And Vault
```json
{
  "graph": {
    "by_relation": {
      "calls": 56,
      "defines": 971,
      "imports": 52
    },
    "edges": 1079,
    "nodes": 965
  },
  "vault": {
    "broken_links": [],
    "invalid_frontmatter": [],
    "mermaid_errors": [],
    "ok": true,
    "orphan_notes": [
      "_templates/Daily Changelog",
      "_templates/File Note",
      "_templates/Symbol Note",
      "files/ragd/CMakeLists",
      "files/ragd/examples/query_example",
      "files/ragd/include/ragd/dead_zone",
      "files/ragd/include/ragd/intent_router",
      "files/ragd/include/ragd/mcp_server",
      "files/ragd/include/ragd/session_bus",
      "files/ragd/install",
      "files/ragd/scripts/agent-init",
      "files/ragd/scripts/ragd-cli",
      "files/ragd/tests/test_agent_memory",
      "files/ragd/tests/test_bm25",
      "files/ragd/tests/test_dead_zone",
      "files/ragd/tests/test_indexer",
      "files/ragd/tests/test_intent_router",
      "files/ragd/tests/test_mcp_server",
      "files/ragd/tests/test_rag_engine",
      "files/ragd/tests/test_session_bus",
      "files/ragd/tests/test_storage",
      "files/ragd/tests/test_temporal",
      "files/ragd/tests/test_todo_engine",
      "files/ragd/tests/test_vector_store",
      "files/reports/dominion-v2-20260512-164703",
      "files/scripts/bin/codexprompt",
      "files/scripts/bin/codexrag",
      "files/scripts/bin/codexstart",
      "files/scripts/bin/codexstatus",
      "files/scripts/bin/dominion-ui",
      "files/scripts/bin/dominion",
      "files/scripts/bin/llm",
      "files/scripts/bin/research",
      "files/tmp/pytest-of-Martin/pytest-14/test_rescan_detects_new_file0/newfile",
      "files/tmp/pytest-of-Martin/pytest-15/test_rescan_detects_new_file0/newfile",
      "files/tmp/pytest-of-Martin/pytest-19/test_rescan_detects_new_file0/newfile",
      "files/tmp/pytest-of-Martin/pytest-20/test_rescan_detects_new_file0/newfile",
      "files/tmp/pytest-of-Martin/pytest-21/test_rescan_detects_new_file0/newfile"
    ],
    "total_notes": 1247
  }
}
```

### Retrieval Quality Note
Semantic recall delta is not claimed because `RAGD_EMBED_API_KEY` is unset. `/query/semantic` fails closed before sending code to an external provider.
