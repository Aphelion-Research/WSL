---
doc_type: reference
system: Dominion
ragd_priority: 6
audience:
  - maintainer
  - owner
status: active
last_reviewed: 2026-05-19
tags:
  - features
  - prioritization
  - planning
---

# Feature Priority Matrix

**Purpose:** Framework for prioritizing feature development using value/effort/risk scoring.

**Status:** Current as of Phase 5 (Q2 2026).

---

## Prioritization Framework

**Scoring Dimensions:**

1. **Value (1-10):** Business impact, alpha generation, risk reduction
2. **Effort (1-10):** Development time, complexity, testing burden
3. **Risk (1-10):** Technical risk, external dependencies, unknowns

**Priority Score:**
```
Priority = (Value × 2) - Effort - Risk
Range: -18 to +18
Higher = better
```

**Priority Tiers:**
- **P1 (Critical):** Score ≥10, must-have for production
- **P2 (High):** Score 5-9, high ROI
- **P3 (Medium):** Score 0-4, nice-to-have
- **P4 (Low):** Score <0, defer or drop

---

## Phase 6: Advanced Alpha Research

| Feature | Value | Effort | Risk | Score | Tier | Notes |
|---|---|---|---|---|---|---|
| ML Feature Selection | 9 | 6 | 3 | 9 | **P1** | Reduces noise, improves all models |
| Ensemble Alpha Models | 9 | 7 | 4 | 7 | **P2** | Diversification benefit |
| Backtesting Framework | 8 | 8 | 5 | 3 | **P3** | Critical but complex |
| Tree Models (XGBoost) | 8 | 5 | 2 | 9 | **P1** | Best Sharpe/effort ratio |
| Neural Models (LSTM) | 7 | 9 | 7 | -2 | **P4** | High effort, GPU needed |
| Portfolio Construction | 7 | 6 | 4 | 4 | **P3** | Needed but not urgent |
| Linear Models (Ridge) | 6 | 4 | 2 | 6 | **P2** | Simple, fast, stable |

**Recommendation:**
- Phase 6a: Feature Selection + Tree Models (4 weeks)
- Phase 6b: Ensemble + Linear Models (4 weeks)
- Phase 6c: Backtesting + Portfolio (4 weeks)
- Defer: Neural models (Phase 9+)

---

## Phase 7: Live Paper Trading

| Feature | Value | Effort | Risk | Score | Tier | Notes |
|---|---|---|---|---|---|---|
| Real-Time Alpha Engine | 10 | 7 | 6 | 7 | **P2** | Critical but complex |
| Paper Executor | 10 | 6 | 5 | 9 | **P1** | Must-have for validation |
| Alert System | 8 | 4 | 2 | 10 | **P1** | High ROI, prevents losses |
| Dashboard | 7 | 5 | 3 | 6 | **P2** | Useful but not critical |
| Regime Adaptation | 6 | 3 | 4 | 5 | **P2** | Validates HMM in real-time |

**Recommendation:**
- Phase 7a: Paper Executor + Alert System (6 weeks)
- Phase 7b: Real-Time Alpha + Dashboard (6 weeks)

---

## Phase 8: Risk Management System

| Feature | Value | Effort | Risk | Score | Tier | Notes |
|---|---|---|---|---|---|---|
| Circuit Breakers | 10 | 4 | 2 | 14 | **P1** | Prevents catastrophic loss |
| Pre-Trade Risk Checks | 10 | 5 | 3 | 12 | **P1** | Critical safety net |
| Dynamic Position Sizing | 9 | 6 | 4 | 8 | **P2** | 20% drawdown reduction |
| Real-Time VaR | 8 | 7 | 5 | 4 | **P3** | Useful but complex |
| Risk Dashboard | 7 | 5 | 3 | 6 | **P2** | Monitoring + transparency |
| Greeks Calculation | 5 | 6 | 4 | 0 | **P3** | Only if options used |

**Recommendation:**
- Phase 8a: Pre-Trade Checks + Circuit Breakers (4 weeks) — **CRITICAL**
- Phase 8b: Dynamic Sizing + Risk Dashboard (4 weeks)
- Phase 8c: VaR (4 weeks)
- Defer: Greeks (only if Phase 9 adds options)

---

## Phase 9: Multi-Asset Expansion

