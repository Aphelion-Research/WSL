# Walk-Forward Research Report

**Date:** 2026-05-20  
**Status:** RESEARCH_EXPERIMENT_FAIL

---

## Executive Summary

**Dataset:** M5 (5-minute XAUUSD), 100K samples, 148 features  
**Validation:** Walk-forward (5 folds, 60-bar embargo)  
**Models:** RandomForest, GradientBoosting, LightGBM  
**Result:** NO ROBUST EDGE FOUND

**Best model:** RandomForest  
**Best AUC:** 0.5132 (barely above random)  
**Net returns:** Negative after costs (-0.01%)

---

## Registry Allocation Audit

### Verdict: ✅ CONSISTENT

**Registry structure:**
- Total columns: 3,000
- Available: 2,255
- Unavailable: 695
- Reserved: 50

**Block B allocation:**
- Designed capacity: 195 slots
- Purpose: Tick microstructure (unavailable)
- Current use: 90 semantic M5 features mapped
- Remaining: 105 null placeholders

**Contract satisfied:**
- Registry totals exactly 3,000 columns ✓
- Block allocations match BLOCK_ALLOCATIONS dict ✓
- No mismatches or overflows ✓

---

## Semantic Mapping Validation

### Verdict: ✅ VALID

**Mapping file:** `data/registry/semantic_column_mapping.json`

**Validation results:**
- Mapped features: 90
- All slots exist in dataset: ✓
- All slots have non-null data (<95% null): ✓
- All slots marked trainable: ✓
- No label/reserved conflicts: ✓
- No duplicate slots: ✓

**New quality gate added:**
- `check_semantic_mapping()` gate now runs during validation
- Gate checks slot existence, null fraction, trainable flag, conflicts
- Current dataset passes gate ✓

---

## Walk-Forward Validation Setup

**Configuration:**
- Folds: 5
- Embargo: 60 bars between train/test
- Chronological splits (no shuffle)
- No overlap between folds

**Fold structure (folds 1-4 valid):**
```
Fold 1: train=20,000, test=20,000
Fold 2: train=40,000, test=20,000
Fold 3: train=60,000, test=20,000
Fold 4: train=80,000, test=20,000
Fold 5: NaN (insufficient test samples)
```

**Note:** Fold 5 produced NaN results (test set too small or edge case). Analysis based on folds 1-4.

---

## Baseline Comparisons

**Baseline strategies (avg return %):**
```
always_long:              0.0006%
always_short:            -0.0006%
random_50_50:             0.0006%
prev_bar_direction:       0.0005%
momentum_5bar:            0.0241% ← Best baseline
mean_reversion_5bar:     -0.0241%
```

**Key insight:** Simple 5-bar momentum beats all ML models.

---

## Model Results (Folds 1-4 Average)

### RandomForest
```
AUC:        0.5132  (barely above random 0.50)
Accuracy:   50.28%
F1:         0.4144
Precision:  51.85%
Recall:     38.09%
Net return: -0.0101% (negative after costs)
Sharpe:     NaN
Training:   ~3s per fold
```

### GradientBoosting
```
AUC:        0.5057  (nearly random)
Accuracy:   49.78%  (worse than random!)
F1:         0.2934
Precision:  52.14%
Recall:     24.40%
Net return: -0.0105% (negative)
Sharpe:     NaN
Training:   ~260s per fold
```

### LightGBM
```
AUC:        0.5126  (barely above random)
Accuracy:   50.49%
F1:         0.4435
Precision:  51.70%
Recall:     41.24%
Net return: -0.0098% (negative)
Sharpe:     NaN
Training:   ~8s per fold
```

---

## Cost-Aware Analysis

**Assumptions:**
- Spread: 2.0 pips round-trip
- Conversion: 1 pip = 0.005% (at ~$2000 XAUUSD)
- Cost per trade: ~0.01%

**Findings:**
- **All models lose money after costs**
- Net returns: -0.01% (models) vs +0.024% (momentum baseline)
- Gross returns near zero → edge too small to survive costs
- Models predict positive 24-40% of time (conservative)
- Returns when long: ~0.0007% (tiny)
- Returns when short: ~-0.0004% (tiny)

**Verdict:** No tradable edge. Costs exceed signal.

---

## Cross-Fold Consistency

**AUC by fold (RF):**
```
Fold 1: 0.505
Fold 2: 0.506
Fold 3: 0.518
Fold 4: 0.503
Fold 5: 0.524 (NaN results)
```

**Observations:**
- AUC varies 0.503-0.524 (unstable)
- No fold exceeds 0.53 threshold
- Weak evidence of any persistent edge
- Returns consistently negative after costs

---

## Feature Analysis

**Current features (148 total):**
- 90 semantic M5 features (returns, volatility, momentum, spread, volume)
- 58 registry features (OHLCV, rolling, technical, macro, COT, regime)

