---
doc_type: vision
system: Dominion
ragd_priority: 4
audience:
  - owner
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - future
  - vision
  - roadmap
---

# Future Vision (Post-Production)

**Purpose:** Long-term vision for Dominion beyond Phase 10 (production launch).

**Horizon:** 2028-2030 (2-3 years post-launch).

**Status:** Aspirational. Subject to market validation + resource availability.

---

## Vision Statement

**Mission:** Build institutional-grade quantitative research platform for solo/small-team researchers.

**Goal:** Transform Dominion from single-asset futures trader → multi-strategy research platform.

**Success Metrics (2030):**
- 100+ assets (futures, equities, FX, crypto)
- 10+ strategy families (alpha, market-making, statistical arb)
- Sharpe >2.0 (portfolio-level)
- 99.9% uptime
- $10M+ AUM capacity

---

## Phase 11: Multi-Strategy Framework (Q2-Q3 2028)

### Goals
1. Support multiple strategy types (beyond directional alpha)
2. Strategy isolation (separate P&L, risk)
3. Capital allocation across strategies
4. Unified execution layer

### Deliverables

**Strategy Types:**
- Directional alpha (current, Phase 6-8)
- Statistical arbitrage (pairs trading, mean-reversion)
- Market making (liquidity provision)
- Volatility trading (options straddles)
- Carry strategies (futures roll yield)

**Architecture:**
```
Strategy Manager
├─ Alpha Strategy 1 (GC=F directional)
├─ Alpha Strategy 2 (ES=F directional)
├─ Stat Arb Strategy (GC-SI spread)
├─ Market Making Strategy (ES=F)
└─ Vol Strategy (SPX options)
     │
     └─ Unified Execution Layer
          ├─ Order Router
          ├─ Risk Manager
          └─ Position Aggregator
```

**Capital Allocation:**
- Risk budgeting (allocate risk, not capital)
- Kelly optimal allocation (per strategy Sharpe + correlation)
- Dynamic rebalancing (shift capital to top performers)

**Expected Sharpe:** 1.5 (current) → 2.0 (diversification across strategies)

---

## Phase 12: Asset Class Expansion (Q4 2028 - Q2 2029)

### Goals
1. Expand from 12 futures → 100+ assets
2. Add equities, FX, crypto
3. Multi-asset portfolio optimization
4. Cross-asset strategies

### Asset Universe (100+ Target)

**Futures (30):**
- Metals: GC, SI, HG, PL, PA (5)
- Energy: CL, NG, RB, HO, BZ (5)
- Currencies: 6E, 6J, 6B, 6C, 6A, 6N (6)
- Indices: ES, NQ, YM, RTY, VIX (5)
- Bonds: ZN, ZB, ZF, ZT, UB (5)
- Ags: ZC, ZS, ZW, ZL, LE (4)

**Equities (50):**
- S&P 500 top 50 (liquid, high vol)
- Sectors: Tech, Finance, Healthcare, Energy
- Market cap: >$10B

**FX (10):**
- Majors: EUR/USD, GBP/USD, USD/JPY, USD/CHF
- Crosses: EUR/GBP, EUR/JPY, GBP/JPY
- Emerging: USD/MXN, USD/BRL, USD/ZAR

**Crypto (10):**
- BTC, ETH (large cap)
- SOL, ADA, AVAX (mid cap)
- Perpetual futures (funding rate arb)

**Challenges:**
- Data pipeline scaling (100× current)
- Execution venues (CME, NYSE, Binance, etc.)
- Regulatory (equities = pattern day trader rules)

---

## Phase 13: Machine Learning Research (Q3-Q4 2029)

### Goals
1. Deep learning models (LSTM, Transformer)
2. Reinforcement learning (optimal execution)
3. AutoML (hyperparameter search)
4. Model interpretability (SHAP, LIME)

### Deep Learning

**Architectures:**
- LSTM: Time-series forecasting (60-min forward returns)
- Transformer: Attention mechanism (cross-asset dependencies)
- CNN: Image-based features (candlestick patterns)

**Target Sharpe:** 1.8-2.2 (vs 1.5 tree models)

