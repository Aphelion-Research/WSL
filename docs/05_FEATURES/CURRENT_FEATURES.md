---
doc_type: catalog
system: Dominion
ragd_priority: 7
audience:
  - maintainer
  - developer
  - researcher
status: active
last_reviewed: 2026-05-19
tags:
  - features
  - catalog
  - operational
---

# Current Features (Operational)

**Purpose:** Catalog of all operational features in Dominion V2 as of Phase 5.

**Status:** 19 operational features across 6 categories.

---

## Feature Categories

1. **Data Pipeline** (5 features)
2. **Microstructure** (5 features)
3. **Regime Detection** (3 features)
4. **Agent Operations** (3 features)
5. **Documentation** (2 features)
6. **Infrastructure** (1 feature)

---

## 1. Data Pipeline Features

### 1.1 Yahoo Finance Ingestion
- **Status:** Operational (Phase 1)
- **Purpose:** GC=F futures + GLD ETF data
- **Output:** 1-minute OHLCV bars
- **Tests:** 4/4 passing
- **Docs:** [[DATA_PIPELINE_OVERVIEW]]

### 1.2 Multi-Source Fusion
- **Status:** Operational (Phase 2)
- **Purpose:** Fuse 5 sources (Yahoo, FRED, AV, COT, MT5)
- **Algorithm:** 6-timescale Kalman filter bank
- **Performance:** 62% error reduction vs simple average
- **Tests:** 16/16 passing
- **Docs:** [[PHASE_2]], [[ADR_0003_kalman_fusion_over_simple_average]]

### 1.3 MT5 Real-Time Bridge
- **Status:** Operational (Phase 2)
- **Purpose:** Live tick ingestion via domdata CLI
- **Latency:** <100ms (tick → database)
- **Tests:** 4/4 passing
- **Docs:** [[DOMDATA_FEATURE]] (to be created)

### 1.4 Trust Scoring System
- **Status:** Operational (Phase 2)
- **Purpose:** Dynamic trust weighting per source
- **Algorithm:** Adaptive exponential smoothing + 3σ outlier rejection
- **Byzantine FT:** >90% outlier detection accuracy
- **Docs:** [[PHASE_2]]

### 1.5 Feature Generation Pipeline
- **Status:** Operational (Phase 2)
- **Purpose:** Compute 400+ features per bar
- **Categories:** Price (50), volatility (40), volume (30), microstructure (280)
- **Performance:** Vectorized pandas, <30s per day
- **Tests:** 8/8 passing
- **Docs:** [[DATA_FLOW]], [[EXEC_FEATURES_FEATURE]]

---

## 2. Microstructure Features

### 2.1 LOB Reconstruction Engine
- **Status:** Operational (Phase 3)
- **Purpose:** 10-level order book reconstruction from ticks
- **Features:** OFI (1s, 5s, 1m), VPIN (50 buckets), spread estimates
- **Limitation:** Synthetic quotes (2 bps spread)
- **Tests:** 8/8 passing
- **Docs:** [[LOB_RECONSTRUCTION_FEATURE]]

### 2.2 Execution Simulator
- **Status:** Operational (Phase 3)
- **Purpose:** Simulate order execution with realistic slippage
- **Strategies:** VWAP, TWAP, POV
- **Impact Model:** Almgren-Chriss
- **Performance:** 10K orders/s matching
- **Tests:** 8/8 passing
- **Docs:** [[EXEC_SIM_FEATURE]]

### 2.3 TCA Dashboard
- **Status:** Operational (Phase 3)
- **Purpose:** Transaction cost attribution
- **Components:** Decision, Timing, Impact, Opportunity costs
- **Benchmarks:** VWAP, TWAP, Arrival Price
- **Metrics:** <20 bps total cost (typical)
- **Tests:** 4/4 passing
- **Docs:** [[TCA_FEATURE]]

