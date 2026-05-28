# RAGD REST API Reference

**Status:** LIVE_GREEN (Production API, port 7474)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Base URL:** `http://127.0.0.1:7474`

---

## Overview

RAGD REST API provides HTTP endpoints for:
- Semantic search (query codebase)
- Document indexing (add/update/delete files)
- Session management (agent lifecycle tracking)
- Memory storage (decisions, TODOs, dead zones)
- Temporal queries (code history, chunk diffs)

**Protocol:** HTTP/1.1 (no TLS)  
**Format:** JSON request/response  
**Authentication:** None (localhost only)

---

## Health & Metrics

### `GET /health`

Health check with system metrics.

**Response:**
```json
{
  "ok": true,
  "status": "ok",
  "active_chunks": 9024,
  "chunks": 10716,
  "sessions": 0,
  "todos": 18,
  "decisions": 18,
  "dead_zones": 0,
  "bus_messages": 1,
  "embed_backend": "external_hnsw",
  "ragd_version": "1.0.0",
  "retrieval_latency_ms": {
    "p50": 0,
    "p95": 0,
    "p99": 0
  }
}
```

**Fields:**
- `ok` — true if storage health check passes
- `active_chunks` — non-deleted chunks
- `chunks` — total chunks (including deleted)
- `retrieval_latency_ms` — query latency percentiles (0 if no recent queries)

---

### `GET /metrics`

Detailed metrics JSON (same as `/health` but with extended stats).

---

## Query

### `POST /query`

Unified query endpoint (BM25 + keyword, hybrid mode default).

**Request:**
```json
{
  "q": "Kalman filter fusion",
  "query": "Kalman filter fusion",  // alias
  "mode": "hybrid",  // "hybrid" | "bm25" | "keyword"
  "top_k": 5,
  "limit": 5  // alias
}
```

**Response:**
```json
{
  "elapsed_ms": 97,
  "mode": "hybrid",
  "query": "",
  "query_intent": "general",
  "results": [
    {
      "chunk_id": 10699,
      "document_id": "8d000eecff81cfa4",
      "filepath": "/home/Martin/Dominion/toxicity/cli.py",
      "relative_path": "toxicity/cli.py",
      "content": "\"\"\"Toxicity monitor CLI.\"\"\"\nimport sys...",
      "chunk_type": "block",
      "line_start": 1,
      "line_end": 10,
      "language": "python",
      "score": 1.0,
      "score_breakdown": {
        "bm25": 0.0,
        "rrf": 0.01282051282051282,
        "vector": 0.0,
        "total": 1.0
      },
      "bm25_score": 0.0,
      "rrf_score": 0.01282051282051282,
      "is_public": true,
      "docstring": "",
      "parent_symbol": "",
      "qualified_name": "top_level",
      "imports": ["sys", "duckdb", "pandas", ...],
      "calls": [],
      "git_commit": "2d0b44515fd425cff1c363513713a13f4e544d2b",
      "indexed_at": 1779228188,
      "modified_at": 1779221956,
      "content_hash": "04ce9b482ea2d9a5b3518456014565b35fb8e1fdaa2fe0ca27665730a26ff0ff",
      "source_subsystem": "ragd",
      "repo_root": "/home/Martin/Dominion"
    }
  ]
}
```

**Modes:**
- `hybrid` — BM25 + RRF (reciprocal rank fusion) (default)
- `bm25` — BM25 only (term frequency ranking)
- `keyword` — Keyword match only (no ranking)

**Note:** HNSW semantic search available via `/query/semantic` when external service configured.

---

### `POST /query/semantic`

Semantic search via HNSW vector index (requires external service).

**Request:**
```json
{
  "q": "error handling in pipeline",
  "top_k": 10
}
```

**Response:** Same format as `/query`

**Requirements:**
- `ragd_hnsw` service running (port 7476)
- Embeddings generated (`nomic-embed-text`)
- HNSW index built

**Error (503 if service unavailable):**
```json
{
  "ok": false,
  "error": "semantic query service unavailable",
  "remedy": "Start python -m ragd_hnsw.semantic_server after embeddings and HNSW sync are available."
}
```

---

### `POST /query/hybrid`

Hybrid query (BM25 + keyword). Same as `/query` with `mode=hybrid`.

**Note:** Header `X-RAGD-Semantic-Note` explains HNSW availability.

---

## Indexing

### `POST /index`

Index files or directories.

**Request:**
```json
{
  "path": "/home/Martin/Dominion/data_pipeline",  // single path
  "paths": ["/path/1", "/path/2"]  // or multiple paths
}
```

