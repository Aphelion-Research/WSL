---
doc_type: catalog
system: Dominion
ragd_priority: 6
audience:
  - researcher
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - features
  - experimental
  - research
---

# Experimental Features

**Purpose:** Catalog of experimental/research features not yet production-ready.

**Status:** 12 experimental features in various stages of research/validation.

**Maturity Levels:**
- **Prototype:** Proof-of-concept code, not integrated
- **Alpha:** Integrated but unstable, limited testing
- **Beta:** Stable but needs more validation before production

---

## 1. Reinforcement Learning Alpha (Prototype)

**Status:** Prototype (Phase 6 research)

**Purpose:**
RL agent learns optimal execution policy via environment interaction.

**Approach:**
- PPO (Proximal Policy Optimization)
- State: 50 features (prices, vol, OFI, regime)
- Action: Position size (-1 to +1)
- Reward: Sharpe ratio (risk-adjusted returns)

**Progress:**
- Simulator built (OpenAI Gym environment)
- PPO agent trains but unstable
- Reward function needs tuning

**Challenges:**
- Sparse rewards (only after trades close)
- Sample efficiency low (needs 100K+ episodes)
- Doesn't outperform tree models yet

**Next Steps:**
- Shaped rewards (intermediate signals)
- Imitation learning (bootstrap from supervised)
- More compute (GPU cluster)

**Docs:** None (research notes only)

---

## 2. Sentiment Analysis (Prototype)

**Status:** Prototype (Phase 6 research)

**Purpose:**
Extract sentiment from news, Twitter, Reddit for alpha generation.

**Approach:**
- Data: NewsAPI, Twitter API (via snscrape)
- Model: FinBERT (financial sentiment BERT)
- Output: Sentiment score (-1 to +1) per article/tweet
- Feature: Aggregate sentiment (1h, 4h, daily)

**Progress:**
- NewsAPI integration works
- FinBERT sentiment extraction functional
- IC correlation weak (0.02-0.03)

**Challenges:**
- News delay (minutes after event)
- Noise (sentiment ≠ price moves)
- Rate limits (Twitter API expensive)

**Next Steps:**
- Filter by source reliability
- Event-driven (only FOMC, NFP)
- Combine with price action

**Docs:** None (research notes only)

---

## 3. Options Data Integration (Alpha)

**Status:** Alpha (Phase 9 research)

**Purpose:**
Use options implied volatility, skew, open interest for alpha.

**Approach:**
- Data: CBOE (VIX, SKEW), TDAmeritrade options chain
- Features: IV surface, put/call ratio, skew, term structure
- Use Case: Volatility forecasting, tail risk hedging

**Progress:**
- CBOE VIX ingestion works
- IV surface reconstruction prototype
- Not yet integrated into pipeline

**Challenges:**
- Options data expensive (TDA requires account)
- IV surface fitting complex (SVI calibration)
- Limited historical data

**Next Steps:**
- Use free CBOE indices (VIX, SKEW)
- Add put/call ratio feature
- Backtest vol forecasting

**Docs:** `research/options_integration.md` (draft)

---

## 4. High-Frequency Tick Prediction (Alpha)

**Status:** Alpha (Phase 6 research)

**Purpose:**
Predict next tick direction (up/down/flat) for ultra-short-term alpha.

**Approach:**
- Features: L2 LOB (10 levels), recent ticks (100), OFI (1s)
- Model: LSTM (sequence model)
- Horizon: Next tick (1-5 seconds)

**Progress:**
- LSTM trained (accuracy ~52%)
- Barely beats random (50%)
- High transaction costs kill alpha

**Challenges:**
- Signal-to-noise ratio low at tick level
- Slippage dominates (2 bps spread)
- Requires real LOB data (not synthetic)

**Next Steps:**
- Abandon unless real LOB data available
- Alternative: Focus on 1-min+ horizons

**Docs:** `research/tick_prediction.md` (draft)

---

## 5. Portfolio Rebalancing Optimization (Beta)

**Status:** Beta (Phase 8 research)

**Purpose:**
Optimize rebalancing schedule to minimize transaction costs.

