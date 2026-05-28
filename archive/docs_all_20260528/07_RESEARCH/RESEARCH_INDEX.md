---
doc_type: index
system: Dominion
ragd_priority: 5
audience:
  - researcher
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - research
  - index
  - literature
---

# Research Index

**Purpose:** Catalog of research notes, literature, and experiments for Dominion V2.

**Status:** 4 research areas documented (Phase 5).

---

## Research Areas

### 1. Kalman Filtering & Multi-Source Fusion
**File:** [[KALMAN_RESEARCH]]

**Topics:**
- Kalman filter theory
- Multi-timescale filter banks
- Dynamic trust scoring
- Byzantine fault tolerance
- Brownian bridge interpolation

**Key Papers:**
- Kalman (1960) — Original Kalman filter paper
- Bar-Shalom et al. (2001) — Multi-sensor fusion
- Durbin & Koopman (2012) — Time series via state space

**Implementation:** Phase 2 (Q2-Q3 2025)
**Results:** 62% error reduction vs simple average

---

### 2. HMM Regime Detection
**File:** [[HMM_REGIME_RESEARCH]]

**Topics:**
- Hidden Markov Models
- Regime classification (Bull/Neutral/Bear)
- Baum-Welch algorithm
- Online updating
- Regime-conditional features

**Key Papers:**
- Baum et al. (1970) — HMM foundations
- Hamilton (1989) — Regime-switching models
- Ang & Bekaert (2002) — International asset allocation with regime shifts

**Implementation:** Phase 4 (Q4 2025 - Q1 2026)
**Results:** 3-state model, 5-day avg regime duration

---

### 3. Microstructure & Market Toxicity
**File:** [[MICROSTRUCTURE_LITERATURE]]

**Topics:**
- Order flow imbalance (OFI)
- Volume-synchronized PIN (VPIN)
- Adverse selection
- Limit order book dynamics
- Trade classification (Lee-Ready)

**Key Papers:**
- Easley et al. (2012) — Flow toxicity and liquidity
- Cont et al. (2014) — Order book dynamics
- Hasbrouck (2007) — Empirical market microstructure

**Implementation:** Phase 3 (Q3-Q4 2025)
**Results:** VPIN alert threshold 0.7, OFI IC=0.15

---

### 4. Alpha Research & Feature Selection
**File:** [[ALPHA_RESEARCH_LOG]]

**Topics:**
- Feature selection (LASSO, RF importance)
- Alpha model comparison (Linear, Tree, Neural)
- Walk-forward validation
- Ensemble methods
- IC decay monitoring

**Key Papers:**
- De Prado (2018) — Advances in Financial ML
- Guyon & Elisseeff (2003) — Feature selection introduction
- Breiman (2001) — Random forests

**Implementation:** Phase 6 (planned Q2-Q3 2026)
**Target:** Sharpe >1.0, top 50 features IC >0.05

---

## Research by Phase

### Phase 0: Foundation (Q4 2024 - Q1 2025)
- RAGD vector search (HNSW)
- Native C++ parsing (tree-sitter)
- Agent OS safety rules

### Phase 1: Data MVP (Q1-Q2 2025)
- DuckDB vs PostgreSQL
- Feature engineering patterns
- Vectorized pandas operations

### Phase 2: Multi-Source Fusion (Q2-Q3 2025)
- **[[KALMAN_RESEARCH]]** — Kalman filter banks
- Trust scoring algorithms
- Byzantine fault tolerance
- Brownian bridge interpolation

### Phase 3: Microstructure (Q3-Q4 2025)
- **[[MICROSTRUCTURE_LITERATURE]]** — LOB reconstruction
- Almgren-Chriss market impact
- Synthetic quote generation
- VPIN computation (50 buckets)

### Phase 4: Regime Detection (Q4 2025 - Q1 2026)
- **[[HMM_REGIME_RESEARCH]]** — 3-state HMM
- Baum-Welch online updating
- Economic calendar integration

### Phase 5: Documentation (Q2 2026)
- Documentation quality metrics
- Obsidian vault design
- Prompt engineering patterns

### Phase 6: Alpha Research (Planned Q2-Q3 2026)
- **[[ALPHA_RESEARCH_LOG]]** — Feature selection
- Model comparison (Linear/Tree/Neural)
- Ensemble strategies
- Walk-forward validation

---

## Key Findings

### 1. Kalman Filter Superior to Simple Average
**Result:** 62% error reduction (0.12% vs 0.32% RMSE)
**Decision:** [[ADR_0003_kalman_fusion_over_simple_average]]
**Insight:** Multi-timescale filtering captures both short-term noise and long-term trends

### 2. HMM Identifies Stable Regimes
**Result:** 5-day avg regime duration, 35% Bull / 45% Neutral / 20% Bear
**Insight:** Regime-conditional features outperform unconditional by ~15%

### 3. Microstructure Features Add Alpha
**Result:** Top exec feature (ofi_1m) IC=0.15, 60-min horizon
**Insight:** Order flow imbalance predictive for 1-hour forward returns

### 4. Synthetic Quotes Limitation Real
**Result:** LOB reconstruction requires real depth (not available from MT5)
**Workaround:** 2 bps synthetic spread, focus on 1-min+ horizons