**Response:**
```json
{
  "queued": 42,
  "chunks_indexed": 42,
  "already_current": 0
}
```

**Behavior:**
- Scans paths recursively
- Skips files >1MB (configurable)
- Rebuilds HNSW vector index after completion
- Idempotent (skips unchanged files based on content hash)

---

### `POST /index/delete`

Mark files/chunks as deleted (soft delete).

**Request:**
```json
{
  "path": "/home/Martin/Dominion/old_file.py",
  "paths": ["/path/1", "/path/2"]
}
```

**Response:**
```json
{
  "ok": true,
  "paths_submitted": 2,
  "files_marked_deleted": 2,
  "chunks_marked_deleted": 12,
  "errors": []
}
```

**Response (errors):**
```json
{
  "ok": false,
  "paths_submitted": 2,
  "files_marked_deleted": 1,
  "chunks_marked_deleted": 6,
  "errors": [
    {
      "path": "/nonexistent",
      "error": "file not found"
    }
  ]
}
```

**Behavior:**
- Marks chunks as deleted (not removed from DB)
- Rebuilds HNSW vector index after completion
- Deleted chunks excluded from query results

---

## Sessions

### `POST /session/start`

Start agent session.

**Request:**
```json
{
  "agent_name": "claude-sonnet-4",
  "agent": "claude-sonnet-4",  // alias
  "git_branch": "main",
  "parent_session": "sess_abc123"
}
```

**Response:**
```json
{
  "session_id": "sess_def456",
  "started_at": "2026-05-19T18:30:00Z"
}
```

---

### `POST /session/end`

End agent session.

**Request:**
```json
{
  "session_id": "sess_def456",
  "summary": "Completed feature X",
  "handoff_note": "Next: test coverage",
  "status": "completed"  // "completed" | "failed" | "abandoned"
}
```

**Response:**
```json
{
  "ok": true
}
```

---

### `GET /session/active`

