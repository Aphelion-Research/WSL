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
  - phase-4
  - regime-detection
---

# Phase 4: Regime Detection + Calendar (Complete)

**Timeline:** Q4 2025 - Q1 2026 (2 months)  
**Status:** ✓ Complete

---

## Goals

1. HMM regime detection (3-state model)
2. Calendar features (FOMC, NFP, etc.)
3. Regime-conditional features
4. Intelligence report generation

---

## Deliverables

### HMM Regime Detection
- [x] 3-state Hidden Markov Model
- [x] States: Bull/Neutral/Bear
- [x] Features: returns, volatility, volume
- [x] Online updating (incremental)
- [x] Regime transition probabilities

### Calendar Features
- [x] Economic calendar integration
- [x] FOMC meeting days
- [x] NFP (Non-Farm Payroll) release days
- [x] Fed speeches
- [x] G7 central bank events
- [x] Time-to-event features

### Regime-Conditional Features
- [x] Volatility by regime
- [x] Correlation by regime
- [x] Feature IC by regime
- [x] Regime duration tracking

### Intelligence Reports
- [x] Daily markdown reports
- [x] Regime summary
- [x] Feature performance
- [x] Anomaly highlights
- [x] RAGD ingestion

---

## Timeline

| Milestone | Date | Status |
|---|---|---|
| HMM prototype | 2025-12-01 | ✓ |
| 3-state model trained | 2025-12-15 | ✓ |
| Calendar integration | 2025-12-31 | ✓ |
| Intelligence reports | 2026-01-15 | ✓ |
| RAGD ingestion working | 2026-01-31 | ✓ |
| Phase 4 complete | 2026-01-31 | ✓ |

---

## Dependencies

**Requires Phase 2:**
- Multi-source data
- Feature generation framework

**Requires Phase 3:**
- Microstructure features (improve HMM signals)

**External:**
- Economic calendar API (free tier)
- hmmlearn library

---

## Success Criteria

- [x] HMM identifies 3 distinct regimes
- [x] Regime transitions < 5% per day (stable)
- [x] Calendar features: 20+ events per month
- [x] Intelligence reports generated daily
- [x] RAGD ingests reports successfully

---

## HMM Configuration

**States:**
1. Bull (uptrend + low vol)
2. Neutral (sideways + medium vol)
3. Bear (downtrend + high vol)

**Features:**
- 5-day returns
- 20-day volatility
- Volume ratio (current / avg)
- OFI 1m (from microstructure)

**Training:**
- 90 days initial training
- Daily incremental update (Baum-Welch)

---

## Key Decisions

- 3 states (not 2 or 4) — balance interpretability vs granularity
- Daily regime labels (not intraday) — stable enough for feature conditioning
- Online HMM updating — adapt to changing markets
- Intelligence reports to RAGD — agents query recent market context

---

## Blockers Encountered

1. **HMM overfitting** (Resolved)
   - Too many features → overfitting
   - Solution: Reduce to 4 key features

2. **Calendar API unstable** (Workaround)
   - Free tier rate limits
   - Solution: Cache locally, update weekly

3. **Report generation slow** (Resolved)
   - Initial markdown generation 10s
   - Solution: Template-based, <1s now

---

## Metrics

- **Regime distribution:** Bull 35%, Neutral 45%, Bear 20%
- **Avg regime duration:** 5 days
- **Calendar events:** 25/month average
- **Intelligence reports:** 60 generated (2 months)
- **RAGD chunks:** +300 from reports

---

## Regime Performance

| Regime | Return (avg) | Volatility | Sharpe |
|---|---|---|---|
| Bull | +0.8% | 5% | 1.2 |
| Neutral | +0.1% | 8% | 0.1 |
| Bear | -0.6% | 15% | -0.4 |

---

## Lessons Learned

**What worked:**
- HMM excellent at regime identification
- Calendar features useful (event-driven moves)
- Intelligence reports valuable for agent context

**What struggled:**
- HMM parameter tuning manual
- Calendar API limitations
- Report format evolved (3 revisions)

---

## Next Phase

→ [[PHASE_5]] — Documentation Brain Buildout (Current)
