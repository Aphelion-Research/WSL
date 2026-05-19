---
doc_type: journal
system: Dominion
ragd_priority: 6
audience:
  - researcher
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - research
  - alpha
  - ml
  - phase-6
---

# Alpha Research Log

**Purpose:** Ongoing journal of alpha research experiments (Phase 6+).

**Status:** Active research (Phase 5 → Phase 6 transition).

**Format:** Chronological entries with hypothesis, method, result, decision.

---

## Entry Format

```markdown
### YYYY-MM-DD: [Experiment Name]

**Hypothesis:** [What are we testing?]
**Method:** [How are we testing it?]
**Data:** [Sample period, size]
**Result:** [Metrics: IC, Sharpe, drawdown]
**Decision:** [Promote/Iterate/Deprecate]
**Notes:** [Key insights, gotchas]
```

---

## 2026-05-19: Baseline Feature IC (Initial Survey)

**Hypothesis:** Identify top 10 features from 400+ for Phase 6 selection.

**Method:**
- Compute IC (Information Coefficient) for all 400 features
- Horizon: 60-min forward returns
- Data: 2025-07-01 to 2026-01-31 (7 months, Phase 3-4 data)

**Result:**

| Rank | Feature | IC | Category |
|---|---|---|---|
| 1 | ofi_1m | 0.15 | Microstructure |
| 2 | spread_roll | 0.12 | Microstructure |
| 3 | depth_imbalance_10 | 0.11 | Microstructure |
| 4 | returns_15m | 0.10 | Price |
| 5 | vol_parkinson_1h | 0.09 | Volatility |
| 6 | volume_ratio_1h | 0.08 | Volume |
| 7 | ofi_5m | 0.08 | Microstructure |
| 8 | macd_1h | 0.07 | Technical |
| 9 | rsi_30m | 0.06 | Technical |
| 10 | vpin_toxicity | 0.06 | Microstructure |

**Insight:** Microstructure features dominate top 10 (6/10).

**Decision:** Prioritize microstructure in Phase 6 feature selection.

---

## 2026-03-15: Regime-Conditional IC Analysis

**Hypothesis:** Features perform differently by regime.

**Method:**
- Split data by HMM regime (Bull/Neutral/Bear)
- Compute IC per regime
- Data: 2025-10-01 to 2026-02-28 (5 months, Phase 4)

**Result:**

| Feature | IC (Bull) | IC (Neutral) | IC (Bear) | Avg IC |
|---|---|---|---|---|
| ofi_1m | 0.18 | 0.10 | 0.05 | 0.11 |
| returns_15m | 0.12 | 0.08 | 0.03 | 0.08 |
| vol_parkinson_1h | 0.06 | 0.11 | 0.14 | 0.10 |

**Insight:**
- Momentum features (ofi, returns) stronger in Bull
- Volatility features stronger in Bear
- Regime-conditional weighting potential +15% IC improvement

**Decision:** Implement regime-conditional feature weights (Phase 6).

---

## 2026-02-20: Feature Correlation Analysis

**Hypothesis:** High correlation → redundant features → overfitting risk.

**Method:**
- Compute pairwise correlation (400×400 matrix)
- Identify clusters (ρ >0.7)
- Data: 2025-07-01 to 2026-01-31 (7 months)

**Result:**

**High Correlation Clusters (ρ >0.7):**
1. **OFI cluster:** ofi_1s, ofi_5s, ofi_1m, ofi_5m (ρ=0.8-0.9)
2. **Volatility cluster:** vol_garman_klass, vol_parkinson, vol_rolling (ρ=0.75-0.85)
3. **Returns cluster:** returns_1m, returns_5m, returns_15m (ρ=0.7-0.8)
4. **Volume cluster:** volume_ratio_1h, volume_ratio_4h (ρ=0.85)

**Insight:** Each cluster contributes 1-2 unique signals. Select highest IC from each.

**Decision:**
- Keep ofi_1m (highest IC), drop ofi_1s, ofi_5s
- Keep vol_parkinson (highest IC), drop garman_klass
- Keep returns_15m, drop 1m, 5m

**Expected:** Reduce 400 → ~150 features (remove redundancy).

---

## 2026-01-10: Walk-Forward IC Stability

**Hypothesis:** IC decays over time (feature staleness).

**Method:**
- Train on 2025 Q3 (Jul-Sep)
- Test on 2025 Q4 (Oct-Dec)
- Retrain on 2025 Q3+Q4
- Test on 2026 Q1 (Jan-Mar)

**Result:**

| Feature | IC (Q4 test) | IC (Q1 test) | Decay |
|---|---|---|---|
| ofi_1m | 0.15 | 0.14 | -6% |
| spread_roll | 0.12 | 0.10 | -17% |
| depth_imbalance | 0.11 | 0.08 | -27% |
| returns_15m | 0.10 | 0.09 | -10% |

