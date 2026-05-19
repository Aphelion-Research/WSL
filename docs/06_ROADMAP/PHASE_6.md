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
  - phase-6
  - alpha-research
  - ml
---

# Phase 6: Advanced Alpha Research (Planned)

**Timeline:** Q2 2026 - Q3 2026 (3 months)  
**Status:** 📋 Planned

---

## Goals

1. ML feature selection (400+ → top 50)
2. Alpha combination strategies
3. Backtesting framework
4. Portfolio construction rules
5. Walk-forward validation

---

## Deliverables

### Feature Selection
- [ ] Mutual information ranking
- [ ] LASSO/Ridge feature selection
- [ ] Random forest importance
- [ ] Recursive feature elimination
- [ ] Top 50 features identified

### Alpha Models
- [ ] Linear models (Ridge, LASSO, ElasticNet)
- [ ] Tree models (XGBoost, LightGBM, CatBoost)
- [ ] Neural networks (LSTM, Transformer)
- [ ] Ensemble methods (stacking, blending)
- [ ] 5-fold cross-validation

### Backtesting Framework
- [ ] Event-driven backtester
- [ ] Slippage + commission models
- [ ] Walk-forward validation
- [ ] Regime-conditional metrics
- [ ] Drawdown analysis

### Portfolio Construction
- [ ] Mean-variance optimization
- [ ] Risk parity
- [ ] Kelly criterion
- [ ] Position sizing rules
- [ ] Rebalancing logic

### Alpha Combination
- [ ] Equal-weight ensemble
- [ ] IC-weighted ensemble
- [ ] Meta-model stacking
- [ ] Dynamic weight adjustment
- [ ] Correlation analysis

---

## Timeline

| Milestone | Date | Status |
|---|---|---|
| Feature selection complete | 2026-07-01 | Pending |
| 3 alpha models trained | 2026-07-15 | Pending |
| Backtesting framework | 2026-08-01 | Pending |
| Walk-forward validation | 2026-08-15 | Pending |
| Portfolio construction | 2026-08-31 | Pending |
| Phase 6 complete | 2026-08-31 | Pending |

---

## Dependencies

**Requires Phase 5:**
- Documentation (for alpha strategy specs)
- RAGD (for research note retrieval)

**Requires Phase 4:**
- Regime detection (for regime-conditional alphas)
- Intelligence reports (for market context)

**Requires Phase 3:**
- 400+ features (baseline for selection)
- Execution features (for alpha signals)

**External:**
- scikit-learn, xgboost, lightgbm
- pytorch or tensorflow (for neural nets)
- cvxpy (for portfolio optimization)

---

## Success Criteria

- [ ] Top 50 features selected (IC >0.05)
- [ ] 5+ alpha models trained
- [ ] Sharpe ratio >1.0 (out-of-sample)
- [ ] Max drawdown <20%
- [ ] Walk-forward validation: 12 months
- [ ] Backtesting framework tested on 2+ years data

---

## Feature Selection Strategy

**Phase 1: Univariate screening**
- Compute IC for all 400+ features
- Retain features with |IC| >0.03
- Expected: ~150 features pass

**Phase 2: Correlation clustering**
- Group highly correlated features (ρ >0.7)
- Select highest IC from each cluster
- Expected: ~80 features

**Phase 3: ML-based selection**
- LASSO with cross-validation
- Random forest importance (top 50)
- Recursive elimination
- Expected: ~50 features

**Phase 4: Walk-forward validation**
- Retrain feature selection every 3 months
- Adapt to regime changes
- Monitor feature decay

---

## Alpha Models

### Linear Models
- Ridge regression (L2 regularization)
- LASSO (L1 regularization, sparse)
- ElasticNet (L1+L2 hybrid)
- Sharpe target: 0.8-1.2

### Tree Models
- XGBoost (gradient boosting)
- LightGBM (leaf-wise, fast)
- CatBoost (categorical features)
- Sharpe target: 1.0-1.5

### Neural Networks
- LSTM (time-series memory)
- Transformer (attention mechanism)
- Feedforward (baseline)
- Sharpe target: 1.2-1.8 (if tuned)

### Ensemble
- Stacking (meta-learner on predictions)
- Blending (weighted average)
- Dynamic weighting (IC-based)
- Sharpe target: 1.5-2.0

