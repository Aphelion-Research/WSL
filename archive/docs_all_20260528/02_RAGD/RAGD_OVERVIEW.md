---
doc_type: ragd
system: RAGD
ragd_priority: 9
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - ragd
  - retrieval
  - overview
---

# RAGD Overview

**Status:** SOURCE_GREEN (REST API operational) | LIVE_WARN (chunker/embed config incomplete)

## Purpose

RAGD (Retrieval-Augmented Graph Database) is Dominion's persistent memory system. This doc provides a high-level overview of RAGD's architecture, current state, and capabilities.

---

## Current State (2026-05-19)

### What Works (SOURCE_GREEN)
- ✓ RAGD daemon running on 127.0.0.1:7474
- ✓ SQLite storage + HNSW vector index
- ✓ Native C++ implementation (24/24 tests passing)
- ✓ REST API for query/index/health
- ✓ 7159 active chunks indexed
- ✓ Graph storage (1055 nodes, 1215 edges)
- ✓ 878-note Obsidian vault with 0 broken links

### What's Incomplete (LIVE_WARN)
- ⚠ Chunker service unreachable (connection refused)
- ⚠ Embedding config: no API key present
- ⚠ MCP server not connected (tools referenced in docs but unavailable)
- ⚠ Native WebSocket `/bus` not implemented yet (REST only)

### Overall Doctor Status
```json
{
  "overall": "warn",
  "ragd_chunker": {"status": "warn", "reachable": false},
  "ragd_embed": {"status": "warn", "api_key_present": false},
  "ragd_bridge": {"status": "ok", "reachable": true}
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Client Applications                │
│    (dominion_cli, agents, research_os)          │
└────────────┬────────────────────────────────────┘
             │
             │ REST API (127.0.0.1:7474)
             ↓
┌─────────────────────────────────────────────────┐
│           RAGD Daemon (C++)                     │
│  ┌──────────────┐  ┌──────────────┐             │
│  │ Query Engine │  │ Index Engine │             │
│  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                      │
│  ┌──────▼──────────────────▼──────┐             │
│  │      Graph Store (SQLite)       │             │
│  │  - Nodes (chunks, docs, code)   │             │
│  │  - Edges (calls, imports)       │             │
│  └──────┬──────────────────────────┘             │
│         │                                        │
│  ┌──────▼──────────────────────────┐             │
│  │   HNSW Vector Index (.bin)      │             │
│  │  - 768-dim embeddings           │             │
│  │  - nomic-embed-text (ollama)    │             │
│  └─────────────────────────────────┘             │
└─────────────────────────────────────────────────┘
```

---

## Key Operations

### Query RAGD
```bash
# REST API
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{"q":"agent workflow","top_k":5}'

# CLI (Python wrapper)
python scripts/dominion_cli.py search "agent workflow" --top-k 5 --json
```

### Index Files
```bash
# REST API
curl -X POST http://127.0.0.1:7474/index \
  -H 'Content-Type: application/json' \
  -d '{"path":"docs/new_doc.md","content":"..."}'

# CLI (full scan)
python scripts/dominion_cli.py scan
```

### Health Check
```bash
curl http://127.0.0.1:7474/health

# Expected response
{"status":"ok","version":"0.1.0","uptime_seconds":12345}
```

---

## Subsystems

### 1. Graph Store
- **Purpose:** Store code/doc structure and relationships
- **Technology:** SQLite with custom schema
- **Nodes:** 1055 (files, functions, classes, chunks)
- **Edges:** 1215 (calls, imports, defines relationships)
- **Status:** ✓ Operational

### 2. Vector Index
- **Purpose:** Semantic similarity search
- **Technology:** HNSW (Hierarchical Navigable Small World)
- **Model:** `nomic-embed-text` (768-dim) via Ollama
- **Cache:** 21MB, 7161 entries
- **Status:** ✓ Operational (but no live API key for new embeddings)

### 3. Chunker
- **Purpose:** Split docs into retrievable units
- **Status:** ⚠ Service unreachable
- **Fallback:** Files can still be indexed if pre-chunked

### 4. REST API
- **Endpoints:** `/query`, `/index`, `/health`, `/graph`
- **Port:** 7474
- **Status:** ✓ Operational

---

## Agent Workflow

Before code changes:
1. **Check handoff state** (read `/AGENT_HANDOFF.md`)
2. **Query RAGD** for task-specific context
3. **Inspect files** after understanding context
4. **Make changes** with minimal diff
5. **Validate** with tests

After significant work:
- Update handoff/docs
- Re-index if docs changed: `dominion scan`

---

## Common Queries

| Query | Expected Top Result |
|---|---|
| "agent workflow" | `AGENT_OPERATING_SYSTEM.md` |
| "safety rules" | `AGENT_SAFETY_RULES.md` |
| "data pipeline architecture" | `DATA_FLOW.md`, `DATA_PIPELINE.md` |
| "how RAGD works" | `RAGD_OVERVIEW.md` (this doc) |
| "coding standards" | `CODING_STANDARDS.md` |
| "testing strategy" | `TESTING_GUIDE.md` |

---

## Failure Modes & Fixes

| Symptom | Cause | Fix |
|---|---|---|
| Query returns 0 results | Stale index | Run `dominion scan` |
| Query returns wrong docs | Poor query specificity | Make query more specific or add filters |
| `/query` returns 500 | RAGD daemon down | Check `curl 127.0.0.1:7474/health` |
| Embedding errors | No API key | Set `RAGD_EMBED_API_KEY` or use cached embeddings |
| Chunker unreachable | Service not running | Start chunker service or use static chunking |

---

## Performance

- **Query latency:** <50ms (HNSW search)
- **Index latency:** ~200ms per file (with embedding)
- **Storage:** ~22MB for 7161 chunks
- **Memory:** ~100MB resident
- **Startup:** <1s

---

## Validation Commands

```bash
# Check RAGD health
curl http://127.0.0.1:7474/health

# Run doctor check
python scripts/dominion_cli.py doctor --json

# Check embedding coverage
python scripts/dominion_cli.py embed stats --json

# Run retrieval tests (if available)
python -m pytest -q dominion_ai/tests/test_eval.py
```

---

## Related Docs

- [RAGD_AGENT_USAGE.md](RAGD_AGENT_USAGE.md) — How agents use RAGD
- [RAGD_INDEXING_STRATEGY.md](RAGD_INDEXING_STRATEGY.md) — What to index and when
- [RAGD_QUERY_PATTERNS.md](RAGD_QUERY_PATTERNS.md) — Effective query patterns
- [RAGD_CHUNKING_GUIDE.md](RAGD_CHUNKING_GUIDE.md) — Document splitting strategies
- [RAGD_METADATA_SCHEMA.md](RAGD_METADATA_SCHEMA.md) — Metadata format
- [RAGD_INGESTION_MANIFEST.md](../RAGD_INGESTION_MANIFEST.md) — Priority and chunking rules

---

## Future Enhancements

- WebSocket support (planned, not yet implemented)
- Multi-level indexing (file → section → paragraph)
- Semantic clustering (group related docs)
- Auto-reindexing on file change
- Query rewriting (expand synonyms)
- Cross-reference validation (check `[[links]]`)

---

## Retrieval Hints

Queries that should find this doc:
- "RAGD overview"
- "how does RAGD work"
- "RAGD architecture"
- "memory system overview"
- "what is RAGD"
