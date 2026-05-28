---
doc_type: architecture
system: Dominion
ragd_priority: 9
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - architecture
  - data-flow
---

# Data Flow Architecture

## Primary Data Flows

### 1. Market Data Ingestion Flow

```mermaid
graph LR
    MT5[MT5 Ticks] --> domdata[domdata CLI]
    Yahoo[Yahoo Finance] --> pipeline[Data Pipeline]
    FRED[FRED API] --> pipeline
    AV[Alpha Vantage] --> pipeline
    COT[CFTC COT] --> pipeline
    domdata --> pipeline
    
    pipeline --> kalman[Kalman Fusion]
    kalman --> duckdb[(DuckDB)]
    
    duckdb --> lob[LOB Engine]
    duckdb --> features[Feature Engine]
    
    lob --> toxicity[Toxicity Monitor]
    lob --> execsim[Exec Simulator]
    toxicity --> execsim
    execsim --> tca[TCA Dashboard]
    
    duckdb --> reports[Intelligence Reports]
    reports --> ragd[(RAGD)]
```

### 2. Agent Workflow Data Flow

```mermaid
graph TB
    agent[AI Agent] --> handoff[Read AGENT_HANDOFF.md]
    handoff --> query[Query RAGD]
    query --> ragd[(RAGD)]
    ragd --> chunks[Context Chunks]
    chunks --> agent
    
    agent --> edit[Code Edit]
    edit --> validate[Run Tests]
    validate --> safety[Trading Check]
    safety --> health[Platform Health]
    
    health --> remember[RAGD Remember]
    remember --> ragd
    health --> update[Update Handoff]
    update --> report[Write Report]
```

### 3. RAGD Indexing Flow

```mermaid
graph LR
    files[Repo Files] --> loader[Loader Scan]
    loader --> manifest[(Manifest DB)]
    
    files --> chunker[AST Chunker]
    chunker --> chunks[Text Chunks]
    chunks --> embed[Embedding]
    embed --> hnsw[(HNSW Index)]
    
    chunks --> sqlite[(SQLite)]
    sqlite --> ragd[RAGD API]
    hnsw --> ragd
    
    ragd --> retrieval[RAG Retrieval]
```

## Data Stores

| Store | Technology | Purpose | Size (2026-05-19) |
|---|---|---|---|
| RAGD DB | SQLite + HNSW | Document chunks + embeddings | 8,760 total chunks |
| Manifest DB | SQLite | File hashes + metadata | ~1,300 files |
| Agent OS DB | SQLite | Sessions + tasks + locks | Active sessions vary |
| Data Pipeline DB | DuckDB | Market data + features | Growing daily |
| Microstructure DB | DuckDB | LOB + exec + TCA + toxicity | Growing daily |
| Vault | Markdown files | Knowledge graph | 878 notes |

## Data Retention

- **RAGD chunks:** Soft-delete when source file removed
- **Market data:** Indefinite retention (compressed)
- **Feature history:** Rolling 2-year window
- **Intelligence reports:** Indefinite retention
- **Agent session logs:** 90-day retention
- **Backups:** See backups/ folder

## Data Privacy

- **Secrets:** Never indexed, never committed, never printed
- **API keys:** Environment variables only
- **MT5 credentials:** `secrets/mt5.env` (excluded from all scans)
- **Personal data:** None collected
- **Trading data:** Read-only, no orders

## Data Validation

Every data source validates:
- Schema correctness
- Timestamp ordering
- Missing value handling
- Outlier detection (>5σ quarantine)
- Cross-source consistency (Byzantine FT)

## Retrieval Hints

Queries for this doc:
- "data flow"
- "how does data move through the system"
- "where does market data come from"
- "how does RAGD get populated"
- "what databases exist"
