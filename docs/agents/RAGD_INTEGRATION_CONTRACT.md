# RAGD Integration Contract

**Producer:** `dominion_loader.ragd_bridge.RagdBridge`  
**Consumer:** RAGD C++ daemon (`ragd/src/http_api.cpp`)  
**Protocol version:** 1 (RAGD schema as of 2026-05-13)

---

## Architecture

```
dominion_loader/scan.py  →  RagdBridge  →  POST /index  →  RAGD indexer.cpp
                                                          ↓
                                                     chunks table (WAL)
```

The loader is a **producer**: it tells RAGD which paths to index. RAGD owns:
- The chunking strategy (`ragd/src/indexer.cpp`)
- The `should_ignore()` logic (`ragd/src/indexer.cpp` and `ragd/src/config.cpp`)
- The chunk deduplication (`(filepath, line_start, line_end, content_hash)`)
- The FTS index (`fts_chunks` virtual table)
- The vector embedding backend

---

## API Contract

### `POST /index`

**Request:**
```json
{
  "paths": ["/absolute/path/to/file1.py", "/absolute/path/to/file2.md"]
}
```

**Response (success):**
```json
{
  "chunks_indexed": 42,
  "already_current": 7,
  "queued": 49
}
```

**Response (error):**
```json
{
  "error": "...",
  "chunks_indexed": 0
}
```

### `GET /health`

**Response:**
```json
{
  "status": "ok",
  "active_chunks": 12345,
  "todos": 0,
  "embed_backend": "local"
}
```

---

## RAGD Schema (read-only from loader)

```sql
-- Loader reads this table only (no writes)
chunks(
    id INTEGER PRIMARY KEY,
    filepath TEXT,
    lang TEXT,
    chunk_type TEXT,    -- "function"|"class"|"section"|...
    symbol_name TEXT,
    line_start INTEGER,
    line_end INTEGER,
    content TEXT,
    content_hash TEXT,  -- RAGD's sha256ish() (std::hash<string>), NOT real SHA256
    metadata_json TEXT,
    status TEXT,        -- "active"|"deleted"
    created_at INTEGER,
    updated_at INTEGER
)
```

**CRITICAL:** `content_hash` in RAGD is computed by `sha256ish()` in `ragd/src/storage.cpp` using `std::hash<string>`. This is NOT a real SHA256 digest. Do NOT compare with `dominion_loader` `content_hash` values.

---

## Deduplication

RAGD deduplicates by `(filepath, line_start, line_end, content_hash)`. Unchanged content (same RAGD `content_hash`) will NOT create a new row. This is why the bridge's `already_current` count may exceed `chunks_indexed` on rescans.

---

## Batching Policy

- Default batch size: 50 paths per request
- Max retries: 2 (with 0.5s * attempt backoff)
- Timeout: 30 seconds per request
- Feature flag: `DOMINION_RAGD_BRIDGE=off` disables all requests

---

## Error Handling

On network error, the bridge stops the current batch and records `error` in `IngestResult`. The manifest does NOT mark files as `ragd_ingested` on failure. On the next scan, they will be resubmitted.

---

## Security

- The bridge submits absolute local filesystem paths only
- No secrets paths are ever submitted (Ignore prevents discovery)
- No authentication required for `127.0.0.1:7474` (local loopback only)
- RAGD_URL defaults to `http://127.0.0.1:7474` — never a public endpoint

---

## Invariants

1. Loader never directly writes to RAGD's SQLite (`~/.ragd/ragd.db`)
2. Loader reads RAGD's DB directly only for `ingest_from_ragd()` (knowledge graph build)
3. RAGD's `should_ignore()` is a secondary filter; loader's `Ignore` runs first
4. `document_id` in loader manifest ≠ RAGD `chunk.id` — separate ID spaces
