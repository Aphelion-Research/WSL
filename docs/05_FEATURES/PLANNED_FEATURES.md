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
  - planned
  - roadmap
---

# Planned Features

**Purpose:** Catalog of features planned for Phase 6-10 (Alpha Research → Production).

**Status:** 35+ planned features across 6 phases.

---

## Phase 6: Advanced Alpha Research (Q2-Q3 2026)

### 6.1 ML Feature Selection
- **Purpose:** Reduce 400+ features → top 50 alpha-generating features
- **Methods:** LASSO, Random Forest importance, Recursive elimination
- **Target IC:** >0.05 (top 50)
- **Docs:** [[PHASE_6]]

### 6.2 Alpha Models (Linear)
- **Purpose:** Ridge, LASSO, ElasticNet regression models
- **Target Sharpe:** 0.8-1.2
- **Training:** 5-fold cross-validation
- **Docs:** [[PHASE_6]]

### 6.3 Alpha Models (Tree)
- **Purpose:** XGBoost, LightGBM, CatBoost
- **Target Sharpe:** 1.0-1.5
- **Advantage:** Non-linear relationships
- **Docs:** [[PHASE_6]]

### 6.4 Alpha Models (Neural)
- **Purpose:** LSTM, Transformer, Feedforward
- **Target Sharpe:** 1.2-1.8
- **Compute:** Requires GPU (cloud)
- **Docs:** [[PHASE_6]]

### 6.5 Ensemble Alpha Models
- **Purpose:** Stacking, blending, IC-weighted ensemble
- **Target Sharpe:** 1.5-2.0
- **Benefit:** Diversification across model types
- **Docs:** [[PHASE_6]]

### 6.6 Backtesting Framework
- **Purpose:** Event-driven backtester with realistic slippage
- **Features:** Almgren-Chriss impact, partial fills, regime conditioning
- **Validation:** Walk-forward (retrain every 3 months)
- **Docs:** [[PHASE_6]]

### 6.7 Portfolio Construction
- **Purpose:** Mean-variance optimization, risk parity, Kelly criterion
- **Rebalancing:** Weekly (>5% drift threshold)
- **Constraints:** Position limits, sector limits
- **Docs:** [[PHASE_6]]

---

## Phase 7: Live Paper Trading (Q3-Q4 2026)

### 7.1 Real-Time Alpha Engine
- **Purpose:** Generate live alpha signals from real-time ticks
- **Latency:** <1 second (tick → signal)
- **Models:** Load trained ensembles from Phase 6
- **Docs:** [[PHASE_7]]

### 7.2 Paper Trading Executor
- **Purpose:** Simulated order execution without real capital
- **Features:** Simulated slippage, position tracking, P&L
- **Duration:** 30+ days validation
- **Docs:** [[PHASE_7]]

### 7.3 Real-Time Dashboard
- **Purpose:** Monitor live performance (Streamlit/Dash)
- **Metrics:** Equity curve, Sharpe, drawdown, positions, regime
- **Refresh:** 1 second
- **Docs:** [[PHASE_7]]

### 7.4 Alert System
- **Purpose:** Email/Slack alerts for critical events
- **Types:** System crash, data loss, limit breaches, performance degradation
- **Delivery:** Real-time (critical), daily digest (warnings), weekly (info)
- **Docs:** [[PHASE_7]]

### 7.5 Regime Adaptation Validation
- **Purpose:** Verify HMM regime detection accuracy in real-time
- **Metric:** Regime assignments match offline processing
- **Monitoring:** Feature IC decay by regime
- **Docs:** [[PHASE_7]]

---

## Phase 8: Risk Management System (Q4 2026 - Q1 2027)

### 8.1 Pre-Trade Risk Checks
- **Purpose:** Enforce position, concentration, liquidity limits
- **Checks:** Position size, sector concentration, ADV participation
- **Rejection:** Orders violating limits rejected before execution
- **Docs:** [[PHASE_8]]

### 8.2 Real-Time VaR Computation
- **Purpose:** Value-at-Risk (99%, 1-day)
- **Methods:** Parametric, Historical, Monte Carlo
- **Limit:** <$50K VaR
- **Docs:** [[PHASE_8]]

### 8.3 Greeks Calculation
- **Purpose:** Delta, Gamma, Vega, Theta (if options used)
- **Use Case:** Hedge portfolio sensitivities
- **Docs:** [[PHASE_8]]

### 8.4 Dynamic Position Sizing
- **Purpose:** Volatility-scaled Kelly + regime + drawdown adjustments
- **Features:** Confidence-weighted sizing, adaptive rebalancing
- **Benefit:** Reduce drawdown by >20% vs fixed sizing
- **Docs:** [[PHASE_8]]