### 2.4 Toxicity Monitor
- **Status:** Operational (Phase 3)
- **Purpose:** Real-time adverse selection detection
- **Metrics:** VPIN, OFI, Adverse selection score
- **Composite Score:** Weighted (VPIN=0.4, OFI=0.3, Adverse=0.3)
- **Alert Threshold:** 0.7 (0-1 scale)
- **Tests:** 4/4 passing
- **Docs:** [[TOXICITY_FEATURE]]

### 2.5 Execution Alpha Features
- **Status:** Operational (Phase 3)
- **Purpose:** 50 alpha features for execution quality
- **Categories:** Spread (10), Depth (10), Flow (10), Quote (10), Trade (10)
- **Top Feature:** ofi_1m (IC=0.15)
- **Horizon:** 60-min forward returns
- **Tests:** 6/6 passing
- **Docs:** [[EXEC_FEATURES_FEATURE]]

---

## 3. Regime Detection Features

### 3.1 HMM Regime Detection
- **Status:** Operational (Phase 4)
- **Purpose:** 3-state regime classification (Bull/Neutral/Bear)
- **Features:** 5-day returns, 20-day vol, volume ratio, OFI 1m
- **Performance:** Regime duration avg 5 days (stable)
- **Distribution:** Bull 35%, Neutral 45%, Bear 20%
- **Tests:** 6/6 passing
- **Docs:** [[PHASE_4]], [[ADR_0006_hmm_for_regime_detection]] (to be created)

### 3.2 Economic Calendar Integration
- **Status:** Operational (Phase 4)
- **Purpose:** Event-driven features (FOMC, NFP, Fed speeches)
- **Events:** 20+ per month
- **Features:** Time-to-event, event type, importance score
- **Tests:** 4/4 passing
- **Docs:** [[PHASE_4]]

### 3.3 Intelligence Report Generation
- **Status:** Operational (Phase 4)
- **Purpose:** Daily markdown reports (regime, features, anomalies)
- **Frequency:** Daily at 9am
- **RAGD Ingestion:** Yes (+300 chunks from 60 reports)
- **Format:** Markdown with frontmatter
- **Tests:** 2/2 passing
- **Docs:** [[PHASE_4]]

---

## 4. Agent Operations Features

### 4.1 RAGD Query System
- **Status:** Operational (Phase 0)
- **Purpose:** Vector + keyword search over documentation
- **Index:** SQLite + HNSW (sqlite-vss)
- **Chunks:** ~7500 (as of Phase 5)
- **API:** REST (127.0.0.1:7474)
- **Tests:** 8/8 passing
- **Docs:** [[RAGD_OVERVIEW]]

### 4.2 Agent Session Management
- **Status:** Operational (Phase 0)
- **Purpose:** Track agent sessions, context, handoffs
- **Features:** Session state, complexity budgets, safety rules
- **Storage:** JSON files (sessions/)
- **Tests:** 4/4 passing
- **Docs:** [[AGENT_OPERATING_SYSTEM]]

### 4.3 Agent Handoff Protocol
- **Status:** Operational (Phase 0)
- **Purpose:** Pass work between agents with context preservation
- **Format:** Markdown with sections (Request, Progress, Blockers, Next)
- **Usage:** Multi-session long-running tasks
- **Tests:** 2/2 passing
- **Docs:** [[AGENT_HANDOFF]]

---

## 5. Documentation Features

### 5.1 Obsidian Vault Integration
- **Status:** Operational (Phase 5)
- **Purpose:** 1000+ cross-linked notes for knowledge graph
- **Notes:** 945 (as of Phase 5)
- **Sync:** Auto-sync via post-commit hook
- **Graph View:** Configured with color-coded tags
- **Broken Links:** 63 (target <50)
- **Docs:** [[OBSIDIAN_VAULT_MANIFEST]]