**Approach:**
- Model: Trade-off between drift (risk) and transaction costs
- Algorithm: Dynamic programming (optimal rebalancing times)
- Inputs: Current weights, target weights, transaction costs, covariance

**Progress:**
- DP algorithm implemented
- Simulation shows 20% cost reduction vs fixed schedule
- Needs real-world validation (paper trading)

**Challenges:**
- Assumes transaction costs known (estimates may be wrong)
- Optimization slow (scales poorly with assets)

**Next Steps:**
- Validate in Phase 7 paper trading
- Simplify algorithm (greedy heuristic)

**Docs:** `research/rebalancing_optimization.md` (draft)

---

## 6. Regime-Switching Kalman Filter (Prototype)

**Status:** Prototype (Phase 4 research)

**Purpose:**
Use HMM regime to switch between multiple Kalman filters (regime-conditional fusion).

**Approach:**
- 3 Kalman filters (one per regime: Bull/Neutral/Bear)
- Weight filter outputs by regime probability
- Hypothesis: Better fusion during regime transitions

**Progress:**
- Prototype code written
- Marginal improvement over single Kalman (~5% error reduction)
- Added complexity not worth it

**Challenges:**
- Regime detection lag (transitions detected late)
- 3× computational cost
- Minimal performance gain

**Next Steps:**
- Shelve unless regime detection improves

**Docs:** None (research notes only)

---

## 7. Explainable AI (SHAP Values) (Beta)

**Status:** Beta (Phase 6 research)

**Purpose:**
Explain alpha model predictions via SHAP (SHapley Additive exPlanations).

**Approach:**
- Compute SHAP values for each feature per prediction
- Visualize feature importance (waterfall plots)
- Use Case: Debug model, validate features, regulatory transparency

**Progress:**
- SHAP integration works (TreeSHAP for XGBoost)
- Waterfall plots generated
- Slow (30s per prediction)

**Challenges:**
- Computational cost (SHAP expensive for ensembles)
- SHAP values approximate (not exact)

**Next Steps:**
- Cache SHAP values (recompute daily, not per prediction)
- Add to Phase 7 dashboard (explainability tab)

**Docs:** `research/explainability.md` (draft)

---

## 8. Multi-Timeframe Ensemble (Prototype)

**Status:** Prototype (Phase 6 research)

**Purpose:**
Train separate models per timescale (1m, 5m, 1h, daily) and ensemble.

**Approach:**
- 4 models (one per timescale)
- Features: Same 50 features, different timescales
- Ensemble: IC-weighted average

**Progress:**
- 4 models trained
- Ensemble Sharpe: 1.3 (vs 1.2 single best model)
- Marginal improvement (~10%)

**Challenges:**
- 4× training cost
- Models correlated (limited diversification)

**Next Steps:**
- Test in Phase 7 paper trading
- If gain <20%, not worth complexity

**Docs:** None (research notes only)

---

## 9. Spread Trading Strategies (Alpha)

**Status:** Alpha (Phase 9 research)

**Purpose:**
Trade spreads (GC-SI, CL-RB) for mean-reversion alpha.

**Approach:**
- Compute z-score of spread (deviation from historical mean)
- Enter: z-score >2 or <-2
- Exit: z-score crosses 0
- Hedge: Long one leg, short the other

**Progress:**
- Backtest shows Sharpe ~0.6 (modest)
- Transaction costs eat profits (two legs)

**Challenges:**
- Correlation breakdown (spreads widen in crisis)
- Execution timing tricky (leg risk)

**Next Steps:**
- Test in Phase 9 (multi-asset)
- Focus on high-correlation pairs (GC-SI, CL-RB)

**Docs:** `research/spread_trading.md` (draft)

---

## 10. Volatility Forecasting (GARCH) (Beta)

**Status:** Beta (Phase 6 research)

**Purpose:**
Forecast volatility using GARCH (Generalized Autoregressive Conditional Heteroskedasticity).

**Approach:**
- Model: GARCH(1,1)
- Input: Daily returns
- Output: Forecasted volatility (1-day, 7-day)
- Use Case: Position sizing, VaR estimation

**Progress:**
- GARCH(1,1) implemented (arch library)
- Forecast accuracy ~70% (directional)
- Better than rolling std (~60%)

