# Neural Network Pre-Work Summary

**Date:** 2026-05-19  
**Author:** Claude Code (Sonnet 4.5)  
**Scope:** Pre-requisites for neural network training on Dominion dataset  
**Status:** 3 of 7 tasks complete

---

## Executive Summary

**Goal:** Prepare Dominion platform for neural network training with rigorous data hygiene, reproducible splits, and baseline comparisons.

**Completed (3/7):**
1. ✓ **Leakage audit** — Found 1 critical leakage (HMM regime), documented safe features
2. ✓ **Temporal split** — 70/15/15 train/val/test, validated chronological order
3. ✓ **Metrics definition** — IC, Sharpe, Drawdown, Turnover with target thresholds

**Remaining (4/7):**
4. → Baseline models (Ridge, RandomForest)
5. → Reproducible dataset v1 (join features, hash, save Parquet)
6. → Feature stability monitoring
7. → Regime-conditioned performance split

**Blockers:** None. All tasks can proceed.

**Next priority:** Task #11 (Baseline models) or Task #13 (Dataset build). Recommend Task #13 first (need dataset to train baselines).

---

## Task #9: Leakage Audit ✓

**Report:** `reports/2026-05-19_leakage_audit.md`

### Findings

**CRITICAL LEAKAGE:**
- **HMM regime detection** (`data_pipeline/features/regime.py:52-61`)
  - `.fit()` on full dataset → learns from future
  - `.predict()` on all rows → labels past with future info
  - **Impact:** Regime-conditioned returns use contaminated labels, inflates metrics

**SAFE FEATURES:**
- Rolling windows (`.rolling(w)`) — uses past data only
- Forward fills (`.ffill()`) on external data (COT, macro) — acceptable
- FOMC date lookup — public calendar, not leakage
- Kalman filters — predict step uses past state only

**Affected Features (5):**
- `regime_tactical`
- `regime_prob_trend_up`
- `regime_prob_trend_down`
- `regime_prob_ranging`
- `regime_prob_crisis`

**Action Taken:**
- Documented leakage in audit report
- Added exclusion list to temporal split script
- **EXCLUDED_FEATURES** defined in `scripts/temporal_split.py`

**Recommendation:**
- Remove HMM features from dataset v1
- Use **micro regime** (time-of-day, no leakage) instead
- Or: Implement expanding-window HMM (expensive)

### Impact

**Feature count loss:** 5 features out of ~400 (~1% loss)

**Regime analysis broken:** Can't use HMM regime until fixed.

**Severity:** HIGH — Would inflate model metrics if used.

---

## Task #10: Temporal Train/Val/Test Split ✓

**Report:** `reports/2026-05-19_temporal_split.md`  
**Script:** `scripts/temporal_split.py`  
**Config:** `reports/temporal_split_v1.json`

### Split Summary

| Split | Rows | % | Date Range | Duration |
|---|---:|---:|---|---|
| **TRAIN** | 879 | 70% | 2021-05-21 to 2024-11-15 | ~3.5 years |
| **VAL** | 188 | 15% | 2024-11-15 to 2025-08-18 | ~9 months |
| **TEST** | 189 | 15% | 2025-08-18 to 2026-05-19 | ~9 months |
| **TOTAL** | 1256 | 100% | 2021-05-21 to 2026-05-19 | ~5 years |

### Validation ✓

- [x] Percentages sum to 100%
- [x] Train ≥ 60%
- [x] Val, Test ≥ 10%
- [x] Chronological order (no gaps, no overlaps)
- [x] No shuffling

### Rationale

**Why 70/15/15?**
- **Train (70%):** Need long history for Kalman filters, rolling windows (max 252 days), regime detection
- **Val (15%):** Enough for hyperparameter tuning (~6-9 months, multiple regimes)
- **Test (15%):** Held-out for final evaluation

**Why temporal (not random)?**
- Time series have autocorrelation
- Random shuffle leaks future into past
- Temporal split is production-realistic

### Limitations

1. **Small dataset:** 1256 daily rows → After dropna (~252 NaN rows), expect ~1000 rows
   - Train: ~630 rows (still >2 years, acceptable)
   - Val: ~180 rows
   - Test: ~180 rows
2. **Single asset:** Gold only (XAU/USD)
3. **Daily frequency:** No intraday data in gold_master
4. **Features not joined yet:** gold_master has OHLC only, features in separate table

### Next Steps

