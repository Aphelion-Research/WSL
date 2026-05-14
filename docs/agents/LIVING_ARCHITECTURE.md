# Living Architecture — Dominion Agent OS

*Auto-generated: 2026-05-13T23:25:31Z*
*git: `main` @ `5fb729e`  *(dirty)**

> This document is generated from codebase scan + live Agent OS state.
> Do NOT manually edit — run `dominion agent architecture refresh` to update.

---

## Agent OS Live State

| Metric | Value |
|---|---|
| Active Sessions | 1 |
| Open Tasks | 0 |
| Active File Locks | 0 |

---

## Open Tasks

*(no open tasks)*

---

## Active File Locks

*(no active locks)*

---

## Package Registry

| Package | Description | Status | Primary API | Depends On |
|---|---|---|---|---|
| `dominion_loader` | File manifest scanner and loader | ✅ present | `dominion_loader/api.py` | none |
| `dominion_ai` | RAGD-backed AI query layer | ✅ present | `dominion_ai/api.py` | dominion_loader, ragd |
| `dominion_agent` | Agent OS — session/task/lock/review control plane | ✅ present | `dominion_agent/api.py` | none |
| `ragd_embed` | External embedding pipeline | ✅ present | `ragd_embed/__init__.py` | ragd |
| `ragd_hnsw` | Persistent semantic index | ✅ present | `ragd_hnsw/__init__.py` | ragd_embed |
| `ragd_chunker` | AST chunking service | ✅ present | `ragd_chunker/__init__.py` | ragd |
| `ragd_graph` | Symbol/import/call graph | ✅ present | `ragd_graph/__init__.py` | ragd |
| `ragd_vault` | Obsidian vault generator | ✅ present | `ragd_vault/__init__.py` | ragd |
| `ragd` | Retrieval-Augmented Generation Daemon (C++/HTTP) | ✅ present | `ragd/include/ragd/api.h` | none |
| `domdata` | Market data safety layer | ✅ present | `domdata/domdata.py` | none |
| `research_os` | Research ingestion and RAG preparation pipeline | ✅ present | `research_os/cli.py` | ragd |

---

## Complexity Budgets

| Package | Score | Budget | Status |
|---|---|---|---|
| `dominion_loader` | 53.6 | 40.0 | ⚠️ |
| `dominion_ai` | 135.6 | 50.0 | ⚠️ |
| `dominion_agent` | 429.8 | 60.0 | ⚠️ |
| `ragd_embed` | n/a | 45.0 | ✅ |
| `ragd_hnsw` | n/a | 45.0 | ✅ |
| `ragd_chunker` | n/a | 45.0 | ✅ |
| `ragd_graph` | n/a | 45.0 | ✅ |
| `ragd_vault` | n/a | 45.0 | ✅ |
| `ragd` | 43.9 | 80.0 | ✅ |
| `domdata` | 138.7 | 35.0 | ⚠️ |
| `research_os` | 157.7 | 50.0 | ⚠️ |
| `scripts` | 179.7 | 55.0 | ⚠️ |
| `tests` | 0.0 | 20.0 | ✅ |

---

## Data Flows

```
domdata/ ──────────────────► safety scanner
dominion_loader/ ──────────► file manifest ──► dominion_ai/
ragd/ ─────────────────────► HTTP API ──────► dominion_ai/
dominion_ai/ ──────────────► RAGD queries ──► scripts/dominion_cli.py
dominion_agent/ ───────────► control plane ─► all agents
research_os/ ──────────────► ingestion ─────► ragd/
ragd_chunker/ ─────────────► AST chunks ────► ragd/
ragd_embed/ ───────────────► embeddings ────► ragd_hnsw/
ragd_graph/ ───────────────► graph edges ───► ragd_vault/
ragd_vault/ ───────────────► Obsidian notes ◄ ragd/
```

---

## DB Stores

| Database | Path | Engine |
|---|---|---|
| Manifest | `~/.dominion/manifest.db` | SQLite WAL |
| Agent OS | `~/.dominion/agent_os.db` | SQLite WAL |
| Dominion Main | `data/dominion.duckdb` | DuckDB |

---

## Key Contracts

- `docs/agents/SHARED_INTERFACE_CONTRACT.md` — shared interface rules
- `docs/agents/AGENT_OS_CONTRACT.md` — Agent OS guarantees
- `AGENTS.md` — all active agents and their roles

---

## Missing Packages

*(all packages present)*

---

*Regenerate with: `dominion agent architecture refresh`*
