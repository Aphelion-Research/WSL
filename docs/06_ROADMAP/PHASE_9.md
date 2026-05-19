---
doc_type: roadmap
system: Dominion
ragd_priority: 5
audience:
  - maintainer
  - owner
status: planned
last_reviewed: 2026-05-19
tags:
  - roadmap
  - phase-9
  - multi-asset
  - scaling
---

# Phase 9: Multi-Asset Expansion (Planned)

**Timeline:** Q1 2027 - Q3 2027 (6 months)  
**Status:** 📋 Planned

---

## Goals

1. Expand from GC=F (gold futures) to 10+ assets
2. Cross-asset correlation modeling
3. Multi-asset portfolio optimization
4. Asset-specific alpha models
5. Unified risk management

---

## Deliverables

### Asset Universe Expansion
- [ ] 3 metals (GC=F, SI=F, HG=F — gold, silver, copper)
- [ ] 3 energy (CL=F, NG=F, RB=F — oil, nat gas, gasoline)
- [ ] 2 currencies (6E=F, 6J=F — EUR/USD, JPY/USD)
- [ ] 2 indices (ES=F, NQ=F — S&P 500, Nasdaq)
- [ ] 2 bonds (ZN=F, ZB=F — 10Y, 30Y Treasuries)

### Data Pipeline Scaling
- [ ] Multi-asset tick ingestion
- [ ] Unified feature generation (400+ per asset)
- [ ] Cross-asset features (correlations, spreads, ratios)
- [ ] Asset-specific calendars (FOMC, EIA, NFP)
- [ ] 12×400 = 4800 features total

### Alpha Models
- [ ] Asset-specific models (tuned per asset)
- [ ] Cross-asset models (use correlations)
- [ ] Sector rotation models (metals vs energy vs bonds)
- [ ] Spread trading models (GC-SI, CL-RB)
- [ ] Ensemble per asset

### Portfolio Optimization
- [ ] Multi-asset mean-variance
- [ ] Cross-asset correlation matrix (12×12)
- [ ] Risk budgeting (allocate risk per asset)
- [ ] Dynamic rebalancing (asset-level)
- [ ] Regime-conditional allocation

### Risk Management
- [ ] Asset-level VaR
- [ ] Portfolio VaR (correlated)
- [ ] Cross-asset exposure tracking
- [ ] Sector concentration limits
- [ ] Unified circuit breakers

---

## Timeline

| Milestone | Date | Status |
|---|---|---|
| 3 metals live | 2027-03-31 | Pending |
| 3 energy live | 2027-04-30 | Pending |
| 2 currencies live | 2027-05-31 | Pending |
| 2 indices live | 2027-06-30 | Pending |
| 2 bonds live | 2027-07-31 | Pending |
| Portfolio optimization | 2027-08-31 | Pending |
| Phase 9 complete | 2027-09-30 | Pending |

---

## Dependencies

**Requires Phase 8:**
- Risk management system (extend to multi-asset)
- VaR computation (cross-asset)
- Circuit breakers

**Requires Phase 6:**
- Alpha models (replicate per asset)
- Feature selection (apply per asset)
- Backtesting framework (multi-asset)

**Requires Phase 2:**
- Data pipeline (scale to 12 assets)
- Kalman fusion (replicate per asset)
- Trust scoring

**External:**
- MT5 access to all 12 symbols
- Additional data sources (EIA for energy, CFTC for positioning)
- Increased compute (12× feature generation)

---

## Success Criteria

- [ ] 12 assets ingesting live
- [ ] 4800 features computed daily
- [ ] Asset-specific alphas: Sharpe >0.8 each
- [ ] Portfolio Sharpe >1.5 (diversification benefit)
- [ ] Cross-asset VaR accurate (>95% days)
- [ ] Zero data loss across assets

---

## Asset Universe

### Metals (3)
- **GC=F** (Gold): Safe haven, inflation hedge
- **SI=F** (Silver): Industrial + precious metal hybrid
- **HG=F** (Copper): Economic activity proxy

**Correlations:**
- GC-SI: 0.7 (high)
- GC-HG: 0.3 (low)
- SI-HG: 0.5 (medium)

