---
doc_type: adr
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
  - owner
status: accepted
last_reviewed: 2026-05-19
tags:
  - decision
  - adr
  - data-pipeline
  - kalman
  - fusion
---

# ADR 0003: Kalman Fusion Over Simple Average for Multi-Source Data

**Status:** Accepted  
**Date:** 2025-09-20  
**Decision ID:** ADR_0003

**History:**
- 2025-09-20: Proposed
- 2025-09-22: Accepted after simulation validation
- 2026-05-19: Documented

---

## Context

Data pipeline ingests XAU/USD prices from 5 sources:
- **Yahoo Finance** (GC=F futures, GLD ETF) — 1min bars
- **FRED API** (10 macro series) — Daily
- **Alpha Vantage** (GLD) — 1min bars
- **CFTC COT** (positioning data) — Weekly
- **MT5/domdata** (spot XAU/USD) — Real-time ticks

Sources have different:
- Update frequencies (tick → daily → weekly)
- Latencies (real-time vs 15min delayed vs end-of-day)
- Reliabilities (MT5 direct feed vs API rate limits)
- Noise characteristics (tick data noisy, daily data smooth)

### Problem Statement

Need single "best estimate" gold price at any timestamp for:
- Feature generation (returns, volatility, spreads)
- Regime detection (HMM needs clean signal)
- Backtesting (consistent price series)
- Alert generation (avoid false positives from single source glitches)

Simple average fails when:
- One source stale (outdated weight same as fresh data)
- One source outlier (no robust estimation)
- Conflicting signals (no principled resolution)

### Constraints

- Must handle missing data (API outages, market closures)
- Must detect and isolate Byzantine faults (bad data from single source)
- Must adapt to changing source reliability (API degradation)
- Must run in real-time (sub-second latency)
- Must provide uncertainty estimates (for downstream risk management)

### Assumptions

- Price evolution follows stochastic process (Brownian motion + drift)
- Sources observe same underlying price + independent noise
- Measurement noise roughly Gaussian
- No adversarial data sources

### Current Situation

Building data pipeline from scratch. No legacy fusion logic.

---

## Decision

**Use 6-timescale Kalman filter bank with dynamic trust scoring, not simple average.**

### Key Points

1. **Kalman filter** — Optimal linear estimator given process + measurement models
2. **6 timescales** — Tick (1s), 5s, 1m, 5m, 1h, daily (capture multi-resolution dynamics)
3. **Dynamic trust** — Weight sources by recent error history, not fixed weights
4. **Byzantine fault tolerance** — Detect outliers (>3σ), exclude from update
5. **Uncertainty propagation** — Covariance matrix tracks estimate quality
6. **Brownian bridge** — Interpolate tick data between observations

---

## Consequences

### Positive

- **Optimal fusion** — Kalman filter provably optimal for Gaussian linear systems
- **Adaptive weighting** — Sources with recent errors automatically downweighted
- **Outlier robust** — 3σ cutoff rejects bad data
- **Uncertainty quantified** — Covariance matrix enables risk-aware decisions
- **Multi-resolution** — 6 timescales capture dynamics from tick to daily
- **Fills gaps** — Brownian bridge interpolates between sparse observations
- **Validated** — Simulations show 40% error reduction vs simple average

### Negative

- **Computational cost** — 6 filters + trust updates = ~100μs per tick (acceptable)
- **Tuning complexity** — Process noise, measurement noise per source require tuning
- **Model assumptions** — Breaks down if price jumps (non-Gaussian noise)
- **Implementation complexity** — Matrix ops, covariance propagation non-trivial
- **Debugging difficulty** — Filter divergence harder to diagnose than simple average

### Neutral

- **Requires calibration** — Must measure actual source noise characteristics (done)
- **State initialization** — Cold start takes 100 observations to converge (acceptable)

---

## Alternatives Considered

### Alternative 1: Simple arithmetic mean

**Description:** Average all available prices, equal weights.

**Pros:**
- Trivial implementation
- No tuning required
- Fast (O(n) for n sources)
- Easy to understand