### 5. Tick Prediction Infeasible
**Result:** LSTM accuracy 52% (barely >random), slippage dominates
**Decision:** Deprecated (Phase 6)
**Insight:** Ultra-HF requires real LOB + co-location

---

## Experimental Features (Active Research)

**Beta (promising):**
1. Portfolio rebalancing optimization (20% cost reduction)
2. Vol forecasting (GARCH) — 70% directional accuracy
3. Explainable AI (SHAP values) — model debugging

**Alpha (needs validation):**
1. Spread trading (GC-SI, CL-RB) — Sharpe 0.6
2. Options data integration (IV surface)
3. Multi-timeframe ensemble — 10% improvement

**Prototype (early):**
1. RL alpha (PPO) — unstable
2. Sentiment analysis — IC <0.02 (deprecated)
3. Regime-switching Kalman — marginal gain

**Deprecated:**
- Twitter sentiment (expensive, noisy)
- Tick prediction (infeasible without real LOB)

---

## Research Backlog

**High Priority (Phase 6):**
- [ ] Feature selection (LASSO + RF importance)
- [ ] Tree models (XGBoost, LightGBM)
- [ ] Ensemble strategies (stacking, blending)
- [ ] Walk-forward validation (12 months)

**Medium Priority (Phase 7-8):**
- [ ] Dynamic position sizing (volatility-scaled Kelly)
- [ ] VaR computation (parametric, historical, MC)
- [ ] GARCH volatility forecasting

**Low Priority (Phase 9+):**
- [ ] RL alpha (revisit if GPU available)
- [ ] Sentiment analysis (revisit if better data source)
- [ ] Alternative data (satellite imagery)

---

## Literature Database

**Format:** BibTeX in `research/bibliography.bib`

**Categories:**
- Kalman filtering (15 papers)
- HMM / regime detection (12 papers)
- Microstructure (20 papers)
- Machine learning for finance (18 papers)
- Portfolio optimization (10 papers)
- Risk management (8 papers)

**Total:** ~80 papers

**Access:** Zotero library (local), exports to BibTeX

---

## Research Workflow

**1. Literature Review**
- Identify problem / research question
- Search papers (Google Scholar, SSRN, arXiv)
- Read abstracts, filter relevant
- Deep read top 3-5 papers
- Summarize in research note

**2. Prototyping**
- Implement algorithm (Python notebook)
- Test on synthetic data
- Validate on real data (1 month)
- Document results (research note)

**3. Validation**
- Backtest (walk-forward, 12 months)
- Compare to baseline
- Compute metrics (Sharpe, IC, drawdown)
- Decision: Promote, iterate, or deprecate

**4. Integration**
- Refactor prototype → production code
- Add tests (unit + integration)
- Document (feature spec)
- Deploy (phase plan)

**5. Monitoring**
- Track performance (live)
- Check for decay (IC, Sharpe)
- Quarterly review
- Update research log

---

## Research Principles

**1. Hypothesis-Driven**
- State hypothesis before research
- Define success criteria upfront
- Kill bad ideas fast (3 months max)

**2. Empirical Validation**
- Backtest on real data (not just synthetic)
- Walk-forward validation (not in-sample only)
- Out-of-sample testing (hold-out set)

**3. Publish or Perish (Internally)**
- Document findings (research notes)
- Share with future self (RAGD ingestion)
- Avoid rediscovering same mistakes

**4. Simplicity First**
- Start simple (linear model)
- Add complexity only if justified (>20% improvement)
- Complexity budget: Maintenance cost vs benefit

**5. Know When to Quit**
- IC <0.03 after 3 months → deprecate
- Sharpe <0.5 after validation → deprecate
- External dependency blocked → defer
- Cost >$1K/month → defer (solo researcher)

---

## Collaboration & References

**Internal:**
- Research notes (docs/07_RESEARCH/)
- Experimental features ([[EXPERIMENTAL_FEATURES]])
- Decision logs ([[ADR_INDEX]])

**External:**
- Zotero library (bibliography management)
- Jupyter notebooks (research/notebooks/)
- GitHub issues (research backlog)

**Community:**
- QuantConnect forums (algorithm discussions)
- r/algotrading (strategy ideas)
- SSRN / arXiv (latest papers)

---

## Related Documentation

- [[KALMAN_RESEARCH]] — Kalman filter theory + implementation
- [[HMM_REGIME_RESEARCH]] — Regime detection research
- [[MICROSTRUCTURE_LITERATURE]] — Market microstructure papers
- [[ALPHA_RESEARCH_LOG]] — Ongoing alpha research journal
- [[EXPERIMENTAL_FEATURES]] — Features under research
- [[DEPRECATED_FEATURES]] — Failed experiments (lessons learned)

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Monthly (after research sprints)

**How to Add Research:**
1. Create research note in docs/07_RESEARCH/
2. Add entry to this index (under appropriate phase)
3. Link from related docs ([[EXPERIMENTAL_FEATURES]], [[ADR_INDEX]])
4. Add papers to bibliography.bib (if applicable)
5. Update RAGD (`python scripts/build_ragd.py`)