---

## Backtesting Framework

**Design:**
```python
class Backtester:
    - process_tick(timestamp, price, features)
    - generate_signal(alpha_model, features)
    - size_position(signal, volatility, capital)
    - execute_order(size, price, slippage_model)
    - track_pnl(fills, marks)
    - compute_metrics(trades, equity_curve)
```

**Event flow:**
1. Tick arrives → features computed
2. Alpha model generates signal (-1 to +1)
3. Position sizing (Kelly / fixed %)
4. Order execution (Almgren-Chriss slippage)
5. P&L marking (mark-to-market)
6. Metrics updated (Sharpe, drawdown, turnover)

**Validation:**
- In-sample: 2024-01-01 to 2025-06-30 (train)
- Out-of-sample: 2025-07-01 to 2026-06-30 (test)
- Walk-forward: Retrain every 3 months

---

## Portfolio Construction

**Mean-Variance Optimization:**
```
max: μ^T w - λ w^T Σ w
s.t: sum(w) = 1
     |w_i| ≤ 0.2 (position limits)
```

**Risk Parity:**
- Equal risk contribution per alpha
- Inverse volatility weighting
- Rebalance weekly

**Kelly Criterion:**
```
f* = (μ - r) / σ^2
```
- Half-Kelly for safety (f*/2)
- Floor at 0, ceiling at 20% per position

**Rebalancing:**
- Trigger: >5% drift from target weights
- Frequency: Daily check, weekly rebalance
- Cost model: 2 bps fixed + 0.5 bps market impact

---

## Key Decisions

- Top 50 features (balance signal vs noise)
- Walk-forward 3-month retraining (adapt to regimes)
- Ensemble of 5+ models (diversification)
- Half-Kelly position sizing (conservative)
- Weekly rebalancing (balance turnover vs drift)

---

## Risks and Mitigations

1. **Overfitting** (High risk)
   - Mitigation: 5-fold CV, walk-forward validation
   - Early stopping, regularization

2. **Feature decay** (Medium risk)
   - Mitigation: IC monitoring, quarterly retraining
   - Feature staleness alerts

3. **Regime shifts** (Medium risk)
   - Mitigation: Regime-conditional models
   - Drawdown-based de-risking

4. **Execution slippage** (Low risk)
   - Mitigation: Almgren-Chriss model calibrated
   - Real-time toxicity monitoring

5. **Data snooping** (Medium risk)
   - Mitigation: Hold-out test set never touched during dev
   - Blind validation at end

---

## Metrics (Projected)

| Metric | Target |
|---|---|
| Sharpe ratio (OOS) | >1.0 |
| Max drawdown | <20% |
| Win rate | >50% |
| Turnover | <100%/day |
| IC (top alpha) | >0.10 |
| Features selected | 50 |
| Models trained | 5+ |
| Backtest duration | 2+ years |

---

## Expected Challenges

**Feature selection:**
- 400+ features → multicollinearity risk
- IC instability across regimes
- Solution: Regime-conditional selection

**Model training:**
- Neural nets require GPU (may need cloud)
- Hyperparameter search expensive
- Solution: Bayesian optimization, early stopping

**Backtesting:**
- Event-driven backtester complex
- Slippage model calibration tricky
- Solution: Start simple, iterate

**Portfolio construction:**
- Covariance matrix estimation noisy
- Optimization may be unstable
- Solution: Shrinkage estimators, regularization

---

## Research Questions

1. Do microstructure features add alpha beyond price/volume?
2. Which timescale (1m, 5m, 1h) has best IC?
3. Is regime-conditional training worth the complexity?
4. Linear vs tree vs neural: which dominates?
5. Is ensemble better than single best model?

---

## Lessons from Prior Work

**From Phase 3 (Microstructure):**
- Exec features IC up to 0.15 (ofi_1m)
- 60min horizon best (signal vs noise)
- 1000+ samples needed before trusting IC

**From Phase 4 (Regime Detection):**
- HMM regimes stable (5-day avg duration)
- Regime-conditional features show promise
- Calendar features useful for event-driven moves

**Apply here:**
- Focus on top 10 exec features first
- Regime-conditional models likely to outperform
- Walk-forward validation critical

---

## Next Phase

→ [[PHASE_7]] — Live Paper Trading (Planned)