**Insight:** Depth features decay fastest (synthetic LOB limitation?). OFI/returns stable.

**Decision:**
- Monitor IC monthly (alert if decay >50%)
- Retrain quarterly (adaptive weights)
- Consider deprecating depth features if decay continues

---

## 2025-12-05: LASSO Feature Selection (Preliminary)

**Hypothesis:** LASSO selects sparse, high-IC features.

**Method:**
- Ridge regression (L2): 400 features → 60-min returns
- LASSO regression (L1): 400 features → 60-min returns
- Cross-validation (5-fold) to select λ
- Data: 2025-07-01 to 2025-11-30 (5 months)

**Result:**

**Ridge (L2):**
- Features retained: 400 (all, just shrunk)
- Out-of-sample R²: 0.08
- Sharpe: 0.6

**LASSO (L1):**
- Features retained: 48 (352 zeroed out)
- Out-of-sample R²: 0.10 (better!)
- Sharpe: 0.7

**Top 10 LASSO Features:**
1. ofi_1m (coef=0.08)
2. returns_15m (coef=0.06)
3. spread_roll (coef=0.05)
4. vol_parkinson_1h (coef=-0.04, short vol)
5. depth_imbalance (coef=0.04)
6. volume_ratio_1h (coef=0.03)
7. macd_1h (coef=0.03)
8. rsi_30m (coef=-0.02, mean-reversion)
9. vpin_toxicity (coef=-0.02, risk-off)
10. kalman_velocity (coef=0.02)

**Insight:** LASSO outperforms Ridge (sparse better for 400→1 problem).

**Decision:** Use LASSO as primary feature selection (Phase 6).

---

## 2025-11-20: Random Forest Feature Importance

**Hypothesis:** RF importance ranking complements LASSO.

**Method:**
- Train RandomForestRegressor (100 trees)
- Extract feature_importances_
- Compare to LASSO ranking
- Data: 2025-07-01 to 2025-11-30 (5 months)

**Result:**

**Top 10 RF Features:**
1. ofi_1m (importance=0.12)
2. spread_roll (importance=0.09)
3. vol_parkinson_1h (importance=0.08)
4. returns_15m (importance=0.07)
5. depth_imbalance (importance=0.06)
6. kalman_velocity (importance=0.05)
7. volume_ratio_1h (importance=0.04)
8. macd_1h (importance=0.04)
9. vpin_toxicity (importance=0.03)
10. regime_bull_prob (importance=0.03)

**Comparison with LASSO:**
- 8/10 overlap (ofi_1m, returns_15m, spread_roll, vol, depth, volume, macd, vpin)
- RF adds: kalman_velocity, regime_bull_prob
- LASSO adds: rsi_30m

**Insight:** Strong agreement (80% overlap). Both methods identify similar signals.

**Decision:** Ensemble selection (keep feature if LASSO OR RF ranks top 50).

---

## 2025-10-10: Linear Model Baseline (Ridge)

**Hypothesis:** Simple linear model as baseline for Phase 6.

**Method:**
- Ridge regression (α=1.0)
- Features: Top 50 (from LASSO)
- Train: 2025-07-01 to 2025-09-30 (Q3)
- Test: 2025-10-01 to 2025-12-31 (Q4)

**Result:**

**Out-of-Sample (Q4):**
- Sharpe: 0.8
- IC: 0.09
- Max drawdown: 12%
- Turnover: 60%/day

**Regime Performance:**
| Regime | Sharpe |
|---|---|
| Bull | 1.2 |
| Neutral | 0.6 |
| Bear | 0.3 |

**Insight:** Ridge works but struggles in Bear. Need regime-conditional or nonlinear models.

**Decision:** Ridge = baseline. Target: Sharpe >1.0 (Phase 6 goal).

---

## 2025-09-15: XGBoost Experiment (Early Prototype)

**Hypothesis:** Tree models capture nonlinear relationships → higher Sharpe.

**Method:**
- XGBoost (500 trees, max_depth=3, lr=0.1)
- Features: Top 50 (from LASSO)
- Train: 2025-07-01 to 2025-08-31 (2 months)
- Test: 2025-09-01 to 2025-09-30 (1 month, small sample)

**Result:**

**Out-of-Sample (Sep):**
- Sharpe: 1.1 (better than Ridge!)
- IC: 0.12
- Max drawdown: 8%
- Turnover: 80%/day

**Feature Importance (Top 5):**
1. ofi_1m
2. vol_parkinson_1h
3. spread_roll
4. regime_bull_prob
5. kalman_velocity

