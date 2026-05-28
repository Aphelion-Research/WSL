---
doc_type: roadmap
system: Dominion
ragd_priority: 5
audience:
  - maintainer
  - owner
status: complete
last_reviewed: 2026-05-19
tags:
  - roadmap
  - phase-0
  - foundation
---

# Phase 0: Foundation (Complete)

**Timeline:** Q4 2024 - Q1 2025 (3 months)  
**Status:** ✓ Complete

---

## Goals

1. Build local-first infrastructure
2. Establish RAGD memory system
3. MT5 read-only bridge
4. Agent OS foundation
5. Testing + safety framework

---

## Deliverables

### Core Infrastructure
- [x] WSL/Debian environment setup
- [x] Git repository initialized
- [x] Python venv + dependencies
- [x] CMake build system (for native core)

### RAGD System
- [x] SQLite + HNSW vector store
- [x] REST API (127.0.0.1:7474)
- [x] Document chunking (AST-aware)
- [x] Embedding pipeline
- [x] Basic retrieval (BM25 + semantic)

### domdata (MT5 Bridge)
- [x] Wine/MT5 integration
- [x] Read-only investor account
- [x] Forbidden token scanner
- [x] CLI wrapper (`domdata xautick`, `xaurates`)
- [x] Safety validation (no trading)

### Agent OS
- [x] SQLite-backed session management
- [x] File locking system
- [x] Safety rules enforcement
- [x] Task tracking

### Testing Framework
- [x] pytest setup
- [x] CTest setup (C++)
- [x] Trading safety check script
- [x] Platform health check (doctor)

---

## Timeline

| Milestone | Date | Status |
|---|---|---|
| Repository created | 2024-10-15 | ✓ |
| RAGD prototype | 2024-11-01 | ✓ |
| MT5 connection working | 2024-11-20 | ✓ |
| domdata CLI operational | 2024-12-01 | ✓ |
| Agent OS MVP | 2024-12-15 | ✓ |
| First tests passing | 2025-01-10 | ✓ |
| Phase 0 complete | 2025-01-31 | ✓ |

---

## Dependencies

**External:**
- WSL2 available
- MT5 terminal + login credentials
- OpenAI API key (for embeddings)

**Internal:**
- None (greenfield)

---

## Success Criteria

- [x] RAGD daemon runs stable (>24h uptime)
- [x] MT5 ticks flow to domdata CLI
- [x] Trading check passes (no forbidden tokens)
- [x] Agent can query RAGD, get context
- [x] All baseline tests pass (10+ tests)

---

## Key Decisions (ADRs)

- [[ADR_0001_sqlite_over_postgres]] — SQLite for RAGD storage
- [[ADR_0002_native_cpp_scan_over_python]] — Native C++ file scanning
- ADR_0007 — Read-only MT5 architecture (planned doc)

---

## Blockers Encountered

1. **Wine/MT5 stability** (Resolved)
   - MT5 crashed frequently under Wine
   - Solution: Investor account + manual restart script

2. **HNSW performance** (Resolved)
   - Initial Python HNSW too slow
   - Solution: Native C++ integration via sqlite-vss

3. **Agent OS complexity** (Resolved)
   - First design too heavyweight
   - Solution: Simplified to SQLite + minimal API

---

## Metrics

- **Code:** 5K Python LOC, 500 C++ LOC
- **Tests:** 10 passing
- **Docs:** 15 files
- **RAGD chunks:** 500
- **Uptime:** RAGD stable >48h

---

## Lessons Learned

**What worked:**
- SQLite excellent choice (simple, reliable)
- Native C++ for hot paths worth it
- Forbidden token scanner caught issues early
- tmux sessions for daemon management

**What struggled:**
- Wine/MT5 integration fragile
- Documentation lagged code
- Test coverage low initially

---

## Next Phase

→ [[PHASE_1]] — Data Pipeline MVP (single source)