**Alpha strategy:**
- GC: Safe-haven flows, Fed policy
- SI: Industrial demand + safe-haven
- HG: China growth, construction

### Energy (3)
- **CL=F** (Crude Oil): Global demand, geopolitics
- **NG=F** (Natural Gas): Weather, storage, seasonality
- **RB=F** (RBOB Gasoline): Refining margins, driving season

**Correlations:**
- CL-NG: 0.4 (moderate)
- CL-RB: 0.9 (very high)
- NG-RB: 0.3 (low)

**Alpha strategy:**
- CL: OPEC, China demand, USD
- NG: Weather forecasts, storage reports (EIA)
- RB: Crack spreads (CL-RB)

### Currencies (2)
- **6E=F** (EUR/USD): Fed vs ECB policy
- **6J=F** (JPY/USD): Risk-on/risk-off, BOJ policy

**Correlations:**
- 6E-6J: 0.2 (low)

**Alpha strategy:**
- 6E: Rate differentials, ECB speeches
- 6J: VIX (risk-off → JPY strength)

### Indices (2)
- **ES=F** (S&P 500 E-mini): US equity exposure
- **NQ=F** (Nasdaq E-mini): Tech exposure

**Correlations:**
- ES-NQ: 0.95 (very high)

**Alpha strategy:**
- ES: Macro sentiment, earnings
- NQ: Tech momentum, FAANG

### Bonds (2)
- **ZN=F** (10-Year Treasury): Benchmark rate
- **ZB=F** (30-Year Treasury): Long-duration

**Correlations:**
- ZN-ZB: 0.85 (high)

**Alpha strategy:**
- ZN: Fed policy, inflation
- ZB: Long-term growth expectations

---

## Cross-Asset Features

**Correlation features:**
- Rolling 20-day correlation (all pairs)
- Correlation regime (high >0.7, low <0.3)
- Correlation breakdowns (alerts)

**Spread features:**
- GC-SI spread (gold-silver ratio)
- CL-RB spread (crack spread)
- ZN-ZB spread (yield curve steepness)
- ES-NQ spread (tech vs broad market)

**Ratio features:**
- GC/SI, CL/NG, ES/NQ
- Deviation from historical mean
- Z-score

**Risk-on/risk-off:**
- VIX (if available)
- 6J strength (risk-off proxy)
- ES vs ZN (equities vs bonds)

**Sector rotation:**
- Metals momentum vs Energy momentum
- Bonds vs Equities (flight to safety)

---

## Multi-Asset Portfolio Optimization

**Objective:**
```
max: μ^T w - λ w^T Σ w
s.t: sum(w) = 1
     |w_i| ≤ 0.15 (12 assets → 15% max per asset)
     sum(w[metals]) ≤ 0.40
     sum(w[energy]) ≤ 0.40
     sum(w[currencies]) ≤ 0.20
     sum(w[indices]) ≤ 0.30
     sum(w[bonds]) ≤ 0.30
```

**Covariance estimation:**
- 250-day rolling window
- Shrinkage (Ledoit-Wolf)
- Regime-conditional (separate Σ per regime)

**Risk budgeting:**
- Allocate 50% risk to alphas
- Allocate 30% risk to diversification
- Allocate 20% risk to hedges (bonds, JPY)

**Rebalancing:**
- Daily check
- Rebalance if any weight drifts >3% from target
- Transaction cost model: 2 bps fixed + 0.5 bps impact

---

## Asset-Specific Alpha Models

**Strategy:**
1. Train separate models per asset (12 models)
2. Use asset-specific features + cross-asset features
3. Tune hyperparameters per asset
4. Ensemble per asset (linear + tree + neural)

**Features per asset:**
- 400 asset-specific (from Phase 6 pipeline)
- 100 cross-asset (correlations, spreads, ratios)
- 500 total per asset

**Model selection:**
- Metals: Tree models (XGBoost) — trend-following
- Energy: Neural nets (LSTM) — volatility clustering
- Currencies: Linear (Ridge) — mean-reverting
- Indices: Ensemble (all) — broad market
- Bonds: Linear (Ridge) — rate-driven