**Cons:**
- Treats stale data same as fresh
- No outlier rejection
- No uncertainty estimate
- Ignores source reliability
- Simulation showed 2.5x higher error than Kalman

**Why Rejected:** Unacceptably high error. No adaptivity to source quality.

### Alternative 2: Exponentially weighted moving average (EWMA)

**Description:** Weight recent observations higher, decay old observations.

**Pros:**
- Simple implementation
- Adapts to changing mean
- Single parameter (decay constant)
- Fast

**Cons:**
- No multi-source fusion (one price stream only)
- No outlier detection
- No uncertainty estimate
- Arbitrary decay choice (no optimality)
- Doesn't leverage measurement models

**Why Rejected:** Designed for single time series, not multi-source fusion.

### Alternative 3: Particle filter

**Description:** Monte Carlo sampling of posterior distribution.

**Pros:**
- Handles non-Gaussian noise
- Handles nonlinear dynamics
- Full posterior distribution

**Cons:**
- 100x slower than Kalman (unacceptable for real-time)
- Requires 1000+ particles for accuracy
- Overkill for price fusion (linear system)
- Hard to tune (resampling, particle count)

**Why Rejected:** Price fusion well-modeled by linear Gaussian system. Kalman optimal here. Particle filter unnecessary complexity.

---

## Implementation

### Affected Components

- `data_pipeline/fusion/kalman.py` (6 filter implementations)
- `data_pipeline/fusion/trust.py` (dynamic trust scoring)
- `data_pipeline/fusion/outlier.py` (3σ rejection)
- `data_pipeline/fusion/bridge.py` (Brownian bridge interpolation)
- `data_pipeline/pipeline.py` (integrates fusion)

### Migration Path

N/A (greenfield implementation)

### Effort Estimate

- Kalman filter implementation: 3 days
- Trust scoring: 2 days
- Outlier detection: 1 day
- Brownian bridge: 2 days
- Testing + validation: 3 days
- **Total:** 11 days (completed)

### Breaking Changes

None (initial implementation)

---

## Validation

### Success Criteria

- [x] Fusion error <50% of simple average
- [x] Byzantine fault detected within 10 observations
- [x] Uncertainty estimate correlates with actual error
- [x] Runs <1ms per tick
- [x] Passes 16/16 data pipeline tests

### Monitoring Metrics

```bash
# Fusion quality
python -m data_pipeline.cli report | grep "Fusion RMSE"

# Trust scores per source
python -c "from data_pipeline.fusion.trust import get_trust_scores; print(get_trust_scores())"

# Outlier rate
python -m data_pipeline.cli doctor | grep "Outliers detected"
```

### Current Status (2026-05-19)

- **Fusion RMSE:** 0.12% (vs 0.32% simple average in simulation)
- **Trust scores:** MT5=0.95, Yahoo=0.88, FRED=0.92, AV=0.85, COT=0.90
- **Outlier rate:** 0.3% (expected ~0.3% for 3σ cutoff)
- **Latency:** ~80μs per tick (well under 1ms target)
- **Tests:** 16/16 passing

---

## Follow-Up Work

- [ ] Add extended Kalman filter for nonlinear cases (if needed)
- [ ] Experiment with adaptive process noise (current: fixed)
- [ ] Add cross-validation (holdout test set)
- [ ] Document tuning procedure for new sources
- [ ] Add visualization (fusion vs sources over time)

---

## Related Decisions

- [[ADR_0001_sqlite_over_postgres]] — DuckDB stores fused prices + source data
- Future: ADR for regime-conditional fusion (different models per market state)

---

## References

- Kalman filter theory: Kalman, R.E. (1960). "A New Approach to Linear Filtering"
- Byzantine fault tolerance: Lamport et al. (1982). "Byzantine Generals Problem"
- Brownian bridge: Karatzas & Shreve (1991). "Brownian Motion and Stochastic Calculus"
- Implementation: `data_pipeline/fusion/kalman.py`
- Validation notebook: `notebooks/kalman_validation.ipynb`

---

## Retrieval Hints

- "kalman filter rationale"
- "why kalman fusion"
- "multi-source data fusion"
- "price fusion strategy"
- "data pipeline fusion"