### 8.5 Circuit Breakers
- **Purpose:** Auto-halt trading on limit breaches
- **Triggers:** Daily loss >-5%, drawdown >15%, VaR >$50K
- **Kill Switch:** Manual emergency stop
- **Docs:** [[PHASE_8]]

### 8.6 Risk Dashboard
- **Purpose:** Real-time risk monitoring (VaR, exposure, correlations)
- **Stress Tests:** Market crash, vol spike, regime shift scenarios
- **Reporting:** Daily risk report, weekly review, monthly stress test
- **Docs:** [[PHASE_8]]

---

## Phase 9: Multi-Asset Expansion (Q1-Q3 2027)

### 9.1 Multi-Asset Data Pipeline
- **Purpose:** Expand from 1 asset (GC=F) → 12 assets
- **Assets:** 3 metals, 3 energy, 2 currencies, 2 indices, 2 bonds
- **Features:** 500 per asset (400 specific + 100 cross-asset)
- **Performance:** <15 min pipeline (parallel processing)
- **Docs:** [[PHASE_9]]

### 9.2 Cross-Asset Correlation Modeling
- **Purpose:** 12×12 correlation matrix with regime conditioning
- **Features:** Rolling correlation, correlation regime detection, breakdown alerts
- **Use Case:** Portfolio diversification, spread trading
- **Docs:** [[PHASE_9]]

### 9.3 Cross-Asset Features
- **Purpose:** Spreads (GC-SI, CL-RB), ratios (GC/SI), risk-on/risk-off indicators
- **Count:** ~100 cross-asset features
- **Benefit:** Improve single-asset alphas via cross-asset information
- **Docs:** [[PHASE_9]]

### 9.4 Asset-Specific Alpha Models
- **Purpose:** Tune separate models per asset (12 models)
- **Strategy:** Metals=trees, Energy=neural, Currencies=linear, Indices=ensemble, Bonds=linear
- **Target:** Portfolio Sharpe >1.5 (diversification benefit)
- **Docs:** [[PHASE_9]]

### 9.5 Multi-Asset Portfolio Optimization
- **Purpose:** Mean-variance with sector concentration limits
- **Constraints:** 15% max per asset, 40% max per sector
- **Rebalancing:** Daily check, rebalance if >3% drift
- **Docs:** [[PHASE_9]]

### 9.6 Sector Rotation Models
- **Purpose:** Tactical allocation across metals/energy/bonds/equities
- **Features:** Regime-based rotation, momentum, mean-reversion
- **Docs:** [[PHASE_9]]

---

## Phase 10: Production Hardening (Q4 2027 - Q1 2028)

### 10.1 High-Availability Deployment
- **Purpose:** 99.9% uptime via active-passive failover
- **Architecture:** NGINX LB, primary + standby nodes, DB replication
- **Failover:** <5 minutes
- **Docs:** [[PHASE_10]]

### 10.2 Disaster Recovery System
- **Purpose:** Backup + restore (RTO <1h, RPO <15min)
- **Backups:** Hourly incremental, daily full (S3/GCS encrypted)
- **Testing:** Weekly restore validation, quarterly DR drill
- **Docs:** [[PHASE_10]]

### 10.3 Secrets Management
- **Purpose:** Secure storage for API keys, credentials
- **Solution:** HashiCorp Vault / AWS Secrets Manager
- **Rotation:** 90-day policy
- **Docs:** [[PHASE_10]]

### 10.4 Audit Logging
- **Purpose:** Immutable log (all trades, config changes, logins)
- **Storage:** Append-only (S3 Object Lock)
- **Use Case:** Regulatory compliance, incident investigation
- **Docs:** [[PHASE_10]]

### 10.5 Performance Optimization
- **Purpose:** 10× throughput improvement
- **Techniques:** Vectorization, caching (Redis), parallelization (Ray/Dask), JIT (Numba)
- **Target:** <90 seconds pipeline (vs 15 minutes baseline)
- **Docs:** [[PHASE_10]]

### 10.6 CI/CD Pipeline
- **Purpose:** Automated testing + deployment (GitHub Actions)
- **Workflow:** Lint → Test → Build → Deploy (blue-green)
- **Deployment:** Zero downtime, automatic rollback on failure
- **Docs:** [[PHASE_10]]

### 10.7 Trade Logging & Compliance
- **Purpose:** Regulatory-ready audit trail
- **Content:** Every order, fill, cancel (timestamp, symbol, size, price, reason)
- **Reporting:** Daily P&L, weekly attribution, monthly risk report
- **Docs:** [[PHASE_10]]

