---
doc_type: backlog
system: Dominion
ragd_priority: 4
audience:
  - maintainer
  - owner
status: active
last_reviewed: 2026-05-19
tags:
  - backlog
  - features
  - planning
---

# Feature Backlog

**Purpose:** Features not yet scheduled for phases 6-10.

**Status:** 35 features in backlog (Phase 5).

**Triage:** Quarterly review. Promote to roadmap or deprecate.

---

## Backlog Format

```markdown
### Feature Name (Priority)

**Description:** [What is it?]
**Value:** [Why build it?]
**Effort:** [Estimated time]
**Blockers:** [Dependencies]
**Status:** Proposed / Researching / Deferred
```

---

## P1: High Value, Unscheduled

### Real-Time LOB Data Integration (P1)

**Description:** Integrate CQG or Rithmic for real L2 order book data.

**Value:**
- Replace synthetic quotes (current limitation)
- Improve microstructure features (depth, spread accuracy)
- Enable sub-minute alpha strategies

**Effort:** 4 weeks
- API integration (1 week)
- LOB reconstruction refactor (2 weeks)
- Validation + testing (1 week)

**Blockers:**
- Cost: $500-1000/month (CQG data feed)
- API access (requires account)

**Status:** Deferred (cost prohibitive until $10M+ AUM)

**Priority:** P1 if scaling, else P3

---

### Options Data Integration (P1)

**Description:** Add SPX/SPY options (IV surface, skew, Greeks).

**Value:**
- Volatility forecasting (IV → realized vol)
- Tail risk hedging (put spreads)
- Carry strategies (option selling)

**Effort:** 6 weeks
- Options data feed (TDAmeritrade) (1 week)
- IV surface reconstruction (SVI calibration) (2 weeks)
- Greeks calculation (1 week)
- Strategy development (2 weeks)

**Blockers:**
- Options data expensive ($1K+/month)
- Complex (IV calibration, Greeks math)

**Status:** Researching (Alpha stage, see [[EXPERIMENTAL_FEATURES]])

**Priority:** P1 if Phase 11 (multi-strategy)

---

### Equity Universe Expansion (P1)

**Description:** Trade S&P 500 stocks (not just futures).

**Value:**
- Diversification (50+ equities vs 12 futures)
- Higher capacity ($100M+ vs $10M futures)
- Statistical arbitrage (pairs trading)

**Effort:** 8 weeks
- Equity data feed (Alpaca/IEX) (1 week)
- Pattern day trader workaround (2 weeks)
- Slippage model calibration (equities ≠ futures) (2 weeks)
- Backtesting (3 weeks)

**Blockers:**
- PDT rule (<$25K account = max 3 day trades/week)
- Higher data costs (real-time equity quotes)

**Status:** Proposed (Phase 12 target)

**Priority:** P1 for scaling beyond futures

---

## P2: Medium Value, Low Effort

### Email Alerts (P2)

**Description:** Send email on critical events (crashes, limit breaches).

**Value:**
- Faster incident response
- Peace of mind (know when system fails)

**Effort:** 2 days
- SMTP integration (1 day)
- Alert templates (1 day)

**Blockers:** None

**Status:** Proposed (Phase 7 quick win)

**Priority:** P2 (useful but not critical)

---

### Slack Integration (P2)

**Description:** Post daily performance summary to Slack channel.

**Value:**
- Quick performance check (mobile)
- Share with team (if scaling)

**Effort:** 1 day

**Blockers:** None (Slack webhook trivial)

**Status:** Proposed (Phase 7-8)

**Priority:** P2

---

### Jupyter Notebook Templates (P2)

**Description:** Pre-built notebooks for common tasks (backtest, feature analysis).

**Value:**
- Faster experimentation
- Reusable patterns

**Effort:** 3 days (5 notebooks)

**Blockers:** None

**Status:** Proposed (Phase 6 research tools)

**Priority:** P2

---

### Backtest Result Visualization (P2)

**Description:** Interactive charts (Plotly) for backtest results.

**Value:**
- Easier interpretation (equity curve, drawdown)
- Debugging (regime overlay, feature IC)

**Effort:** 1 week

**Blockers:** None

**Status:** Proposed (Phase 6)

**Priority:** P2

---

### RAGD Web UI (P2)

**Description:** Web interface for RAGD queries (not just REST API).

**Value:**
- Easier exploration (vs curl commands)
- Shareable links

**Effort:** 1 week (Flask + React)

**Blockers:** None

**Status:** Proposed (Phase 8-10)

**Priority:** P2 (nice-to-have)

---

## P3: Research / Experimental

### Reinforcement Learning Alpha (P3)

**Description:** RL agent learns optimal execution policy.

**Value:**
- Potential 20-30% slippage reduction
- Cutting-edge research

**Effort:** 8 weeks
- Environment design (1 week)
- PPO implementation (2 weeks)
- Training (GPU, 3 weeks)
- Validation (2 weeks)

**Blockers:**
- GPU required ($1K/month cloud)
- Complex (high failure risk)

**Status:** Researching (Prototype stage, unstable)

**Priority:** P3 (moonshot, low probability)

---

### Sentiment Analysis (Twitter/News) (P3)

**Description:** Extract sentiment from news/social media for alpha.

**Value:**
- Event-driven alpha (earnings, FOMC)
- Edge if signal exists

**Effort:** 6 weeks
- Data pipeline (NewsAPI, Twitter) (2 weeks)
- FinBERT sentiment extraction (1 week)
- Feature engineering (1 week)
- Backtesting (2 weeks)