**Issues:**
1. **Leakage validation:** BASIC_CHECK_ONLY (not full PIT audit)
2. **Label horizon:** Forward returns (simple) - may not capture intraday structure
3. **Feature quality:** 148 features but AUC ~0.51 suggests weak signal
4. **Timeframe mismatch:** M5 bars but no microstructure (tick data unavailable)

---

## Why No Edge Found

**Primary reasons:**

1. **Signal too weak:** AUC 0.51-0.52 = barely better than random
2. **Costs too high:** 0.01% cost > ~0.0001% gross edge
3. **Feature noise:** 148 features but no strong predictive power
4. **Label noise:** Simple forward returns may not be right target
5. **Timeframe limitations:** M5 without tick microstructure misses HFT alpha
6. **Basic validation:** Leakage check not comprehensive (may have hidden lookahead)

**Secondary factors:**
- Embargo may be insufficient (60 bars = 5 hours)
- No feature selection (using all 148 features indiscriminately)
- No hyperparameter tuning (default params)
- No ensemble methods
- No regime filtering

---

## Comparison to Requirements

**Original goal:** Upgrade from basic research to realistic walk-forward test

**Achieved:**
- ✓ Registry audit (consistent)
- ✓ Semantic mapping validation (valid + gate added)
- ✓ Walk-forward implementation (5 folds, embargo, chronological)
- ✓ Cost-aware metrics (spread-adjusted returns)
- ✓ Baseline comparisons (6 baselines tested)
- ✓ Multiple models (RF, GBM, LGBM)

**Not achieved:**
- ✗ Positive edge (all models lose money)
- ✗ AUC > 0.53 consistently
- ✗ Cost-adjusted returns > 0
- ✗ Beats momentum baseline

---

## Status Classification

**RESEARCH_EXPERIMENT_FAIL**

**Criteria:**
- Best AUC: 0.5132 (< 0.53 threshold)
- Best net return: -0.0101% (< 0 threshold)
- Does not beat simple momentum baseline
- No evidence of persistent edge across folds

**Not production-ready because:**
- No tradable edge found
- Costs exceed signal
- AUC barely above random
- Leakage validation still basic
- No walk-forward profit

---

## Next Steps (Not Executed)

**If continuing research:**

1. **Feature engineering:**
   - Add tick microstructure (if data available)
   - Engineer intraday session features
   - Add regime-conditional features
   - Feature selection (remove noise)

2. **Better labels:**
   - Multi-horizon targets
   - Directional labels with magnitude
   - Volatility-scaled targets
   - Cost-aware label design

3. **Full PIT audit:**
   - Manual inspection of all feature calculations
   - Verify no forward-looking ops
   - Check join logic for asof safety

4. **Hyperparameter tuning:**
   - Grid search per fold
   - Bayesian optimization
   - Ensemble meta-learners

5. **Alternative approaches:**
   - Survival analysis (time-to-target)
   - Reinforcement learning
   - Deep learning (LSTM/Transformer)
   - Portfolio construction

**However:** With AUC 0.51, more feature engineering unlikely to help. Problem may be:
- Wrong timeframe (M5 too slow for XAUUSD scalping)
- Wrong asset (gold intraday has low Sharpe)
- Insufficient data (100K bars = 1.4 years insufficient for ML)
- Wrong approach (supervised classification may not work for M5 gold)

---

## Files Generated

**Walk-forward outputs:**
- `runs/walk_forward_results_20260520_193621.csv` — Per-fold metrics
- `runs/walk_forward_summary_20260520_193621.json` — Aggregate summary

**Previous outputs:**
- `data/hydra_m5_dataset.parquet` — M5 dataset (100K × 3001)
- `data/registry/semantic_column_mapping.json` — Feature mapping
- `runs/multi_training_research_20260520_190957.csv` — Earlier single-split results

**Modified code:**
- `dominion/quality/gates.py` — Added `check_semantic_mapping()` gate
- `scripts/run_walk_forward_training.py` — Walk-forward validation script

---

## Conclusion

**M5 dataset contract:** ✅ SATISFIED  
**Semantic mapping:** ✅ VALID  
**Walk-forward validation:** ✅ IMPLEMENTED  
**Tradable edge:** ❌ NOT FOUND

**Bottom line:** 
Dataset is structurally sound. Quality gates pass. 148 features available. But AUC ~0.51 and negative cost-adjusted returns indicate **no robust predictive edge** for M5 XAUUSD direction using current features and labels.

Simple 5-bar momentum (+0.024%) beats all ML models (-0.01%). Either need:
- Different timeframe (tick, M1, or H1+)
- Different features (tick microstructure, order flow)
- Different targets (volatility, regime, spread prediction)
- Different asset (more predictable than gold)

**Status:** RESEARCH_EXPERIMENT_FAIL (honest assessment)

---

**Report completed:** 2026-05-20  
**Dataset:** data/hydra_m5_dataset.parquet (100,000 × 3,001)  
**Validation:** Walk-forward (5 folds, 60-bar embargo)  
**Best model:** RandomForest (AUC 0.5132)  
**Net return:** -0.0101%  
**Verdict:** NO EDGE