List active sessions.

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "sess_abc123",
      "agent_name": "claude-sonnet-4",
      "started_at": "2026-05-19T17:00:00Z",
      "status": "active",
      "git_branch": "main"
    }
  ]
}
```

---

### `GET /session/:session_id`

Get session details.

**Example:** `GET /session/sess_abc123`

**Response:**
```json
{
  "session_id": "sess_abc123",
  "agent_name": "claude-sonnet-4",
  "status": "active",
  "started_at": "2026-05-19T17:00:00Z",
  "ended_at": null,
  "git_branch": "main",
  "summary": "",
  "handoff_note": ""
}
```

---

### `POST /session/touch`

Record file touch event (agent read/wrote file).

**Request:**
```json
{
  "session_id": "sess_abc123",
  "filepath": "/home/Martin/Dominion/data_pipeline/pipeline.py",
  "action": "edit",  // "analyze" | "edit" | "create" | "delete"
  "note": "Added error handling"
}
```

**Response:**
```json
{
  "ok": true
}
```

---

## Memory (Decisions)

### `POST /memory/decision`

Store decision (architectural choice, tradeoff, rationale).

**Request:**
```json
{
  "session_id": "sess_abc123",
  "decision": "Use Kalman filter for price fusion",
  "text": "Use Kalman filter for price fusion",  // alias
  "filepath": "data_pipeline/fusion/kalman.py",
  "rationale": "Handles noisy data better than simple average",
  "alternatives": ["Simple average", "Median"],
  "tags": ["architecture", "data-pipeline"]
}
```

**Response:**
```json
{
  "id": 42,
  "decision_id": 42,
  "stored": true
}
```

---

### `GET /memory/decisions`

List recent decisions.

**Query Params:**
- `limit` — max results (default: 20)

**Example:** `GET /memory/decisions?limit=10`

**Response:**
```json
{
  "decisions": [
    {
      "id": 42,
      "session_id": "sess_abc123",
      "filepath": "data_pipeline/fusion/kalman.py",
      "decision": "Use Kalman filter for price fusion",
      "rationale": "Handles noisy data better than simple average",
      "created_at": "2026-05-19T17:30:00Z"
    }
  ]
}
```

---

## TODOs

### `GET /todos`

List TODOs filtered by status/priority/kind.

**Query Params:**
- `status` — "open" | "in_progress" | "done" | "wont_fix" (default: "open")
- `priority` — max priority (1-10, default: 99)
- `kind` — "TODO" | "FIXME" | "HACK" | "XXX" (default: all)
- `limit` — max results (default: 50)

**Example:** `GET /todos?status=open&priority=5&limit=20`

**Response:**
```json
{
  "todos": [
    {
      "id": 1,
      "todo_id": 1,
      "filepath": "data_pipeline/pipeline.py",
      "line_number": 42,
      "kind": "TODO",
      "content": "Add retry logic for failed source fetch",
      "priority": 3,
      "status": "open",
      "assigned_to": "",
      "symbol_name": "fetch_sources"
    }
  ]
}
```

---

### `POST /todos`

Create TODO.

**Request:**
```json
{
  "filepath": "data_pipeline/pipeline.py",
  "line_number": 42,
  "line": 42,  // alias
  "kind": "TODO",
  "tag": "TODO",  // alias
  "content": "Add retry logic",
  "text": "Add retry logic",  // alias
  "priority": 3,
  "status": "open",
  "assigned_to": "claude",
  "symbol_name": "fetch_sources",
  "tags": ["data-pipeline", "error-handling"]
}
```

**Response:**
```json
{
  "todo_id": 42
}
```

---

### `PATCH /todos/:id`

Update TODO.

**Example:** `PATCH /todos/42`

**Request:**
```json
{
  "status": "done",
  "assigned_to": "claude",
  "priority": 1
}
```

**Response:**
```json
{
  "ok": true
}
```

---

### `GET /todos/search`

Search TODOs via hybrid query.

**Query Params:**
- `q` — query string
- `limit` — max results (default: 10)

**Example:** `GET /todos/search?q=error%20handling&limit=5`

**Response:** Same format as `/query` (returns chunks matching TODO content)

---

## Handoff

### `GET /handoff`

Get AGENT_HANDOFF.md content + active sessions.

**Response:**
```json
{
  "content": "# Agent Handoff\n\n...",
  "active_sessions": [
    {
      "session_id": "sess_abc123",
      "agent_name": "claude-sonnet-4",
      "status": "active"
    }
  ]
}
```

---

## Temporal Queries

### `GET /temporal/commits`

List recent git commits with indexed files.

**Query Params:**
- `limit` — max commits (default: 20)

**Example:** `GET /temporal/commits?limit=10`

**Response:**
```json
{
  "commits": [
    {
      "git_commit": "2d0b44515fd425cff1c363513713a13f4e544d2b",
      "message": "feat: add Kalman fusion",
      "author": "MatinDeevv",
      "timestamp": "2026-05-19T10:00:00Z",
      "files_changed": 3
    }
  ]
}
```

---

### `POST /temporal/query`

Query code at specific git commit.

**Request:**
```json
{
  "q": "Kalman filter",
  "query": "Kalman filter",  // alias
  "git_commit": "2d0b44515fd425cff1c363513713a13f4e544d2b",
  "top_k": 5
}
```

**Response:** Same format as `/query` but filtered to chunks from specified commit

---

### `GET /temporal/file-timeline`

Get file change timeline (all commits touching file).

**Query Params:**
- `filepath` — absolute or relative path

**Example:** `GET /temporal/file-timeline?filepath=data_pipeline/pipeline.py`

**Response:**
```json
{
  "filepath": "data_pipeline/pipeline.py",
  "commits": [
    {
      "git_commit": "abc123",
      "timestamp": "2026-05-19T10:00:00Z",
      "message": "Add Kalman fusion",
      "chunks_changed": 3
    }
  ]
}
```

---

### `GET /temporal/diff`

Semantic chunk diff (requires two versions).

**Response (not implemented):**
```json
{
  "diff": [],
  "mode": "chunk_history",
  "note": "semantic chunk diff requires two recorded versions"
}
```

---

### `GET /temporal/chunk-diff`

Chunk-level diff (same as `/temporal/diff`).

---

## Dead Zones

### `POST /deadzone/scan`

Scan for dead code (unreachable, unused).

**Request:**
```json
{
  "path": "/home/Martin/Dominion/data_pipeline"
}
```

**Response:**
```json
{
  "job_id": "inline",
  "status": "completed",
  "stored": 5
}
```

**Behavior:**
- Scans for unused imports, unreachable code, unused functions
- Stores findings in `dead_zones` table
- Returns immediately (inline scan, not async)

---

### `GET /deadzone/results`

List dead zones.

**Query Params:**
- `acknowledged` — "true" to include acknowledged dead zones

**Example:** `GET /deadzone/results?acknowledged=false`

**Response:**
```json
{
  "dead_zones": [
    {
      "id": 1,
      "filepath": "data_pipeline/old_utils.py",
      "kind": "unused_function",
      "symbol_name": "old_helper",
      "detail": "Function never called",
      "confidence": 0.9,
      "acknowledged": false,
      "created_at": "2026-05-19T17:00:00Z"
    }
  ]
}
```

---

## Bus (Internal)

### `GET /bus/locks`

List active locks (internal feature for conflict detection).

**Response:**
```json
{
  "locks": []
}
```

**Note:** Experimental feature, not fully implemented.

---

## Error Handling

### Error Response Format

```json
{
  "error": "error message",
  "code": 500
}
```

**HTTP Status Codes:**
- `200` — Success
- `400` — Bad request (invalid JSON, missing required fields)
- `404` — Not found (resource doesn't exist)
- `500` — Internal server error (exception in handler)
- `503` — Service unavailable (e.g., semantic search service down)

---

## Rate Limiting

**None.** RAGD runs on localhost with no auth — callers trusted.

---

## Examples

### Index repo and query

```bash
# Index entire repo
curl -X POST http://127.0.0.1:7474/index \
  -H "Content-Type: application/json" \
  -d '{"path": "/home/Martin/Dominion"}'

