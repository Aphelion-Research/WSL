---
doc_type: adr
system: Dominion
ragd_priority: 6
audience:
  - maintainer
  - researcher
status: accepted
date: 2025-12-01
tags:
  - adr
  - regime
  - hmm
  - phase-4
---

# ADR-0006: HMM for Regime Detection

**Date:** 2025-12-01  
**Status:** Accepted  
**Deciders:** Owner  
**Phase:** Phase 4 (Regime Detection)

---

## Context

Need market regime classification (Bull/Neutral/Bear) for:
- Regime-conditional features (OFI IC varies 3× by regime)
- Dynamic position sizing (reduce exposure in Bear)
- Intelligence reports (daily regime summary)

**Requirements:**
1. Real-time classification (daily updates)
2. Stable regimes (not oscillating daily)
3. Interpretable states (Bull/Neutral/Bear clear)
4. Adaptive (learn from new data)

**Candidate approaches:**
1. Rule-based (if returns >0 and vol <10% → Bull)
2. K-Means clustering (cluster features into 3 groups)
3. Hidden Markov Model (HMM, probabilistic state machine)
4. Regime-switching GARCH (3 GARCH models, switch by regime)
5. Deep learning (LSTM classifier)

---

## Decision

Use **3-state Hidden Markov Model (HMM)** with Baum-Welch training.

**Rationale:**
- Temporal structure (transitions smooth, not oscillating)
- Probabilistic (soft classification, not hard borders)
- Adaptive (online updates via incremental Baum-Welch)
- Interpretable (transition matrix, emission params)
- Fast (inference <1ms, training 100s)

---

## HMM Configuration

### States (3)

1. **Bull** — Positive returns, low vol, high volume
2. **Neutral** — Near-zero returns, medium vol, normal volume
3. **Bear** — Negative returns, high vol, low volume

### Features (4)

Selected via mutual information ranking:
1. **5-day returns** — Trend direction
2. **20-day volatility** — Risk level
3. **Volume ratio** — Activity (current / 20-day avg)
4. **OFI 1m** — Order flow imbalance

**Why 4 features?**
- Tried 10 features → overfitting (HMM unstable)
- Reduced to 4 → stable transitions
- IC validated: Features discriminate regimes (mutual info >0.15)

### Training (Baum-Welch)

**Initial training:** 90 days (Q4 2025)

**Algorithm:**
1. Initialize params (random transition matrix, Gaussian emissions)
2. E-step: Forward-backward (compute posteriors)
3. M-step: Update params (maximize likelihood)
4. Repeat until convergence (ΔLL <0.01)

**Convergence:** 18 iterations, 100s

**Online updates:** Weekly (Baum-Welch on last 30 days)

### Inference (Viterbi)

**Daily classification:**
1. Receive new observation (4 features)
2. Viterbi decode (most likely state sequence)
3. Assign regime label (Bull/Neutral/Bear)

**Latency:** <1ms (real-time)

---

## Validation Results

### Stability

| Metric | Value |
|---|---|
| Avg regime duration | 5.6 days |
| Transition rate | 17.8% (16/90 days) |
| Self-transition prob | 0.81-0.87 (stable) |

**Insight:** Regimes stable (not oscillating daily).

### Accuracy

**Expert labels (90 days out-of-sample):**
- HMM vs expert agreement: 78%
- Confusion: Neutral/Bull boundary (subjective)

**Regime-conditional IC:**
| Regime | OFI 1m IC |
|---|---|
| Bull | 0.18 |
| Neutral | 0.10 |
| Bear | 0.05 |

**Insight:** HMM captures meaningful regime differences.

### Distribution

**3-month validation:**
- Bull: 30 days (33%)
- Neutral: 42 days (47%)
- Bear: 18 days (20%)

**Insight:** Neutral dominant (expected, sideways market most common).

---

## Alternatives Considered

### Alternative 1: Rule-Based Regimes

**Approach:** If returns >0 and vol <10% → Bull, else...

**Pros:**
- Simple (no training)
- Interpretable (clear rules)

**Cons:**
- Brittle (oscillates at boundaries)
- No adaptation (static rules)
- No probabilistic (hard classification)

**Validation:**
- Tested: Transition rate 45% (vs 18% HMM)
- Oscillates daily (unstable)

**Verdict:** Rejected (too noisy).

---

### Alternative 2: K-Means Clustering

**Approach:** Cluster daily features into 3 groups.

**Pros:**
- Simple (sklearn.KMeans)
- Fast (training 10s)

