# Conflict Ledger — Cross-Examination Results

## Purpose
Records all disputes, agreements, and deferrals from inter-agent cross-examination.
Agent 0 is the sole writer of this document.

---

## Conflict Format

```
### CONF-{NNN}: {Title}
- **Parties:** Agent {X} vs Agent {Y}
- **Category:** AGREEMENT | DISPUTE | DEFERRAL | REJECTION
- **Subject:** {what the disagreement is about}
- **Agent X position:** {claim}
- **Agent Y position:** {counter-claim}
- **Evidence:** {what supports each side}
- **Resolution:** {Agent 0's decision}
- **Decision ID:** DEC-{NNN} (if new decision required)
```

---

## Phase 0 Cross-Examination Results

### CONF-001: HMM Full-Sample Fit — Leakage Severity
- **Parties:** Agent 3 (Temporal) vs Agent 6 (Math)
- **Category:** AGREEMENT
- **Subject:** Whether current HMM regime detection constitutes leakage
- **Agent 3 position:** Full-sample HMM.fit() is unambiguous future leakage. The model sees future returns when classifying historical bars.
- **Agent 6 position:** Agrees. HMM must use expanding window with periodic refit. First 6 months of data should be flagged unstable or NULL.
- **Evidence:** data_pipeline/features/regime.py line 52: `model.fit(X_valid)` where X_valid is ALL valid rows.
- **Resolution:** AGREEMENT — both agents concur. Current implementation is UNSAFE. Expanding-window HMM mandatory for new pipeline.

### CONF-002: VPIN Without Order Book — Naming
- **Parties:** Agent 1 (Finance) vs Agent 6 (Math)
- **Category:** AGREEMENT
- **Subject:** Whether bar-derived VPIN should be called "VPIN" or "vpin_proxy"
- **Agent 1 position:** VPIN computed from bar OHLCV is a crude approximation. Tick-rule accuracy for gold is ~67%. Must be labeled "proxy".
- **Agent 6 position:** Agrees. Mathematical definition of VPIN requires tick-level trade classification. Bar-level approximation is a different quantity.
- **Evidence:** data_pipeline/features/microstructure.py uses close > open tick rule on bars. toxicity/vpin.py uses bulk volume classification on reconstructed ticks.
- **Resolution:** AGREEMENT — all microstructure features approximating order book quantities must contain "proxy" in column name.

### CONF-003: COT Join Key — report_date vs release_timestamp
- **Parties:** Agent 3 (Temporal) vs Agent 1 (Finance)
- **Category:** AGREEMENT
- **Subject:** Whether joining COT on report_date (Tuesday) constitutes leakage
- **Agent 3 position:** Joining on report_date means features "know" Tuesday's positions before Friday's release. This is 3-day look-ahead leakage.
- **Agent 1 position:** Agrees. In practice, traders cannot act on COT data until Friday 3:30 PM ET at earliest. Join must use release_timestamp.
- **Evidence:** hydra/data/loader.py line 51: `load_cot` uses report_date as ts. data_pipeline/sources/cot.py only stores report_date.
- **Resolution:** AGREEMENT — canonical COT storage MUST include release_timestamp column. PIT join on release_timestamp only.

### CONF-004: FRED Publication Delay
- **Parties:** Agent 3 (Temporal) vs Agent 2 (Sources)
- **Category:** AGREEMENT
- **Subject:** Whether FRED data can be joined on observation_date
- **Agent 3 position:** CPI observation_date is month-end, but release is ~2 weeks later. Current forward-fill from observation_date leaks by publication delay.
- **Agent 2 position:** Agrees. FRED API provides realtime_start field that represents publication date. This should be stored as release_timestamp.
- **Evidence:** data_pipeline/sources/fred.py fetches observations but does not store realtime_start.
- **Resolution:** AGREEMENT — FRED adapter must fetch and store realtime_start as release_timestamp. PIT join uses release_timestamp.

### CONF-005: Embargo Size for M5
- **Parties:** Agent 3 (Temporal) vs Agent 7 (QA)
- **Category:** AGREEMENT
- **Subject:** Minimum embargo size for M5 dataset
- **Agent 3 position:** embargo_bars >= max_label_horizon. If labels look 288 bars ahead (1 trading day), embargo must be >= 288.
- **Agent 7 position:** Agrees and adds: need a TEST that verifies embargo >= max_label_horizon programmatically. Should be a quality gate.
- **Evidence:** hydra/config.py has embargo_bars=10 (designed for 20-bar daily horizon, but dangerously small even there).
- **Resolution:** AGREEMENT — embargo minimum is max(label_horizon) across all labels in Z2. Quality gate enforces this.