**Requirements:**
- GPU cluster (8× V100 or A100)
- Cloud compute ($5K/month AWS)
- Large dataset (3+ years × 100 assets)

### Reinforcement Learning

**Use Case:** Optimal execution (minimize slippage).

**Environment:**
- State: LOB snapshot, inventory, time remaining
- Action: Order size + timing
- Reward: -slippage (minimize)

**Algorithm:** PPO (Proximal Policy Optimization)

**Expected:** 20-30% slippage reduction vs Almgren-Chriss.

### AutoML

**Goal:** Automate hyperparameter search.

**Tools:**
- Optuna (Bayesian optimization)
- Ray Tune (distributed tuning)

**Benefit:** Save 50% tuning time (2 weeks → 1 week per model).

---

## Phase 14: Alternative Data Integration (2030+)

### Goals
1. Incorporate non-traditional data sources
2. Sentiment, satellite, web scraping
3. Proprietary edge

### Data Sources

**Satellite Imagery ($10K+/month):**
- Oil storage levels (predict EIA inventory)
- Cargo ship tracking (commodity flows)
- Agricultural yield estimation (crop futures)

**Sentiment Data ($5K/month):**
- News sentiment (Bloomberg, Reuters)
- Social media (Twitter, Reddit via aggregators)
- Analyst reports (earnings sentiment)

**Web Scraping:**
- Retail inventory (e-commerce sites)
- Job postings (economic activity proxy)
- Search trends (Google Trends)

**Alternative Exchanges:**
- Prediction markets (Polymarket, Kalshi)
- Crypto funding rates (Binance, Deribit)

**Challenge:** Signal-to-noise ratio low. Requires large capital for exclusive data.

---

## Infrastructure Evolution

### Current (Phase 10)
- Local deployment (single machine)
- HA: Active-passive failover
- 12 assets, 1 strategy
- 99.9% uptime target

### Future (Phase 14)
- Cloud deployment (AWS/GCP multi-region)
- HA: Active-active (load balanced)
- 100+ assets, 10+ strategies
- 99.99% uptime target (52 min downtime/year)

### Scaling Metrics

| Metric | Phase 10 (2028) | Phase 14 (2030) | Scale Factor |
|---|---|---|---|
| Assets | 12 | 100+ | 8× |
| Strategies | 1 | 10+ | 10× |
| Features/bar | 6,000 | 50,000+ | 8× |
| Data throughput | 17K bars/day | 150K bars/day | 9× |
| Compute | 1 server | 10+ servers | 10× |
| Cost | $500/month | $10K/month | 20× |

---

## Regulatory & Compliance

### Current (Phase 10)
- Solo trader (no registration)
- Personal capital only
- Read-only architecture (safety)

### Future (Phase 14)
- Potential: RIA registration (if managing external capital)
- Compliance: SEC Form ADV, CFTC registration
- Audit trail: All trades logged (immutable)
- Reporting: Quarterly performance reports

**Thresholds (SEC):**
- <$25M AUM: Exempt from registration
- $25M-$100M: State registration
- >$100M: SEC registration

**Decision:** Stay <$25M AUM (avoid regulatory burden) unless scaling justifies cost.

---

## Team Scaling

### Current (Phase 5-10)
- Solo researcher/developer
- Part-time (20-30 hours/week)

### Future (Phase 14)
**Potential team (if scaling):**
- Quant researcher (1-2 FTE)
- Infra engineer (1 FTE)
- Compliance officer (0.5 FTE, outsourced)

**Alternative:** Stay solo, outsource infra (AWS managed services).

---

## Business Model Evolution

### Current (Phase 10)
- Personal capital only
- No external investors
- Profit = personal returns

### Future Options

**Option 1: Personal Account (Status Quo)**
- Pros: No compliance, full control
- Cons: Capital-constrained (<$1M)

**Option 2: Friends & Family Fund**
- Raise $5-10M from accredited investors
- Pros: More capital, same strategy
- Cons: Regulatory (RIA), reporting burden

**Option 3: Prop Trading Firm Partnership**
- Trade firm capital (keep 20-30% profit)
- Pros: Large capital ($10M+), no compliance
- Cons: Profit split, firm oversight

