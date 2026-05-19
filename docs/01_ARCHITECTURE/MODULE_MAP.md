---
doc_type: architecture
system: Dominion
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - architecture
  - modules
  - dependencies
---

# Module Map

## Top-Level Modules

```
Dominion/
├── ragd/                   # Native C++ RAGD core
├── domdata/                # MT5 data bridge (CRITICAL)
├── data_pipeline/          # Multi-source fusion + features
├── dominion_agent/         # Agent OS (safety + lifecycle)
├── dominion_ai/            # RAG retrieval layer
├── dominion_loader/        # Scan + manifest + cache
├── research_os/            # Approved-source crawler
├── exec_sim/               # Execution simulator
├── lob/                    # LOB reconstruction engine
├── tca/                    # Transaction cost analysis
├── toxicity/               # Toxicity monitoring
├── exec_features/          # Execution alpha features
├── ragd_embed/             # Embedding pipeline
├── ragd_hnsw/              # HNSW vector index
├── ragd_chunker/           # AST-aware chunking
├── ragd_graph/             # Graph memory
├── ragd_vault/             # Vault operations
├── ragd_bus/               # Agent coordination bus
├── scripts/                # CLI tools
├── tests/                  # Test suite
├── vault/                  # Obsidian vault
├── docs/                   # Documentation brain
└── reports/                # Historical reports
```

## Module Dependencies

```mermaid
graph TB
    domdata[domdata<br/>MT5 bridge] --> pipeline[data_pipeline<br/>Fusion + features]
    
    pipeline --> lob[lob<br/>LOB engine]
    pipeline --> execfeat[exec_features<br/>Alpha features]
    
    lob --> tox[toxicity<br/>Toxicity monitor]
    lob --> exec[exec_sim<br/>Execution simulator]
    tox --> exec
    exec --> tca[tca<br/>Cost analysis]
    
    loader[dominion_loader<br/>Scan + manifest] --> native[ragd<br/>Native C++ core]
    loader --> ragd_core[RAGD<br/>Memory system]
    
    chunker[ragd_chunker<br/>AST chunker] --> ragd_core
    embed[ragd_embed<br/>Embeddings] --> hnsw[ragd_hnsw<br/>Vector index]
    hnsw --> ragd_core
    
    ragd_core --> rag[dominion_ai<br/>RAG retrieval]
    ragd_core --> vault_ops[ragd_vault<br/>Vault ops]
    ragd_core --> graph[ragd_graph<br/>Graph memory]
    ragd_core --> bus[ragd_bus<br/>Agent bus]
    
    rag --> agent_sys[dominion_agent<br/>Agent OS]
    agent_sys --> adversary[Adversary<br/>Review system]
    
    research[research_os<br/>Web crawler] --> ragd_core
```

## Critical Modules (Do Not Break)

| Module | Why Critical | Validation |
|---|---|---|
| **domdata** | Only MT5 data source | `domdata xautick` must work |
| **RAGD** | All agent context | `curl 127.0.0.1:7474/health` |
| **data_pipeline** | All market data | 16/16 tests must pass |
| **dominion_agent** | Agent safety | Safety tests must pass |

## Module Owners

| Module | Primary Owner | Notes |
|---|---|---|
| domdata | Matin | Trading safety critical |
| RAGD | Matin | Native C++ + Python |
| data_pipeline | Matin | Multi-source integration |
| Agent OS | Matin | Safety + lifecycle |
| Microstructure | Matin | LOB/Exec/TCA/Tox/Features |
| Research OS | Matin | Optional crawler |
| Vault | Matin | Obsidian integration |
| Docs | Matin + Agents | Living documentation |

## Module Maturity

| Module | Status | Test Coverage | Notes |
|---|---|---|---|
| domdata | STABLE | High | Production-ready |
| RAGD | STABLE | High | 24/24 C++ tests |
| data_pipeline | STABLE | High | 16/16 tests |
| Agent OS | STABLE | High | Full coverage |
| RAG retrieval | STABLE | High | Eval passing |
| LOB engine | STABLE | High | 8/8 tests |
| Exec simulator | STABLE | High | 8/8 tests |
| TCA | STABLE | Medium | 4/4 tests |
| Toxicity | STABLE | Medium | 4/4 tests |
| Exec features | STABLE | High | 6/6 tests |
| Research OS | BETA | Medium | 7 tests |
| Vault | STABLE | High | 0 broken links |

## Extension Points

To add a new module:
1. Create folder under repo root
2. Add `__init__.py` for Python modules
3. Add tests under `<module>/tests/`
4. Update this doc with dependencies
5. Update RAGD_INGESTION_MANIFEST.md
6. Run `dominion scan` to index

## Retrieval Hints

- "module structure"
- "what modules exist"
- "dependencies between modules"
- "which modules are critical"
- "how to extend the system"
