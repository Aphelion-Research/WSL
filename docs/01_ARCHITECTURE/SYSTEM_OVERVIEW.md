---
doc_type: architecture
system: Dominion
ragd_priority: 9
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19
tags:
  - architecture
  - system-design
  - overview
---

# Dominion System Architecture

See [00_START_HERE/OVERVIEW.md](../00_START_HERE/OVERVIEW.md) for complete system overview.

This doc focuses on architectural design principles and high-level structure.

## Architectural Principles

1. **Local-first:** No cloud dependencies, sovereign infrastructure
2. **Agent-native:** Designed for AI coding agents from day 1
3. **RAGD-first:** Persistent memory powers all operations
4. **Read-only data:** Market data input only, zero trading execution
5. **Validated:** Tests pass before claiming success
6. **Documented:** Self-documenting system
7. **Incremental:** Small diffs, frequent validation
8. **Safe:** Multiple safety layers (trading blocks, secret protection, data preservation)

## Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│         Agent Layer (Codex, Claude, Cursor)         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │  Agent OS    │  │  Adversary   │  │  Handoff  │ │
│  │  (Safety)    │  │  (Review)    │  │  (Report) │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                       ↕
┌─────────────────────────────────────────────────────┐
│        Intelligence Layer (RAGD + RAG + Vault)      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │    RAGD      │  │  RAG Retrieval│  │   Vault   │ │
│  │ (Memory)     │  │  (Context)   │  │  (Graph)  │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                       ↕
┌─────────────────────────────────────────────────────┐
│       Data Layer (Pipeline + Microstructure)        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Data Pipeline│  │  LOB + Exec  │  │ TCA + Tox │ │
│  │ (5 sources)  │  │  (Sim)       │  │ (Analysis)│ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
                       ↕
┌─────────────────────────────────────────────────────┐
│    Foundation Layer (Native Core + domdata)         │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ Native Core  │  │   domdata    │  │  Loader   │ │
│  │ (C++ spine)  │  │  (MT5 bridge)│  │  (Scan)   │ │
│  └──────────────┘  └──────────────┘  └───────────┘ │
└─────────────────────────────────────────────────────┘
```

## Component Interaction

```mermaid
graph TB
    subgraph "Agent Layer"
        CODEX[Codex/Claude<br/>AI Agents]
        AGENTSYS[Agent OS<br/>Session + Safety]
        ADVERSARY[Adversary<br/>Review System]
    end
    
    subgraph "Intelligence Layer"
        RAGD[(RAGD<br/>SQLite + HNSW<br/>7159 chunks)]
        RAG[RAG Retrieval<br/>BM25 + Semantic]
        VAULT[Vault<br/>878 Obsidian notes]
        GRAPH[Graph Memory<br/>Handoffs + Relations]
    end
    
    subgraph "Data Layer"
        PIPELINE[Data Pipeline<br/>5 sources<br/>400+ features]
        LOB[LOB Engine<br/>Order book<br/>OFI + VPIN]
        EXEC[Exec Simulator<br/>VWAP/TWAP/POV]
        TCA[TCA Dashboard<br/>Cost attribution]
        TOX[Toxicity Monitor<br/>Adverse selection]
        EXECFEAT[Exec Features<br/>50 alpha features]
    end
    
    subgraph "Storage Layer"
        DUCKDB[(DuckDB<br/>gold_master<br/>features<br/>reports)]
        SQLITE[(SQLite<br/>RAGD<br/>Agent OS<br/>Manifest)]
    end
    
    subgraph "Foundation Layer"
        NATIVE[Native Core<br/>C++ spine<br/>Fast scan]
        DOMDATA[domdata<br/>MT5 bridge<br/>Read-only]
        LOADER[Loader<br/>File scanner<br/>Manifest gen]
        RESEARCH[Research OS<br/>Web crawler<br/>Approved sources]
    end
    
    subgraph "Data Sources"
        MT5[MT5/Wine<br/>Real-time ticks]
        YAHOO[Yahoo Finance<br/>GC=F, GLD]
        FRED[FRED API<br/>10 macro series]
        AV[Alpha Vantage<br/>GLD OHLCV]
        COT[CFTC COT<br/>Positioning]
    end
    
    %% Agent workflows
    CODEX -->|init session| AGENTSYS
    CODEX -->|query context| RAG
    RAG -->|retrieve chunks| RAGD
    CODEX -->|read files| NATIVE
    CODEX -->|write code| AGENTSYS
    AGENTSYS -->|check safety| ADVERSARY
    ADVERSARY -->|score output| CODEX
    CODEX -->|handoff report| GRAPH
    GRAPH -->|store| RAGD
    
    %% Intelligence layer
    VAULT -.->|synced to| RAGD
    RAGD -->|indexes| NATIVE
    LOADER -->|scans repo| NATIVE
    LOADER -->|writes manifest| SQLITE
    RESEARCH -->|fetches docs| RAGD
    
    %% Data ingestion
    MT5 -->|ticks| DOMDATA
    YAHOO -->|prices| PIPELINE
    FRED -->|macro| PIPELINE
    AV -->|OHLCV| PIPELINE
    COT -->|positioning| PIPELINE
    DOMDATA -->|XAU/USD ticks| PIPELINE
    
    %% Data processing
    PIPELINE -->|fused prices| DUCKDB
    PIPELINE -->|400+ features| DUCKDB
    PIPELINE -->|intelligence reports| RAGD
    
    %% Microstructure flow
    DUCKDB -->|ticks| LOB
    LOB -->|OFI + depth| TOX
    LOB -->|book state| EXEC
    TOX -->|toxicity| EXEC
    EXEC -->|simulated trades| TCA
    TCA -->|TCA reports| DUCKDB
    DUCKDB -->|market data| EXECFEAT
    EXECFEAT -->|features| DUCKDB
    
    %% Agent reads data
    CODEX -.->|query| DUCKDB
    RAG -.->|search| DUCKDB
```

**Key Interactions:**

| From | To | Purpose |
|---|---|---|
| Agent | RAGD | Context retrieval before code changes |
| Agent | Agent OS | Session lifecycle + safety enforcement |
| Agent | Adversary | Output review + toxicity scoring |
| Data Sources | Pipeline | Multi-source fusion + feature generation |
| Pipeline | DuckDB | Normalized storage (gold_master, features) |
| Pipeline | RAGD | Intelligence reports indexed for retrieval |
| DuckDB | Microstructure | Tick data + book reconstruction |
| LOB | Toxicity/Exec | Order flow imbalance + adverse selection |
| Vault | RAGD | Obsidian notes indexed for semantic search |
| Loader | Native | Fast file scanning (11x faster than Python) |
| Research | RAGD | External docs ingested with provenance |

See DATA_FLOW.md, CONTROL_FLOW.md, MODULE_MAP.md for detailed diagrams.

## Extension Points

See EXTENSION_POINTS.md for how to add:
- New data sources
- New features
- New microstructure subsystems
- New agent capabilities
- New RAGD indexes

## Current Limitations

See KNOWN_LIMITATIONS.md for:
- Performance bottlenecks
- Scalability constraints
- Missing features
- Technical debt
- Open questions

## Future Architecture

See FUTURE_ARCHITECTURE.md for long-term vision.