### CONF-006: PCA/Statistical Transform Window Policy
- **Parties:** Agent 6 (Math) vs Agent 3 (Temporal)
- **Category:** AGREEMENT
- **Subject:** Whether PCA and z-scores can use full-sample statistics
- **Agent 6 position:** PCA must use expanding window (fit on data[0:T]). Z-scores must use rolling or expanding window. Full-sample stats are leakage.
- **Agent 3 position:** Agrees completely. Adds: first N rows (where N = minimum window for stable estimation) should be NULL, not zero-filled.
- **Evidence:** data_pipeline/features/price.py zscore uses rolling window (correct). hydra/data/features.py PCA uses train_idx (correct per fold but not for online inference).
- **Resolution:** AGREEMENT — all statistical transforms use rolling or expanding windows. Insufficient-window rows are NULL.

### CONF-007: Advanced Feature Compute Budget
- **Parties:** Agent 6 (Math) vs Agent 4 (Infrastructure)
- **Category:** DEFERRAL
- **Subject:** Whether persistent homology is computationally feasible on 725K rows
- **Agent 6 position:** TDA with window=200 bars, computed per bar, requires ~725K Rips complex calculations. With Ripser++ and small window, may be feasible but will take days.
- **Agent 4 position:** Compute budget unclear until benchmarked. Proposes: Phase 10 starts with 1-year sample timing test. If single feature takes >24h on 1 year, it's infeasible for V1.
- **Evidence:** No benchmarks exist in repo. Theoretical: O(n^3) for Rips on n points, n=200 → ~8M operations per bar, ×725K bars = 5.8T operations total.
- **Resolution:** DEFERRAL — benchmark in Phase 10 on 1-year sample. If infeasible, allocated columns become NULL with documentation. Decision will be made in Phase 10.

### CONF-008: Source Availability — LBMA Fix
- **Parties:** Agent 2 (Sources) vs Agent 1 (Finance)
- **Category:** DEFERRAL
- **Subject:** Whether LBMA gold fix is freely available with 10+ years history
- **Agent 2 position:** LBMA publishes fixing prices on their website. Historical data availability and format need Phase 2 verification. Cannot confirm depth or stability of access.
- **Agent 1 position:** LBMA fix is critical for gold market analysis (AM/PM fix drives physical market pricing). Even if scraping is fragile, having it as a source is important.
- **Evidence:** Protocol lists lbma_fix as FREE_OFFICIAL, CORE_REQUIRED. No existing adapter in repo.
- **Resolution:** DEFERRAL — marked as DOCUMENTATION_BASED. Phase 2 must verify connectivity, format, and historical depth. If unavailable, allocated columns become NULL.

### CONF-009: GVZ Historical Depth
- **Parties:** Agent 2 (Sources) vs Agent 1 (Finance)
- **Category:** DEFERRAL
- **Subject:** How far back GVZ (CBOE Gold Volatility Index) data extends
- **Agent 2 position:** GVZ launched in 2008-2010 era. Available via Yahoo Finance as ^GVZ. Exact start date and data quality need Phase 2 verification.
- **Agent 1 position:** GVZ is the gold equivalent of VIX. Critical for volatility regime detection. Even 5 years is useful.
- **Evidence:** Protocol lists cboe_gvz as 10yr depth. No existing adapter in repo.
- **Resolution:** DEFERRAL — verify in Phase 2. If <10yr history, document coverage gap.

### CONF-010: Registry Size — 3,000 YAML Entries Feasibility
- **Parties:** Agent 5 (Schema) vs Agent 4 (Infrastructure)
- **Category:** AGREEMENT
- **Subject:** Whether 3,000 column specs can be maintained in a single YAML file
- **Agent 5 position:** 3,000 entries × ~20 fields each = ~60,000 lines of YAML. Manageable with template generation for repetitive blocks (returns × windows, cross-asset × metrics).
- **Agent 4 position:** Agrees but notes: YAML parsing of 60K lines takes ~2-5 seconds. Acceptable for validation, not for hot-path computation.
- **Evidence:** No existing columns.yaml in repo. Protocol requires config/columns.yaml.
- **Resolution:** AGREEMENT — Use template generation for repetitive patterns, manual specification for unique columns. YAML is validation-time only, not runtime.

---

## Summary Statistics
- Total conflicts examined: 10
- AGREEMENT: 7
- DISPUTE: 0
- DEFERRAL: 3
- REJECTION: 0

## Unresolved Items for User Decision
None at this time. All deferrals are resolvable in later phases without user intervention.
