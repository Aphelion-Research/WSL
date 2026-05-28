---
doc_type: adr
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
  - owner
status: accepted
last_reviewed: 2026-05-19
tags:
  - decision
  - adr
  - ragd
  - database
---

# ADR 0001: SQLite Over PostgreSQL for RAGD

**Status:** Accepted  
**Date:** 2024-12-15  
**Decision ID:** ADR_0001  

**History:**
- 2024-12-15: Proposed
- 2024-12-16: Accepted
- 2026-05-19: Documented

---

## Context

RAGD requires persistent storage for:
- Document chunks (~10K chunks expected)
- Metadata (frontmatter, tags, hashes)
- Embeddings (768-dim vectors)
- Graph relationships (handoffs, references)

### Problem Statement

Need database that supports:
- ACID transactions
- Full-text search
- Vector similarity search (via HNSW extension)
- File-based (no separate daemon)
- Low operational overhead
- Fast reads for retrieval

### Constraints

- Must run on WSL/Debian
- Local-first architecture (no cloud dependencies)
- Single-user system (Matin primary, Dan occasional)
- Must survive process crashes
- Must support 100K+ chunks eventually

### Assumptions

- Concurrent writes low (<10 per minute)
- Reads dominant (90%+ workload)
- No distributed access needed
- Owner can manage schema migrations manually

### Current Situation

Building RAGD from scratch. No legacy database constraints.

---

## Decision

**Use SQLite for RAGD storage, not PostgreSQL.**

### Key Points

1. **File-based storage** — Single .db file, no daemon process
2. **HNSW extension** — sqlite-vss provides vector search
3. **FTS5 module** — Built-in full-text search
4. **ACID guarantees** — Same durability as PostgreSQL for single-user
5. **Zero admin** — No pg_ctl, no config tuning, no vacuum management
6. **Embeddable** — Native C++ integration via sqlite3.h

---

## Consequences

### Positive

- **Zero operational overhead** — No daemon to monitor/restart
- **Simple backup** — Copy .db file, done
- **Fast startup** — No connection pooling overhead
- **Small footprint** — ~600KB binary vs 50MB+ for PostgreSQL
- **Native C++ integration** — Direct sqlite3_* API calls
- **Perfect for local-first** — Aligns with sovereign infrastructure principle
- **Easy testing** — In-memory mode for fast test suite

### Negative

- **Single-writer limitation** — Only one process can write at a time (acceptable for single-user)
- **No built-in replication** — Must implement backup strategy manually
- **Vector search extension immature** — sqlite-vss less mature than pgvector
- **Limited concurrency** — Not suitable if system scales to multi-user (not planned)

### Neutral

- **Schema migrations manual** — Acceptable, we control all schema changes
- **No procedural language** — All logic in C++/Python (preferred anyway)

---

## Alternatives Considered

### Alternative 1: PostgreSQL + pgvector

**Description:** Industry-standard RDBMS with mature vector extension.

**Pros:**
- Mature, battle-tested
- pgvector well-supported
- Better concurrency
- Stored procedures available

**Cons:**
- Requires daemon process
- Operational overhead (monitoring, backups, vacuuming)
- Connection pooling complexity
- Overkill for single-user system
- Against local-first principle (feels like server architecture)

**Why Rejected:** Operational complexity outweighs concurrency benefits for single-user system.

### Alternative 2: DuckDB

**Description:** In-process analytical database optimized for OLAP.

**Pros:**
- File-based, no daemon
- Excellent for analytical queries
- Growing ecosystem
- Good Python integration

**Cons:**
- No vector similarity search extension
- OLAP-optimized, not OLTP (RAGD needs transactional writes)
- Immature for production use (as of 2024)
- No C++ HNSW library integration

**Why Rejected:** Lack of vector search support + OLAP focus mismatches RAGD workload.

### Alternative 3: Embedded key-value store (RocksDB, LMDB)

**Description:** Low-level key-value storage.

**Pros:**
- Extremely fast
- Minimal overhead
- Battle-tested (RocksDB from Facebook)

**Cons:**
- No SQL, must build indexes manually
- No FTS, must implement search manually
- No vector search, must integrate HNSW manually
- Low-level API increases development time

**Why Rejected:** Would require building relational layer + FTS + vector search from scratch. SQLite provides all three.

---

## Implementation

### Affected Components

- `ragd/` (C++ native core)
- `ragd_embed/` (embedding pipeline writes to SQLite)
- `ragd_hnsw/` (vector index backed by SQLite)
- `dominion_ai/` (RAG retrieval queries SQLite)
- `ragd_graph/` (graph memory writes to SQLite)

### Migration Path

N/A (greenfield implementation)

### Effort Estimate

- SQLite schema design: 2 days
- HNSW integration (sqlite-vss): 3 days
- FTS5 setup: 1 day
- C++ API wrapper: 2 days
- Python bindings: 1 day
- **Total:** ~9 days (completed)

### Breaking Changes

None (initial implementation)

---

## Validation

### Success Criteria

- [x] 10K chunks indexed without performance degradation
- [x] Full-text search returns results <100ms
- [x] Vector similarity search <200ms (top-10)
- [x] Database survives process crash without corruption
- [x] Backup/restore workflow tested

### Monitoring Metrics

```bash
# Database size
du -h data/ragd.db

# Query performance
sqlite3 data/ragd.db "EXPLAIN QUERY PLAN SELECT * FROM chunks WHERE ..."

# Integrity check
sqlite3 data/ragd.db "PRAGMA integrity_check;"
```

### Current Status

- **7,159 active chunks** indexed (2026-05-19)
- **8,760 total chunks** (includes soft-deleted)
- **Query performance:** <50ms for FTS, <100ms for vector search
- **Zero corruption events**
- **Backup strategy:** Manual .db file copy (working)

---

## Follow-Up Work

- [ ] Implement automated backup (daily snapshot to backups/)
- [ ] Add WAL mode benchmarks (vs default journal mode)
- [ ] Test 100K chunk scaling
- [ ] Document schema migration process
- [ ] Add VACUUM automation (monthly)

---

## Related Decisions

- [[ADR_0002_native_cpp_scan_over_python]] — Native C++ scan complements SQLite file-based approach
- Future: ADR for HNSW index tuning strategy

---

## References

- SQLite documentation: https://sqlite.org/docs.html
- sqlite-vss (vector extension): https://github.com/asg017/sqlite-vss
- FTS5 documentation: https://sqlite.org/fts5.html
- Local-first principles: https://www.inkandswitch.com/local-first/

---

## Retrieval Hints

- "why sqlite"
- "database choice"
- "ragd storage"
- "sqlite vs postgres"
- "vector database decision"