| Feature | Value | Effort | Risk | Score | Tier | Notes |
|---|---|---|---|---|---|---|
| Multi-Asset Pipeline | 9 | 8 | 6 | 4 | **P3** | High effort, high payoff |
| Asset-Specific Models | 9 | 7 | 5 | 7 | **P2** | Tuning per asset improves Sharpe |
| Cross-Asset Correlation | 8 | 5 | 4 | 7 | **P2** | Diversification + spreads |
| Multi-Asset Portfolio | 8 | 6 | 5 | 5 | **P3** | Optimization complex |
| Cross-Asset Features | 7 | 4 | 3 | 7 | **P2** | Spreads, ratios, rotation |
| Sector Rotation Models | 6 | 6 | 5 | 1 | **P3** | Nice-to-have |

**Recommendation:**
- Phase 9a: Multi-Asset Pipeline + Cross-Asset Correlation (8 weeks)
- Phase 9b: Cross-Asset Features + Asset-Specific Models (8 weeks)
- Phase 9c: Multi-Asset Portfolio (8 weeks)
- Defer: Sector Rotation (Phase 10+)

---

## Phase 10: Production Hardening

| Feature | Value | Effort | Risk | Score | Tier | Notes |
|---|---|---|---|---|---|---|
| High-Availability | 10 | 7 | 6 | 7 | **P2** | 99.9% uptime requirement |
| Disaster Recovery | 10 | 6 | 5 | 9 | **P1** | Prevents data loss |
| Audit Logging | 10 | 4 | 2 | 14 | **P1** | Regulatory compliance |
| Secrets Management | 9 | 5 | 3 | 10 | **P1** | Security critical |
| Performance Opt (10×) | 8 | 8 | 6 | 2 | **P3** | Nice-to-have, not urgent |
| CI/CD Pipeline | 7 | 6 | 4 | 4 | **P3** | Quality-of-life |
| Trade Logging | 7 | 3 | 2 | 9 | **P1** | Compliance |
| Model Governance | 6 | 4 | 3 | 5 | **P2** | Documentation burden |

**Recommendation:**
- Phase 10a: Secrets + Audit Log + Trade Log (4 weeks) — **COMPLIANCE**
- Phase 10b: Disaster Recovery (4 weeks) — **SAFETY**
- Phase 10c: HA + CI/CD + Perf Opt (4 weeks)

---

## Cross-Phase Prioritization

**If forced to cut scope, drop in this order:**

### Tier 1: Must-Have (Blocks Production)
1. Pre-Trade Risk Checks (8.1)
2. Circuit Breakers (8.5)
3. Disaster Recovery (10.2)
4. Audit Logging (10.4)
5. Secrets Management (10.3)
6. Trade Logging (10.7)

### Tier 2: High ROI (Strong Alpha or Risk Reduction)
7. ML Feature Selection (6.1)
8. Tree Models (6.3)
9. Paper Executor (7.2)
10. Alert System (7.4)
11. Dynamic Position Sizing (8.4)
12. Asset-Specific Models (9.4)

### Tier 3: Nice-to-Have (Incremental Gains)
13. Ensemble Models (6.5)
14. Real-Time Dashboard (7.3)
15. VaR (8.2)
16. Multi-Asset Pipeline (9.1)
17. HA Deployment (10.1)
18. CI/CD (10.6)

### Tier 4: Optional (Defer or Drop)
19. Neural Models (6.4)
20. Greeks (8.3)
21. Sector Rotation (9.6)
22. Performance Opt (10.5)

---

## ROI Analysis

**Top 10 Features by ROI (Value/Effort):**

| Rank | Feature | Value | Effort | ROI | Phase |
|---|---|---|---|---|---|
| 1 | Circuit Breakers | 10 | 4 | 2.50 | 8 |
| 2 | Alert System | 8 | 4 | 2.00 | 7 |
| 3 | Pre-Trade Checks | 10 | 5 | 2.00 | 8 |
| 4 | Audit Logging | 10 | 4 | 2.50 | 10 |
| 5 | Secrets Management | 9 | 5 | 1.80 | 10 |
| 6 | Trade Logging | 7 | 3 | 2.33 | 10 |
| 7 | Tree Models | 8 | 5 | 1.60 | 6 |
| 8 | Paper Executor | 10 | 6 | 1.67 | 7 |
| 9 | Disaster Recovery | 10 | 6 | 1.67 | 10 |
| 10 | ML Feature Selection | 9 | 6 | 1.50 | 6 |