# Query
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q": "Kalman filter", "top_k": 5}' | jq .
```

---

### Session tracking

```bash
# Start session
SESSION=$(curl -s -X POST http://127.0.0.1:7474/session/start \
  -H "Content-Type: application/json" \
  -d '{"agent_name": "claude"}' | jq -r .session_id)

# Touch file
curl -X POST http://127.0.0.1:7474/session/touch \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"filepath\": \"data_pipeline/pipeline.py\", \"action\": \"edit\"}"

# End session
curl -X POST http://127.0.0.1:7474/session/end \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"status\": \"completed\", \"summary\": \"Fixed bug X\"}"
```

---

### Create decision + TODO

```bash
# Store decision
curl -X POST http://127.0.0.1:7474/memory/decision \
  -H "Content-Type: application/json" \
  -d '{"session_id": "sess_abc", "decision": "Use DuckDB for feature storage", "rationale": "Faster than SQLite for analytical queries", "filepath": "data_pipeline/features/store.py"}'

# Create TODO
curl -X POST http://127.0.0.1:7474/todos \
  -H "Content-Type: application/json" \
  -d '{"filepath": "data_pipeline/pipeline.py", "line": 42, "content": "Add retry logic", "priority": 3, "kind": "TODO"}'

# List open TODOs
curl http://127.0.0.1:7474/todos?status=open | jq .
```

---

## Performance

| Endpoint | Typical Latency | Notes |
|----------|----------------|-------|
| `/health` | <5ms | Simple DB query |
| `/query` (BM25) | 10-50ms | Depends on index size |
| `/query/semantic` | 50-200ms | Depends on HNSW index + embedding cache |
| `/index` | 1-60s | Depends on file count |
| `/session/*` | <10ms | Simple DB writes |
| `/memory/decision` | <10ms | Simple DB write |
| `/todos` | 10-30ms | DB query with filters |

---

## Security Notes

**Localhost Only:** RAGD binds to `127.0.0.1` (not `0.0.0.0`) — not exposed to network.

**No TLS:** HTTP only (acceptable for localhost).

**No Authentication:** Trusted local callers only.

**Input Validation:** JSON parsing validates structure but not semantics. Malicious JSON can crash server (exception handler returns 500).

**Path Traversal:** `/index` and `/index/delete` accept absolute paths — caller can access any file readable by RAGD process. No sandboxing.

**DoS:** No rate limiting — caller can spam requests.

---

## Client Libraries

**Python:**
```python
import requests

# Query
response = requests.post("http://127.0.0.1:7474/query", json={"q": "Kalman", "top_k": 5})
results = response.json()["results"]

# Index
requests.post("http://127.0.0.1:7474/index", json={"path": "/path/to/code"})
```

**Bash (curl):**
```bash
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q": "error handling", "top_k": 10}'
```

**JavaScript (fetch):**
```javascript
const response = await fetch("http://127.0.0.1:7474/query", {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify({q: "Kalman filter", top_k: 5})
});
const data = await response.json();
```

---

## Related

- [RAGD_ARCHITECTURE.md](../01_ARCHITECTURE/RAGD_ARCHITECTURE.md) — RAGD internals
- [DEPLOYMENT_DIAGRAM.md](../01_ARCHITECTURE/DEPLOYMENT_DIAGRAM.md) — RAGD deployment
- [MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md) — MCP tools wrapping REST API

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All endpoints tested via curl + live RAGD instance (port 7474)