**Option 4: Managed Account Platform**
- Trade via platform (Quantopian successor)
- Pros: No capital, no compliance
- Cons: Profit split (50%+), IP risk

**Likely Path:** Option 1 (personal) → Option 3 (prop firm) if performance justifies.

---

## Technology Roadmap

### Near-Term (2028)
- Multi-strategy framework
- 100-asset scaling
- Cloud migration (AWS)

### Mid-Term (2029)
- Deep learning (GPU cluster)
- RL-based execution
- AutoML pipeline

### Long-Term (2030+)
- Alternative data integration
- Proprietary data pipelines
- Real-time streaming architecture

---

## Success Scenarios

### Scenario 1: High Performance (Sharpe >2.0)
- Attract prop firm partnership ($10M+ capital)
- Scale to 100+ assets
- Hire 1-2 quant researchers
- Revenue: $2M+/year (20% of $10M at 100% returns)

### Scenario 2: Moderate Performance (Sharpe 1.5-2.0)
- Stay personal account ($1M capital)
- Selective asset expansion (30-50 assets)
- Part-time research
- Revenue: $150K-300K/year

### Scenario 3: Low Performance (Sharpe <1.5)
- Pivot to research tools (sell Dominion platform?)
- Open-source core components
- Consulting (quant strategy development)

---

## Risks & Mitigations

### Risk 1: Performance Decay
- **Risk:** Alpha decays as markets adapt
- **Likelihood:** High (inevitable)
- **Mitigation:** Continuous research (Phase 13), 10+ strategies (diversification)

### Risk 2: Scaling Complexity
- **Risk:** 100 assets = 10× operational burden
- **Likelihood:** Medium
- **Mitigation:** Automation (CI/CD, monitoring), outsource infra (AWS managed)

### Risk 3: Regulatory Change
- **Risk:** New rules prohibit retail algo trading
- **Likelihood:** Low
- **Mitigation:** Monitor SEC/CFTC, pivot to prop firm if needed

### Risk 4: Capital Constraints
- **Risk:** Can't scale beyond $1M personal capital
- **Likelihood:** Medium
- **Mitigation:** Prop firm partnership (Phase 14)

### Risk 5: Burnout (Solo Researcher)
- **Risk:** 100+ assets = unsustainable workload
- **Likelihood:** High
- **Mitigation:** Hire help or stay 12-30 assets (sustainable)

---

## Key Decisions (Future)

### 2028: Multi-Strategy vs Deep Single-Strategy
- **Trade-off:** 10 strategies (diversification) vs 1 strategy (focus)
- **Decision:** Start multi-strategy (Phase 11), measure Sharpe improvement
- **Threshold:** If Sharpe <1.8, revert to single-strategy

### 2029: Cloud vs Local
- **Trade-off:** AWS ($10K/month) vs local ($500/month)
- **Decision:** Migrate if >30 assets (local insufficient)
- **Threshold:** 30 assets = breaking point

### 2030: Solo vs Team
- **Trade-off:** Solo (full control) vs team (scale)
- **Decision:** Hire if revenue >$500K/year (justifies cost)
- **Threshold:** $500K revenue = 1 FTE affordable

---

## Moonshots (10% Probability)

**Moonshot 1: Sharpe >3.0**
- Achievable? Maybe (ensemble of 10+ uncorrelated strategies)
- Impact: Attract institutional capital ($50M+)

**Moonshot 2: Real-Time News Alpha**
- Achievable? Maybe (NLP on earnings calls, FOMC transcripts)
- Impact: Edge in event-driven trading

**Moonshot 3: Proprietary LOB Data**
- Achievable? Maybe (partnership with exchange for L3 data)
- Impact: Ultra-HF alpha (sub-second)

**Moonshot 4: Open-Source Dominion**
- Achievable? Yes (release as research platform)
- Impact: Community contributions, consulting revenue

---

## Related Documentation

- [[SCALING_STRATEGY]] — Technical scaling plan
- [[TECH_DEBT_MAP]] — Known debt + remediation
- [[PHASE_10]] — Production readiness (baseline)
- [[PLANNED_FEATURES]] — Phase 6-10 roadmap

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Annually (or after major milestones)

**How to Use:** Aspirational guide, not rigid plan. Adapt based on performance + resources.