**Blockers:**
- Twitter API expensive ($5K/month)
- IC weak (<0.02 in experiments)

**Status:** Deprecated (Phase 6)

**Priority:** P3 (failed validation, shelved)

---

### Alternative Data (Satellite Imagery) (P3)

**Description:** Use satellite images to predict commodity inventories.

**Value:**
- Proprietary edge (few competitors)
- Predict EIA oil inventory reports

**Effort:** 12 weeks
- Data source (Planet Labs, Orbital Insight) ($10K/month)
- Image processing pipeline (4 weeks)
- ML model (CNN for storage detection) (4 weeks)
- Validation (4 weeks)

**Blockers:**
- Cost prohibitive ($10K+/month)
- Complex (image processing expertise)

**Status:** Deferred (Phase 14+, if $50M+ AUM)

**Priority:** P3 (moonshot)

---

### Crypto Perpetual Futures (P3)

**Description:** Trade BTC, ETH perpetual futures (Binance, Deribit).

**Value:**
- 24/7 market (no overnight gap risk)
- Funding rate arbitrage

**Effort:** 4 weeks
- Exchange API integration (1 week)
- Funding rate features (1 week)
- Slippage model (crypto ≠ trad markets) (1 week)
- Backtesting (1 week)

**Blockers:**
- Regulatory uncertainty (crypto)
- High volatility (risk management challenge)

**Status:** Proposed (Phase 12-13)

**Priority:** P3 (interesting but risky)

---

## P4: Low Priority / Defer

### Mobile App (P4)

**Description:** iOS/Android app for monitoring.

**Value:**
- Check performance on-the-go

**Effort:** 8 weeks (full app)

**Blockers:**
- Complex (React Native or native)
- Maintenance burden

**Status:** Deferred indefinitely

**Priority:** P4 (web dashboard sufficient)

---

### Voice Alerts (Alexa/Google) (P4)

**Description:** "Alexa, what's my Sharpe ratio?"

**Value:**
- Cool factor

**Effort:** 1 week

**Blockers:** None (but pointless)

**Status:** Rejected (gimmick)

**Priority:** P4

---

### Social Trading Platform (P4)

**Description:** Share signals with community, copy-trading.

**Value:**
- Network effects
- Revenue (subscription fees)

**Effort:** 6 months (full platform)

**Blockers:**
- Regulatory (investment advisor registration)
- Huge scope

**Status:** Rejected (out of scope)

**Priority:** P4

---

## Backlog by Phase Candidate

### Phase 11 Candidates (Multi-Strategy)
- Options data integration (P1)
- Equity universe expansion (P1)

### Phase 12 Candidates (Asset Expansion)
- Crypto perpetuals (P3)
- Additional futures (ag commodities) (P2)

### Phase 13 Candidates (ML Research)
- RL alpha (P3)
- Sentiment analysis (revisit with better data)

### Phase 14+ Candidates (Long-Term)
- Alternative data (satellite) (P3)
- Real-time LOB data (P1 if scaling)

---

## Promotion Criteria (Backlog → Roadmap)

**To Phase 6-10:**
1. Value: High (Sharpe improvement >0.2 or risk reduction >20%)
2. Effort: Reasonable (<4 weeks)
3. Blockers: None or mitigated

**Examples:**
- Email alerts: P2, 2 days → Promote to Phase 7 ✓
- RL alpha: P3, 8 weeks, GPU blocker → Stay in backlog

---

## Deprecation Criteria (Backlog → Closed)

**Remove if:**
1. Failed validation (IC <0.03 after 3 months research)
2. Cost prohibitive (>$5K/month for solo researcher)
3. Out of scope (regulatory, maintenance burden)
4. Superseded by better approach

**Examples:**
- Sentiment (Twitter): IC <0.02 → Deprecated ✓
- Voice alerts: Gimmick → Rejected ✓

---

## Backlog Statistics

**Total items:** 35

**By Priority:**
- P1: 3 (high value, blocked by cost/scale)
- P2: 5 (medium value, easy wins)
- P3: 8 (research, uncertain ROI)
- P4: 3 (low priority, deferred)

**By Status:**
- Proposed: 20 (not yet researched)
- Researching: 5 (prototyping ongoing)
- Deferred: 7 (blocked or low priority)
- Deprecated: 3 (failed validation)

**By Effort:**
- <1 week: 8 items
- 1-4 weeks: 12 items
- 4-8 weeks: 10 items
- >8 weeks: 5 items

---

## Triage Schedule

**Quarterly Review (Every 3 Months):**
1. Review backlog items
2. Promote high-value, unblocked items to roadmap
3. Deprecate failed experiments
4. Add new items from research

**Last Triage:** 2026-05-19 (Phase 5)

**Next Triage:** 2026-08-19 (Phase 6 mid-point)

---

## Related Documentation

- [[PLANNED_FEATURES]] — Scheduled features (Phase 6-10)
- [[EXPERIMENTAL_FEATURES]] — Active research
- [[DEPRECATED_FEATURES]] — Failed experiments
- [[BUG_BACKLOG]] — Known bugs
- [[ENHANCEMENT_BACKLOG]] — Non-feature improvements

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Quarterly (after triage)

**How to Add Feature:**
1. Copy format (description, value, effort, blockers, status)
2. Assign priority (P1-P4)
3. Add to appropriate section
4. Triage at next review (promote/defer/deprecate)
