# Decision Ledger — Agent 0 (Systems Architect)

## Purpose
Records all architectural decisions, conflict resolutions, and phase gate approvals.
Agent 0 is the sole writer of this document.

---

## Decision Format

```
### DEC-{NNN}: {Title}
- **Date:** YYYY-MM-DD
- **Phase:** N
- **Raised by:** Agent {X}
- **Decision:** {description}
- **Rationale:** {why}
- **Dissenting agents:** {who disagreed, if any}
- **Impact:** {what changes}
- **Status:** ACTIVE | SUPERSEDED | DEFERRED
```

---

## Phase 0 Decisions

### DEC-001: Dataset Scope — M5 Timeframe, 10+ Years
- **Date:** 2026-05-20
- **Phase:** 0
- **Raised by:** Protocol specification
- **Decision:** Target dataset is M5 bars for XAUUSD, ~725,000 rows, 3,000 columns exactly.
- **Rationale:** M5 provides sufficient resolution for intraday trading while keeping row count manageable. 10+ year history ensures multiple market regimes captured.
- **Dissenting agents:** None
- **Impact:** Fundamental shift from current daily dataset (1,256 rows, 792 cols). Entire pipeline must be rebuilt.
- **Status:** ACTIVE

### DEC-002: Point-in-Time Safety is Non-Negotiable
- **Date:** 2026-05-20
- **Phase:** 0
- **Raised by:** Agent 0 (architectural invariant)
- **Decision:** Every feature must prove causal availability at bar close time. No exceptions.
- **Rationale:** Current codebase has at least 3 confirmed PIT violations (HMM full-sample fit, COT join on report_date not release_date, FRED join on observation_date not release_date). These silently poison any model trained on the data.
- **Dissenting agents:** None
- **Impact:** Existing data_pipeline/ regime detection, macro joins, and COT joins cannot be reused without fundamental redesign.
- **Status:** ACTIVE

### DEC-003: Existing Pipeline Coexistence
- **Date:** 2026-05-20
- **Phase:** 0
- **Raised by:** Agent 0
- **Decision:** New dominion/ package will be built alongside existing data_pipeline/ and hydra/. No modifications to existing code. Old and new pipelines coexist.
- **Rationale:** Existing hydra system is operational for live trading. Disrupting it during 15-phase dataset construction would be reckless. New pipeline writes to dominion/ namespace and data/dominion/ paths.
- **Dissenting agents:** None
- **Impact:** File ownership is clean — no conflicts with existing modules.
- **Status:** ACTIVE

### DEC-004: Registry-First Architecture
- **Date:** 2026-05-20
- **Phase:** 0
- **Raised by:** Protocol specification
- **Decision:** All 3,000 columns must be registered in config/columns.yaml BEFORE any computation begins. Computation code must validate against registry before writing.
- **Rationale:** Prevents unregistered columns, enforces naming convention, enables static validation without data.
- **Dissenting agents:** None
- **Impact:** Phase 1 must complete before any Phase 6+ feature work.
- **Status:** ACTIVE

### DEC-005: Source Realism — V1 Uses Free Data Only
- **Date:** 2026-05-20
- **Phase:** 0
- **Raised by:** Protocol specification
- **Decision:** No paid data sources in V1. No order book data. All microstructure features labeled "proxy". Unavailable sources produce NULL columns.
- **Rationale:** Prevents cosplay institutionalism. Better to have honest NULL than fabricated features.
- **Dissenting agents:** None
- **Impact:** Block K (Microstructure Proxy) names must contain "proxy". Blocks V, W may have high NULL percentage from unavailable sentiment sources.
- **Status:** ACTIVE

### DEC-006: Embargo Must Equal or Exceed Max Label Horizon
- **Date:** 2026-05-20
- **Phase:** 0
- **Raised by:** Agent 0 (identified from current config deficiency)
- **Decision:** embargo_bars >= max_label_horizon (288 bars = 1 trading day for M5). Current config has embargo=10 which is dangerously insufficient.
- **Rationale:** If labels look 288 bars ahead, an embargo of 10 bars means validation data can see information that influenced training labels. This is a subtle but critical leakage vector.
- **Dissenting agents:** None
- **Impact:** Split design must use embargo >= 288 bars minimum. Reduces effective validation set size.
- **Status:** ACTIVE

---

## Pending Decisions (Awaiting Agent Reports)

### PENDING-001: Dukascopy Library vs Direct HTTP
- **Status:** Awaiting Agent 2 and Agent 4 evaluation in Phase 2
- **Context:** Existing code uses direct HTTP + custom bi5 parser (working). Question is whether a library provides better reliability.

### PENDING-002: DuckDB Role in New Pipeline
- **Status:** Awaiting Agent 4 infrastructure report
- **Context:** DuckDB currently stores everything. New pipeline may use it only for metadata/registry, with Parquet blocks for features.

### PENDING-003: Advanced Feature Feasibility (TDA, Path Signatures)
- **Status:** Awaiting Agent 6 math report
- **Context:** Some proposed features (persistent homology) may be computationally infeasible on 725K rows. Need realistic compute budget.

---

## Escalation Queue
Items requiring user decision before proceeding:

(None yet — awaiting Phase 0 specialist reports)