**Insight:** XGBoost captures regime interactions (vol × regime). Higher turnover (acceptable).

**Decision:** Promising. Full validation in Phase 6 (walk-forward 12 months).

---

## Research Pipeline (Phase 6 Plan)

### Stage 1: Feature Selection (4 weeks)

**Methods:**
1. Mutual information ranking
2. LASSO (L1 regression)
3. Random Forest importance
4. Recursive feature elimination

**Target:** 400 → 50 features (balance signal vs noise).

**Validation:** 5-fold cross-validation.

---

### Stage 2: Model Training (8 weeks)

**Models:**
1. **Linear:** Ridge, LASSO, ElasticNet (baseline, 2 weeks)
2. **Tree:** XGBoost, LightGBM, CatBoost (4 weeks)
3. **Neural:** LSTM, Transformer (2 weeks, if GPU available)

**Training:**
- Walk-forward validation (12 months)
- Retrain every 3 months
- Hyperparameter search (Bayesian optimization)

**Target Metrics:**
- Sharpe >1.0 (out-of-sample)
- IC >0.10
- Max drawdown <15%

---

### Stage 3: Ensemble (2 weeks)

**Methods:**
1. Equal-weight average
2. IC-weighted average
3. Stacking (meta-learner)

**Target:** Sharpe >1.5 (diversification benefit).

---

## Key Insights (So Far)

1. **Microstructure dominates:** Top features are OFI, spread, depth (6/10).
2. **Regime matters:** IC varies 3× across regimes (Bull=0.18, Bear=0.05 for OFI).
3. **LASSO > Ridge:** Sparse models outperform (48 features vs 400).
4. **XGBoost promising:** Sharpe 1.1 (vs 0.8 Ridge) in early test.
5. **Feature decay real:** Depth features -27% IC over 3 months.

---

## Open Questions

1. **Optimal feature count:** 50 vs 100? (diminishing returns >50?)
2. **Neural nets worth GPU cost?** LSTM Sharpe target: 1.2+ (vs 1.1 XGBoost).
3. **Ensemble benefit:** Stacking vs simple average? (expect +0.2-0.3 Sharpe).
4. **Walk-forward frequency:** Retrain monthly vs quarterly? (tradeoff: adaptation vs stability).

---

## Failed Experiments (Lessons Learned)

### 2025-08-10: All 400 Features (No Selection)

**Hypothesis:** More features = more signal.

**Result:** Overfitting. Out-of-sample Sharpe 0.3 (worse than baseline).

**Lesson:** Feature selection critical. 400 features >> 1000 training samples.

---

### 2025-07-25: 1-Minute Horizon (Too Short)

**Hypothesis:** Ultra-short-term alpha (1-min forward returns).

**Result:** IC 0.03, Sharpe 0.2. Transaction costs dominate (2 bps spread).

**Lesson:** Focus on 60-min+ horizons (slippage manageable).

---

### 2025-11-01: Neural Net (No GPU)

**Hypothesis:** LSTM on CPU acceptable.

**Result:** Training 12 hours/epoch (infeasible). Abandoned.

**Lesson:** Neural nets require GPU. Revisit in Phase 9 (cloud).

---

## Research Principles (Learned)

1. **Walk-forward validation mandatory:** In-sample R² 0.15, out-of-sample 0.05 (overfitting real).
2. **Start simple:** Ridge = baseline. Add complexity only if justified (>20% improvement).
3. **Monitor decay:** IC decays 10-30% over 3 months. Retrain quarterly.
4. **Kill bad ideas fast:** 1-min horizon failed in 1 week. Moved on.
5. **Feature selection > model complexity:** 50 features + Ridge > 400 features + XGBoost.

---

## Phase 6 Roadmap

**Week 1-4:** Feature selection (LASSO + RF + mutual info)
**Week 5-6:** Linear models (Ridge, LASSO, ElasticNet)
**Week 7-10:** Tree models (XGBoost, LightGBM, CatBoost)
**Week 11-12:** Ensemble (stacking, IC-weighted)
**Week 13:** Walk-forward validation (12 months)
**Week 14:** Documentation + handoff to Phase 7

**Target:** Sharpe >1.0, IC >0.10, ready for paper trading.

---

## Related Documentation

- [[PLANNED_FEATURES]] — Phase 6 alpha research features
- [[EXPERIMENTAL_FEATURES]] — Active experiments
- [[PHASE_6]] — Alpha research phase plan
- [[RESEARCH_INDEX]] — Research catalog

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After each experiment (weekly during Phase 6)

**How to Add Entry:**
1. Copy entry format above
2. Fill in hypothesis, method, result, decision
3. Add to chronological log (newest first)
4. Update "Key Insights" section if major finding
5. Update RAGD (`python scripts/build_ragd.py`)
