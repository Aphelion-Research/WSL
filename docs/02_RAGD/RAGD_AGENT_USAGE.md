---
doc_type: ragd
system: RAGD
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - ragd
  - retrieval
---

# RAGD AGENT USAGE

**Status:** LIVE_GREEN (RAGD daemon running on 127.0.0.1:7474)

## Purpose

RAGD (Retrieval-Augmented Graph Database) is Dominion's persistent memory system.

This doc covers: ragd agent usage

## Current State

- 7159 active chunks
- 8760 total chunks
- SQLite + HNSW vector index
- Native C++ implementation (24/24 tests passing)
- REST API on 127.0.0.1:7474
- MCP support
- Bus system for agent coordination

## Key Operations

```bash
# Query RAGD
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{"q":"<query>","top_k":5}'

# Index files
curl -X POST http://127.0.0.1:7474/index \
  -H 'Content-Type: application/json' \
  -d '{"path":"<path>","content":"<content>"}'

# Health check
curl http://127.0.0.1:7474/health
```

## Agent Usage

Agents MUST query RAGD before code changes:

```python
# Python
from ragd.scripts.ragd_mcp_stdio import ragd_query
result = ragd_query("<task description>", top_k=5)

# CLI
python scripts/dominion_cli.py search "<query>" --top-k 5 --json
```

## Indexing Strategy

- **heading-based chunking:** Split markdown by ## headers
- **semantic chunking:** AST-aware for code
- **metadata extraction:** Frontmatter → filter/boost
- **priority tiers:** P10 docs indexed first

See RAGD_INGESTION_MANIFEST.md for full strategy.

## Query Patterns

Best practices:
- Use task-specific queries ("how to add feature" not "code")
- Include context ("data pipeline feature implementation")
- Check top 5-10 results
- Verify metadata (doc_type, status, last_reviewed)

## Common Queries

| Query | Expected Result |
|---|---|
| "agent workflow" | AGENT_OPERATING_SYSTEM.md |
| "safety rules" | AGENT_SAFETY_RULES.md |
| "data pipeline" | DATA_PIPELINE_FEATURE.md |
| "how RAGD works" | RAGD_OVERVIEW.md |

## Failure Modes

- **Stale chunks:** Re-run `dominion scan`
- **Missing embeddings:** Set `RAGD_EMBED_API_KEY` + run `dominion embed run`
- **Poor retrieval:** Check query specificity, verify metadata
- **Daemon down:** Check `curl 127.0.0.1:7474/health`

## Validation

```bash
# Check RAGD health
curl http://127.0.0.1:7474/health

# Run retrieval tests
python -m pytest -q dominion_ai/tests/test_eval.py

# Check embedding coverage
python scripts/dominion_cli.py embed stats --json
```

## Future Enhancements

- WebSocket support (in progress)
- Multi-level indexing
- Semantic clustering
- Auto-reindexing on file change
- Query rewriting
- Cross-reference validation

## Related Docs

- [RAGD_INGESTION_MANIFEST.md](../RAGD_INGESTION_MANIFEST.md)
- [01_ARCHITECTURE/DATA_FLOW.md](../01_ARCHITECTURE/DATA_FLOW.md)
- [03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md](../03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md)

## Retrieval Hints

- "RAGD"
- "retrieval"
- "indexing"
- "query"
- "how to use memory system"