**Challenges:**
- GARCH assumes returns normal (not true)
- Underestimates tail risk (fat tails)

**Next Steps:**
- Use in Phase 8 dynamic position sizing
- Consider EGARCH (asymmetric vol)

**Docs:** `research/garch_volatility.md` (draft)

---

## 11. Economic Indicator Features (Alpha)

**Status:** Alpha (Phase 4 research)

**Purpose:**
Use macro indicators (GDP, CPI, unemployment) as features.

**Approach:**
- Data: FRED API (10 macro series)
- Features: GDP growth, CPI YoY, unemployment rate, etc.
- Frequency: Monthly (low frequency)

**Progress:**
- FRED integration works (Phase 2)
- Features computed but IC weak (<0.02)
- Macro data lags (released weeks after period)

**Challenges:**
- Low frequency (monthly) vs daily trading
- Lagged data (less predictive)

**Next Steps:**
- Focus on high-frequency indicators (jobless claims, PMI)
- Regime-conditional (macro matters more in Bear regime)

**Docs:** [[PHASE_2]]

---

## 12. Alternative Data (Satellite Imagery) (Prototype)

**Status:** Prototype (Phase 9 research)

**Purpose:**
Use satellite imagery (oil storage, cargo ships) for commodities alpha.

**Approach:**
- Data: Planet Labs, Orbital Insight
- Target: Oil storage levels (predict inventory reports)
- Model: CNN on satellite images → storage estimate

**Progress:**
- Researched providers (expensive: $5K+/month)
- No implementation yet

**Challenges:**
- Cost prohibitive for solo researcher
- Data access restrictions
- Complex (image processing pipeline)

**Next Steps:**
- Shelve until Phase 9+ (multi-asset expansion)
- Consider cheaper proxy (cargo ship tracking via AIS)

**Docs:** None (research notes only)

---

## Feature Maturity Pipeline

**Research → Prototype → Alpha → Beta → Production**

```
Prototype (5)        Alpha (4)             Beta (3)              Production (0)
──────────────      ──────────────        ──────────────        ──────────────
RL Alpha            Options Data          Portfolio Rebal        [None yet]
Sentiment           HF Tick Predict       Explainable AI
Regime Kalman       Spread Trading        Vol Forecast (GARCH)
Multi-Timeframe     Econ Indicators
Alt Data (Sat)
```

---

## Promotion Criteria

**Prototype → Alpha:**
- Code integrated into repo
- Preliminary results (IC, Sharpe)
- At least 1 backtest

**Alpha → Beta:**
- Stable implementation
- Multiple backtests (walk-forward)
- Tests passing (>80% coverage)
- Documentation draft

**Beta → Production:**
- Paper trading validation (30+ days)
- Sharpe >0.8 or clear value-add
- Full test coverage (>90%)
- Production docs complete
- Code review + approval

---

## Retirement Criteria

Experimental feature should be deprecated if:
- IC consistently <0.03 after 3+ months research
- Sharpe <0.5 after walk-forward validation
- Complexity > benefit (maintenance burden)
- External dependency too expensive
- Blocked by data availability

**Recent Deprecations:**
- Twitter sentiment (API too expensive, IC <0.02)
- Tick prediction (signal-to-noise too low)

---

## Resource Allocation

**Recommended effort split:**
- 70% production features (Phase 6-10)
- 20% experimental research
- 10% maintenance/infrastructure

**Current focus (Phase 5-6):**
- Priority: Alpha models (tree, neural, ensemble)
- Secondary: Portfolio rebalancing, GARCH vol forecasting
- Low priority: RL, sentiment, alternative data

---

## Related Documentation

- [[CURRENT_FEATURES]] — Operational features
- [[PLANNED_FEATURES]] — Production roadmap (Phase 6-10)
- [[DEPRECATED_FEATURES]] — Retired features
- [[RESEARCH_INDEX]] — Research notes (to be created)
- [[ALPHA_RESEARCH_LOG]] — Research journal (to be created)

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Monthly (after research sprints)

**How to Add:**
1. Create research note in `research/`
2. Add entry here (under appropriate maturity level)
3. Link to research note
4. Update quarterly (promote/deprecate/retire)