### 5.2 Prompt Library
- **Status:** Operational (Phase 5)
- **Purpose:** Reusable agent workflow templates
- **Prompts:** 11 (repo audit, feature impl, doc update, RAGD update, etc.)
- **Format:** Context + Mission + Constraints + Workflow + Validation
- **Usage:** CODEX agent workflows
- **Docs:** [[PROMPT_INDEX]]

---

## 6. Infrastructure Features

### 6.1 DuckDB Analytics Storage
- **Status:** Operational (Phase 1)
- **Purpose:** OLAP-optimized storage for prices + features
- **Tables:** gold_master (prices), features (400+ columns)
- **Performance:** Fast aggregations, columnar storage
- **Size:** ~50MB per month
- **Tests:** 6/6 passing
- **Docs:** [[REPO_STRUCTURE]], [[ADR_0005_duckdb_for_analytics_storage]] (to be created)

---

## Feature Statistics

| Category | Features | Tests | Test Pass Rate |
|---|---|---|---|
| Data Pipeline | 5 | 32 | 100% |
| Microstructure | 5 | 30 | 100% |
| Regime Detection | 3 | 12 | 100% |
| Agent Operations | 3 | 14 | 100% |
| Documentation | 2 | N/A | N/A |
| Infrastructure | 1 | 6 | 100% |
| **Total** | **19** | **94** | **100%** |

---

## Feature Dependencies

**High-level dependency graph:**

```
Phase 0 (Foundation)
  ├─ RAGD Query System
  ├─ Agent Session Management
  └─ Agent Handoff Protocol
         │
Phase 1 (Data MVP)
  └─ Yahoo Finance Ingestion
  └─ DuckDB Analytics Storage
         │
Phase 2 (Multi-Source)
  ├─ Multi-Source Fusion
  ├─ MT5 Real-Time Bridge
  ├─ Trust Scoring System
  └─ Feature Generation Pipeline
         │
Phase 3 (Microstructure)
  ├─ LOB Reconstruction Engine
  ├─ Execution Simulator
  ├─ TCA Dashboard
  ├─ Toxicity Monitor
  └─ Execution Alpha Features
         │
Phase 4 (Regime Detection)
  ├─ HMM Regime Detection
  ├─ Economic Calendar Integration
  └─ Intelligence Report Generation
         │
Phase 5 (Documentation)
  ├─ Obsidian Vault Integration
  └─ Prompt Library
```

---

## Feature Maturity

**Production-Ready (13):**
- All Phase 1-2 features
- All microstructure subsystems (Phase 3)
- HMM regime detection (Phase 4)

**Beta (4):**
- Economic calendar (API limitations)
- Intelligence reports (format evolving)
- Obsidian vault (broken links >50)
- Prompt library (in early use)

**Alpha (2):**
- Agent session management (minimal usage)
- Agent handoff (new protocol)

---

## Usage Statistics (Est.)

| Feature | Daily Usage |
|---|---|
| Data Pipeline | 24/7 (continuous) |
| LOB Reconstruction | 24/7 (continuous) |
| Feature Generation | 1×/day (daily run) |
| HMM Regime Detection | 1×/day (daily update) |
| Intelligence Reports | 1×/day (9am) |
| RAGD Query | 50-100×/session (agent queries) |
| Obsidian Vault | 1×/commit (auto-sync) |
| TCA Dashboard | On-demand (manual review) |
| Toxicity Monitor | 24/7 (real-time) |

---

## Related Documentation

- [[PLANNED_FEATURES]] — Features in development
- [[EXPERIMENTAL_FEATURES]] — Research features
- [[DEPRECATED_FEATURES]] — Retired features
- [[FEATURE_DEPENDENCY_MAP]] — Dependency visualization
- [[FEATURE_PRIORITY_MATRIX]] — Development prioritization

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After each phase completion

**How to Add:**
1. Create feature spec (use [[FEATURE_TEMPLATE]])
2. Add entry here (under appropriate category)
3. Update feature count + statistics
4. Update dependency graph
5. Update RAGD (`python scripts/build_ragd.py`)