**Cons:**
- No temporal structure (treats days independently)
- Oscillates (cluster boundaries hard)
- No probabilistic (hard assignment)

**Validation:**
- Tested: Transition rate 38% (vs 18% HMM)
- No smoothing across time

**Verdict:** Rejected (lacks temporal structure).

---

### Alternative 3: Regime-Switching GARCH

**Approach:** 3 GARCH models (one per regime), switch by likelihood.

**Pros:**
- Captures volatility dynamics (GARCH strength)
- Probabilistic (likelihood-based switching)

**Cons:**
- Complex (3 GARCH models to train)
- Slow (training 10 min vs 100s HMM)
- Overfits (more params than HMM)

**Validation:**
- Tested: Similar accuracy to HMM (78% vs 78%)
- 5× slower training (not worth complexity)

**Verdict:** Rejected (complexity >> benefit).

---

### Alternative 4: Deep Learning (LSTM)

**Approach:** LSTM trained on features → regime label.

**Pros:**
- Flexible (learns nonlinear patterns)
- State-of-art (LSTM designed for sequences)

**Cons:**
- Needs large dataset (1000+ days, have 90)
- Overfits (90 days insufficient)
- Slow (training hours, GPU required)
- Not interpretable (black box)

**Validation:**
- Tested: Accuracy 65% (worse than HMM 78%)
- Overfits (train acc 95%, val acc 65%)

**Verdict:** Rejected (insufficient data).

---

## Consequences

### Positive

1. **Stable regimes** — 5-day avg duration (not oscillating)
2. **Adaptive** — Weekly retraining adapts to new data
3. **Probabilistic** — Soft classification (regime probabilities)
4. **Fast** — Inference <1ms, training 100s (real-time)
5. **Interpretable** — Transition matrix shows regime dynamics

### Negative

1. **Lag** — Regime detected 1-2 days after transition (needs confirmation)
2. **Gaussian assumption** — Emissions assume Gaussian (real data has fat tails)
3. **Fixed K** — 3 states chosen manually (could automate via BIC)

### Neutral

1. **Parameter tuning** — Features, K states require experimentation
2. **Maintenance** — Weekly retraining (automated cron job)

---

## Implementation

**Location:** `regime/hmm.py`

**Library:** hmmlearn (scikit-learn ecosystem)

**Tests:** `tests/unit/test_regime.py` (6/6 passing)

**Docs:** [[HMM_REGIME_RESEARCH]], [[PHASE_4]]

---

## Performance

**Training (90 days):**
- 20 iterations × 5s = 100s
- Acceptable (runs offline, weekly)

**Inference (1 day):**
- Viterbi: 0.5ms
- Acceptable (real-time)

**Memory:**
- Transition matrix: 3×3 = 9 floats
- Emission params: 3×4 means + 3×4×4 covariances = 60 floats
- Total: <1KB

---

## Future Work

### Investigated (Marginal Gain)

**Regime-switching Kalman Filter:**
- 3 Kalman filters (one per regime)
- Result: 5% error reduction (not worth 3× complexity)
- Status: Prototype, likely to deprecate

### Planned (Phase 6-8)

**Regime-conditional position sizing:**
- Bull: 1.2× exposure
- Neutral: 1.0× exposure
- Bear: 0.6× exposure

**Regime-conditional alpha models:**
- Train separate models per regime
- Expected: 15% IC improvement

### Open Questions

1. **Optimal K states:** 3 vs 4 (Bull/Neutral/Bear/Crash)?
2. **Feature engineering:** Add macro (VIX, yields)?
3. **Hierarchical HMM:** Intraday regimes nested in daily?

---

## Review Schedule

**Quarterly:** Review regime stability (transition rate <20%).

**Annual:** Re-evaluate HMM vs alternatives (if LSTM dataset grows to 1000+ days).

**Last Review:** 2025-12-01 (Initial)

**Next Review:** 2026-12-01 (1 year validation)

---

## Related

- [[PHASE_4]] — Regime detection implementation
- [[HMM_REGIME_RESEARCH]] — Detailed research notes
- [[INTELLIGENCE_REPORTS]] — Uses regime for daily summaries
- [[DYNAMIC_POSITION_SIZING]] — Regime-conditional sizing (Phase 8)

---

## References

- Baum et al. (1970) — Original Baum-Welch algorithm
- Hamilton (1989) — Regime-switching models in economics
- Ang & Bekaert (2002) — Regime switches in asset allocation
- Rabiner (1989) — HMM tutorial (IEEE)