**Expected performance:**
| Asset Class | Sharpe (Target) | IC (Target) |
|---|---|---|
| Metals | 0.8 | 0.08 |
| Energy | 1.0 | 0.10 |
| Currencies | 0.6 | 0.05 |
| Indices | 1.2 | 0.12 |
| Bonds | 0.7 | 0.06 |
| **Portfolio** | **1.5** | **N/A** |

---

## Data Pipeline Scaling

**Challenges:**
- 12 assets × 1440 bars/day = 17,280 bars/day
- 12 assets × 500 features = 6000 features/bar
- Total: ~100M feature values/day

**Solutions:**
1. Parallel ingestion (12 workers, 1 per asset)
2. Feature caching (avoid recomputation)
3. Incremental updates (only new bars)
4. DuckDB partitioning (1 table per asset)

**Storage:**
- DuckDB: ~500MB/day (compressed)
- RAGD: +200 chunks/day (intelligence reports)
- Vault: +50 notes/day (cross-asset observations)

**Performance target:**
- Ingest all 12 assets: <5 minutes
- Feature generation: <10 minutes
- Total pipeline: <15 minutes

---

## Key Decisions

- 12 assets (balance coverage vs complexity)
- Asset-specific models (not one universal model)
- Sector concentration limits (avoid overexposure)
- Cross-asset correlation monitoring (catch regime shifts)
- Unified risk management (portfolio-level VaR)

---

## Risks and Mitigations

1. **Data pipeline overload** (Medium risk)
   - Risk: 12 assets × 500 features = slow
   - Mitigation: Parallel processing, caching

2. **Model overfitting per asset** (Medium risk)
   - Risk: 12 models × hyperparameter tuning = data snooping
   - Mitigation: Hold-out test set, walk-forward validation

3. **Correlation breakdown** (High risk)
   - Risk: Crisis → all correlations → 1 (no diversification)
   - Mitigation: Stress tests, tail-risk hedging (bonds, JPY)

4. **Operational complexity** (Medium risk)
   - Risk: 12 data feeds, 12 models, 12 monitors
   - Mitigation: Unified dashboard, health checks, automation

5. **Liquidity risk** (Low risk)
   - Risk: Some assets illiquid (NG, HG)
   - Mitigation: ADV limits, position size caps

---

## Metrics (Target)

| Metric | Target |
|---|---|
| Assets live | 12 |
| Features | 6000/bar |
| Portfolio Sharpe | >1.5 |
| Max drawdown | <12% (better via diversification) |
| Cross-asset VaR accuracy | >95% days |
| Pipeline latency | <15 min |
| Uptime (all assets) | >99% |

---

## Expected Challenges

**Data synchronization:**
- 12 assets update at different times
- Solution: Brownian bridge interpolation (from Phase 2)

**Feature correlation:**
- Cross-asset features correlated (GC-SI, CL-RB)
- Solution: Correlation clustering, PCA

**Model tuning:**
- 12 models × hyperparameter search = expensive
- Solution: Bayesian optimization, transfer learning

**Portfolio rebalancing:**
- Transaction costs add up with 12 assets
- Solution: Higher rebalance threshold (>3% drift)

---

## Research Questions

1. Do cross-asset features improve single-asset alphas?
2. Which assets benefit most from cross-asset information?
3. Optimal portfolio: equal-weight vs risk-parity vs mean-variance?
4. Does sector rotation add alpha?
5. Spread trading (GC-SI, CL-RB) viable?

---

## Lessons from Prior Work

**From Phase 7 (Paper Trading):**
- Real-time monitoring critical
- Latency matters (<1s signal generation)
- Operational procedures necessary

**From Phase 8 (Risk Management):**
- VaR accuracy depends on correlation estimates
- Stress testing catches tail risks
- Circuit breakers prevent catastrophic loss

**Apply here:**
- Cross-asset correlation monitoring
- Portfolio-level VaR (not just per-asset)
- Unified risk dashboard

---

## Next Phase

→ [[PHASE_10]] — Production Hardening (Planned)