### 10.8 Model Governance
- **Purpose:** Model versioning, approval, validation documentation
- **Contents:** Model assumptions, limitations, backtest results, walk-forward validation
- **Compliance:** SEC/CFTC/FCA ready
- **Docs:** [[PHASE_10]]

---

## Feature Prioritization

**P1 (Critical for Production):**
- Pre-trade risk checks (8.1)
- Circuit breakers (8.5)
- High-availability deployment (10.1)
- Disaster recovery (10.2)
- Audit logging (10.4)

**P2 (High Value):**
- ML feature selection (6.1)
- Ensemble alpha models (6.5)
- Real-time alpha engine (7.1)
- Dynamic position sizing (8.4)
- Multi-asset data pipeline (9.1)

**P3 (Medium Value):**
- Alpha models (tree/neural) (6.3, 6.4)
- Paper trading executor (7.2)
- Real-time VaR (8.2)
- Cross-asset features (9.3)
- Performance optimization (10.5)

**P4 (Nice to Have):**
- Alpha models (linear) (6.2)
- Alert system (7.4)
- Greeks calculation (8.3)
- Sector rotation models (9.6)
- CI/CD pipeline (10.6)

---

## Feature Dependencies

**Critical Path (blocks production):**
```
6.1 Feature Selection
  → 6.5 Ensemble Models
    → 7.1 Real-Time Alpha Engine
      → 8.1 Pre-Trade Checks
        → 8.5 Circuit Breakers
          → 10.1 HA Deployment
            → PRODUCTION READY
```

**Parallel Tracks:**
- **Risk:** 8.2 VaR → 8.4 Dynamic Sizing → 8.6 Risk Dashboard
- **Multi-Asset:** 9.1 Data Pipeline → 9.2 Correlation → 9.4 Asset-Specific Models → 9.5 Portfolio Opt
- **Infrastructure:** 10.2 DR → 10.3 Secrets → 10.4 Audit Log → 10.7 Trade Log

---

## Timeline Summary

| Phase | Duration | Key Features | Target Completion |
|---|---|---|---|
| Phase 6 | 3 months | Feature selection, alpha models, backtesting | 2026-08-31 |
| Phase 7 | 3 months | Paper trading, real-time dashboard, alerts | 2026-11-30 |
| Phase 8 | 3 months | Risk management, VaR, circuit breakers | 2027-02-28 |
| Phase 9 | 6 months | Multi-asset (12 assets), portfolio optimization | 2027-09-30 |
| Phase 10 | 3 months | Production hardening, HA, compliance | 2028-01-31 |

**Total:** 18 months (Phase 6 → Production)

---

## Estimated Effort

| Category | Features | Est. Dev Time |
|---|---|---|
| Alpha Research (Phase 6) | 7 | 3 months |
| Live Trading (Phase 7) | 5 | 3 months |
| Risk Management (Phase 8) | 6 | 3 months |
| Multi-Asset (Phase 9) | 6 | 6 months |
| Production (Phase 10) | 8 | 3 months |
| **Total** | **32** | **18 months** |

---

## Success Metrics

**Phase 6 Targets:**
- Sharpe ratio >1.0 (out-of-sample)
- Top 50 features IC >0.05
- Walk-forward validation: 12 months

**Phase 7 Targets:**
- Paper trading: 30+ days without intervention
- Sharpe within 20% of backtest
- Latency <1 second

**Phase 8 Targets:**
- Zero limit breaches
- VaR accuracy >95% days
- Drawdown reduction >20% vs fixed sizing

**Phase 9 Targets:**
- 12 assets live
- Portfolio Sharpe >1.5
- Pipeline latency <15 min

**Phase 10 Targets:**
- 99.9% uptime
- RTO <1h, RPO <15min
- 10× throughput improvement
- Zero critical/high security vulnerabilities

---

## Related Documentation

- [[CURRENT_FEATURES]] — Operational features (Phase 0-5)
- [[EXPERIMENTAL_FEATURES]] — Research features (not production-ready)
- [[DEPRECATED_FEATURES]] — Retired features
- [[FEATURE_DEPENDENCY_MAP]] — Dependency visualization
- [[FEATURE_PRIORITY_MATRIX]] — Development prioritization
- [[PHASE_6]] through [[PHASE_10]] — Detailed phase roadmaps

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After each phase planning

**How to Add:**
1. Identify feature need
2. Assign to phase (6-10)
3. Add entry here (under phase section)
4. Create detailed spec if starting development
5. Move to [[CURRENT_FEATURES]] when operational