**Insight:**
- Phase 8 + 10 dominate top 10 (risk management + infrastructure)
- Phase 6 alpha research has lower ROI (complex, uncertain)
- Quick wins: Alerts, Circuit Breakers, Logging (high value, low effort)

---

## Risk-Adjusted Prioritization

**Features with high technical risk (defer if possible):**

| Feature | Risk | Mitigation |
|---|---|---|
| Neural Models (6.4) | 7 | Defer until GPU available |
| Multi-Asset Pipeline (9.1) | 6 | Start with 3 assets, expand gradually |
| HA Deployment (10.1) | 6 | Validate failover extensively |
| Performance Opt (10.5) | 6 | Benchmark before optimizing |
| VaR (8.2) | 5 | Use 3 methods (parametric, historical, MC) |
| Backtesting (6.6) | 5 | Start simple, iterate |

**De-risking Strategy:**
1. Prototype high-risk features early (kill bad ideas fast)
2. Incremental rollout (3 assets → 12 assets)
3. Extensive testing (HA, VaR validation)
4. Fallback plans (VaR fallback to simple vol scaling)

---

## Experimental Features (Research)

**Experimental features ranked by potential:**

| Feature | Value (If Works) | Effort | Risk | Likelihood | Notes |
|---|---|---|---|---|---|
| Portfolio Rebalancing Opt | 8 | 6 | 4 | 60% | Beta, shows promise |
| Vol Forecasting (GARCH) | 7 | 4 | 3 | 70% | Beta, better than rolling std |
| Explainable AI (SHAP) | 7 | 5 | 3 | 80% | Beta, useful for debugging |
| Spread Trading | 6 | 5 | 5 | 40% | Alpha, modest Sharpe |
| Multi-Timeframe Ensemble | 6 | 8 | 4 | 50% | Prototype, marginal gain |
| Options Data | 6 | 7 | 6 | 30% | Alpha, expensive |
| RL Alpha | 5 | 9 | 8 | 20% | Prototype, unstable |
| Sentiment Analysis | 4 | 7 | 7 | 10% | Deprecated (IC <0.02) |
| Tick Prediction | 3 | 8 | 8 | 5% | Deprecated (noise >> signal) |

**Recommendation:**
- Promote to Phase 8: GARCH, Portfolio Rebalancing Opt
- Continue research: SHAP, Spread Trading
- Deprioritize: RL, Sentiment, Tick Prediction

---

## Decision Rules

**When to prioritize a feature:**

1. **Blocks production launch** → P1 (always do)
2. **Prevents catastrophic loss** → P1 (risk management)
3. **ROI >1.5** → P2 (high value/effort)
4. **Regulatory requirement** → P1 (compliance)
5. **Sharpe improvement >0.2** → P2 (alpha generation)
6. **External dependency resolved** → Bump up 1 tier

**When to defer a feature:**

1. **Risk >6** → Defer until mitigated
2. **ROI <0.8** → P4 (low priority)
3. **External dependency blocked** → Defer
4. **Research inconclusive** → Prototype first
5. **Maintenance burden >benefit** → Drop

**When to drop a feature:**

1. **IC <0.03 after 3+ months** → Drop
2. **Sharpe <0.5 after validation** → Drop
3. **Cost >$1K/month** → Drop (solo researcher)
4. **Complexity >> benefit** → Drop
5. **Better alternative exists** → Drop, use alternative

---

## Related Documentation

- [[PLANNED_FEATURES]] — Roadmap (Phase 6-10)
- [[FEATURE_DEPENDENCY_MAP]] — Dependency visualization
- [[CURRENT_FEATURES]] — Operational features
- [[EXPERIMENTAL_FEATURES]] — Research features
- [[PHASE_6]] through [[PHASE_10]] — Detailed phase plans

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Monthly (during phase planning)

**How to Use:**
1. Score new features (Value, Effort, Risk)
2. Compute priority score
3. Assign tier (P1/P2/P3/P4)
4. Sequence by dependencies + tier
5. Re-evaluate quarterly (adjust scores based on learnings)