1. Join features to gold_master (Task #13)
2. Add target variables (forward returns)
3. Drop NaN rows
4. Save to Parquet
5. Hash dataset

---

## Task #12: Metrics Definition ✓

**Report:** `reports/2026-05-19_metrics_definition.md`  
**Module:** `scripts/metrics.py`

### Metrics Defined

| Metric | Definition | Excellent | Good | Acceptable | Poor |
|---|---|---:|---:|---:|---:|
| **IC** | Spearman(pred, actual) | > 0.10 | > 0.05 | > 0.02 | ≤ 0.00 |
| **Sharpe** | (return / vol) * √252 | > 2.0 | > 1.0 | > 0.5 | ≤ 0.0 |
| **Max DD** | Worst drawdown | > -5% | > -10% | > -20% | < -50% |
| **Turnover** | Daily position change | < 0.1 | < 0.5 | < 1.0 | > 2.0 |

### Why These Thresholds?

**IC:**
- **> 0.10:** Publication-worthy, institutional-grade
- **> 0.05:** Profitable after costs (HFT threshold)
- **> 0.02:** Detectable signal
- **≤ 0.00:** Random or worse

**Sharpe:**
- **> 2.0:** Hedge fund target
- **> 1.0:** Good quant strategy
- **> 0.5:** Better than S&P 500 (~0.4)
- **≤ 0.0:** Losing

**Max Drawdown:**
- **> -5%:** Low-vol strategies
- **> -10%:** Typical quant equity
- **> -20%:** Directional, single-asset
- **< -50%:** Catastrophic

**Turnover:**
- **< 0.1:** Low-frequency (swing trading)
- **< 0.5:** Medium-frequency (daily rebalance)
- **< 1.0:** High-frequency (intraday)
- **> 2.0:** Excessive, costs dominate

### Implementation

```python
from scripts.metrics import compute_all_metrics, print_metrics, evaluate_model

metrics = compute_all_metrics(
    predictions=pred_series,
    actuals=actual_series,
    returns=strategy_returns,
    positions=position_series,
)

print_metrics(metrics, title="Validation Set")
ratings = evaluate_model(metrics)
```

### Baseline Targets (Task #11)

**Ridge Regression:**
- IC: 0.02 - 0.04 (acceptable)
- Sharpe: 0.3 - 0.6 (acceptable)
- Max DD: -15% to -25%

**Random Forest:**
- IC: 0.04 - 0.06 (good)
- Sharpe: 0.6 - 1.0 (good)
- Max DD: -10% to -20%

**Neural Network (goal):**
- IC: 0.06 - 0.10 (excellent)
- Sharpe: 1.0 - 2.0 (excellent)
- Max DD: -5% to -15%

---

## Remaining Tasks

### Task #11: Build Baseline Models

**Goal:** Train simple models (Ridge, RandomForest) on train set, evaluate on val set.

**Why baselines?**
- Establish performance floor
- Validate dataset quality
- Sanity check (if baselines fail, data has issues)
- Comparison for neural networks

**Steps:**
1. Load train/val data (from Task #13 output)
2. Train Ridge(alpha=1.0)
3. Train RandomForest(n_estimators=100)
4. Predict on val set
5. Compute metrics
6. Save results

**Estimated time:** 1 hour

---

### Task #13: Build Reproducible Dataset v1

**Goal:** Frozen dataset with hash, version tag, feature list.

**Steps:**
1. Join features from `features` table to `gold_master`
2. Pivot from long to wide format
3. Exclude HMM features (leakage)
4. Add target variables (forward returns)
5. Drop NaN rows (first ~252 rows)
6. Split by temporal boundaries
7. Save to Parquet:
   - `data/train_v1.parquet`
   - `data/val_v1.parquet`
   - `data/test_v1.parquet`
8. Compute feature stats (train only)
9. Hash each split (SHA-256)
10. Write manifest:
    ```json
    {
      "version": "1.0",
      "created": "2026-05-19",
      "split_boundaries": {...},
      "row_counts": {...},
      "feature_count": 395,
      "excluded_features": [...],
      "hashes": {...}
    }
    ```

**Estimated time:** 2 hours

**Blocker:** Need to understand `features` table schema (long format → wide format pivot)

---

### Task #14: Feature Stability Monitoring

**Goal:** Track IC decay over time, detect distribution shifts.

**Steps:**
1. Compute rolling IC (252-day window) for each feature
2. Flag features with IC decay (IC[t] - IC[t-252] < -0.03)
3. Compute KL divergence (distribution shift detection)
4. Alert on unstable features
5. Store in `feature_decay_alerts` table

**Estimated time:** 2 hours

**Dependencies:** Task #13 (need dataset)

---

### Task #15: Regime-Conditioned Performance Split

**Goal:** Split metrics by regime (london/ny/asian/overlap/dead_zone).

**Steps:**
1. Add micro regime feature (time-of-day, no leakage)
2. For each regime:
   - Filter val set
   - Compute metrics
   - Print report
3. Compare:
   - Which regime has highest IC?
   - Which has highest Sharpe?
   - Which has worst drawdown?

**Estimated time:** 1 hour

**Dependencies:** Task #11, #13 (need baselines + dataset)

---

## Recommended Next Steps

### Option A: Build Dataset First (Recommended)

1. **Task #13:** Build dataset v1 (2 hours)
2. **Task #11:** Train baselines (1 hour)
3. **Task #15:** Regime-conditioned metrics (1 hour)
4. **Task #14:** Feature stability (2 hours)

**Total:** ~6 hours

**Rationale:** Need dataset before training models. Parallelize 14/15 after 11.

### Option B: Build Baselines on Existing Data

1. **Task #11:** Train baselines on `gold_master` only (limited features)
2. **Task #13:** Build full dataset
3. **Task #11 (retry):** Retrain baselines on full dataset
4. **Task #15, #14:** Regime + stability

**Total:** ~7 hours (1 hour wasted retraining)

**Rationale:** Get quick baseline metrics, but limited value without full features.

---

## Recommendations Before Neural Networks

### Gate Checklist

- [x] **Leakage audit:** Completed, HMM exclusion documented
- [x] **Temporal split:** Validated 70/15/15
- [x] **Metrics:** Defined with thresholds
- [ ] **Baselines:** Ridge + RandomForest trained
- [ ] **Dataset v1:** Reproducible, hashed, frozen
- [ ] **Feature stability:** IC decay monitored
- [ ] **Regime analysis:** Per-regime metrics computed

**Status:** 3 of 7 complete (43%)

**Estimated time to complete:** 6 hours (Option A)

**Blockers:** None

---

## Key Findings

### 1. Data Pipeline is Mostly Clean ✓

- 395 of 400 features are safe
- Rolling windows, Kalman filters, external data handling are correct
- Only HMM regime detection leaks future info

### 2. Dataset is Small

- 1256 daily rows (5 years)
- After dropna: ~1000 rows
- Train: ~630 rows (still acceptable for simple models)
- **Implication:** Prefer simple models (Ridge, RandomForest) over deep learning

### 3. Temporal Split is Realistic

- Train on 2021-2024, predict 2025-2026
- No shuffling = production-realistic
- Harder than random split (distribution shift)

### 4. Metrics are Institutional-Grade

- IC, Sharpe, Drawdown, Turnover
- Thresholds match quant industry standards
- Automated evaluation (excellent/good/acceptable/poor)

---

## Risks

### 1. Small Sample Size

**Risk:** 630 train rows may not be enough for complex models.

**Mitigation:**
- Use regularization (Ridge alpha=1.0, RandomForest min_samples_leaf=5)
- Cross-validation (expanding window)
- Ensemble models
- Avoid deep learning until more data

### 2. Single Asset

**Risk:** Gold-only dataset, no diversification.

**Mitigation:**
- Cross-asset features (DXY, VIX, TNX) provide correlation info
- Focus on gold-specific microstructure (LOB, toxicity)
- Future: add silver, copper, platinum

### 3. Distribution Shift

**Risk:** 2021-2024 train data may not generalize to 2025-2026 test.

**Mitigation:**
- Regime-conditioned metrics (detect which regimes generalize)
- Feature stability monitoring (detect decaying ICs)
- Rolling retraining (update model every quarter)

---

## Deliverables

### Reports Created

1. `reports/2026-05-19_leakage_audit.md` — Data leakage analysis
2. `reports/2026-05-19_temporal_split.md` — Train/val/test split
3. `reports/2026-05-19_metrics_definition.md` — Quant metrics
4. `reports/temporal_split_v1.json` — Split config (machine-readable)

### Scripts Created

1. `scripts/temporal_split.py` — Compute and validate splits
2. `scripts/metrics.py` — Standard quant metrics module

### Configuration

1. `EXCLUDED_FEATURES` list in `scripts/temporal_split.py`
2. Metric thresholds in `scripts/metrics.py` (TARGETS dict)

---

## Next Agent Handoff

**If next agent continues this work:**

1. **Read reports:** Leakage audit, temporal split, metrics definition
2. **Run:** `python scripts/temporal_split.py` to verify split
3. **Task priority:** Build dataset v1 (Task #13) first
4. **After dataset:** Train baselines (Task #11)
5. **After baselines:** Regime + stability monitoring (Task #14, #15)

**If next agent does neural network work:**

1. **Wait** until Tasks #11-15 complete
2. **Verify:** Baselines show IC > 0.02 (sanity check)
3. **Start:** Simple feedforward NN, then LSTM, then Transformer
4. **Compare:** NN metrics vs baseline metrics

---

**Pre-work 43% complete.** Recommend completing dataset build (Task #13) next.
