# FINAL DATASET VALIDATION VERDICT

**Dataset:** `data/hydra_xauusd_m5_master.parquet`  
**Date:** 2026-05-21  
**Validator:** Claude Code (Dominion validation protocol)

---

## VERDICT: **DATASET_NEEDS_REPAIR**

**Status:** Not ready for production training.  
**Next Steps:** Fix critical issues below, then re-validate.

---

## EXECUTIVE SUMMARY

**Problem:** ML models trained on clean features perform at random chance (AUC=0.54, Sharpe=-19). Only forward-looking leaked features showed predictive power (AUC=0.93 with leakage).

**Root Cause:** Dataset contains minimal true predictive signal when point-in-time safety enforced. High baseline performance (always-long Sharpe=273, previous-bar AUC=0.80) driven by test period trend + M5 autocorrelation, not learnable features.

**Impact:** Cannot proceed with strategy development until dataset rebuilt with better feature engineering.

---

## VALIDATION RESULTS

### 1. DATA QUALITY CHECKS

| Check | Status | Details |
|-------|--------|---------|
| Dataset loads | ✓ | 789,257 rows × 1,147 cols, 3.5 GB |
| Time column | ✓ | Present, Datetime type |
| Time range | ✗ | **1970-01-01** → 2026-05-20 (Unix epoch bug) |
| Duplicates | ✓ | None |
| M5 spacing | ✓ | 90.4% correct (3,176 gaps = weekends) |
| Null rate | ✓ | 0.05% overall |
| Label nulls | ⚠ | 36.7% → only 499,921 usable rows (63%) |
| Constant features | ✗ | 22 H1 features all zero |
| Infinite values | ✓ | None |
| Label leakage | ✗ | Forward features present (excluded in clean run) |

**Score:** 7/10 checks passed

---

### 2. TRAINING VALIDATION (CLEAN FEATURES ONLY)

**Configuration:**
- Train/Val/Test: 60/20/20 split (temporal)
- Features: 812 clean (excluded `fwd_*`, `forward_*`, `next_*`, `future_*`, `lead_*`)
- Label: `label_6b` (6-bar forward return, binary up/down)
- Model: RandomForest (100 trees, depth 10)

**Baseline Performance (Test Set, 100K bars):**

| Strategy | AUC | Bal Acc | Sharpe | Net Return | Max DD |
|----------|-----|---------|--------|------------|--------|
| Always Long | 0.500 | 0.500 | **273.6** | +50,764 | 0 |
| Previous Bar | **0.805** | 0.805 | 131.5 | +31,258 | 8 |
| Momentum (20) | 0.666 | 0.506 | 273.3 | +50,734 | 15 |
| Mean Reversion | 0.000 | 0.000 | -273.6 | -50,764 | 50,764 |

**ML Model Performance (Clean Features):**

| Model | AUC | Bal Acc | Sharpe | Net Return | Max DD |
|-------|-----|---------|--------|------------|--------|
| Top 100 | 0.538 | 0.524 | -19.3 | -5,088 | 5,110 |
| Top 200 | 0.539 | 0.526 | -31.1 | -8,178 | 8,180 |
| All 812 | 0.529 | 0.521 | -58.4 | -15,094 | 15,121 |

**Analysis:**
- ML models at **random chance** (AUC ≈ 0.54 vs 0.50 random)
- **Negative Sharpe** across all feature sets
- **Cannot beat simple baselines** (previous-bar AUC=0.80)
- More features = worse performance (overfitting noise)

**Top 5 Features (Importance):**
1. `gld_z60d` (0.0429) — GLD ETF 60-day z-score
2. `macro_DGS20_z252` (0.0224) — 20Y Treasury 1Y z-score
3. `iau_z60d` (0.0199) — IAU ETF 60-day z-score
4. `macro_T10Y3M_z252` (0.0158) — 10Y-3M spread 1Y z-score
5. `slv_z60d` (0.0156) — Silver ETF 60-day z-score

→ Top features = slow-moving macro/ETF indicators (60d-252d windows)  
→ Poor predictors of 6-bar M5 moves (30-minute horizon)

---

### 3. LEAKED MODEL COMPARISON (FOR REFERENCE)

**First run (with forward features included):**

| Model | AUC | Sharpe | Net Return |
|-------|-----|--------|------------|
| Top 100 (leaked) | **0.934** | 189.5 | +40,984 |
| Top 100 (clean) | **0.538** | -19.3 | -5,088 |

**Delta:** AUC drops from 0.93 → 0.54 when leakage removed.  
**Conclusion:** Original 0.93 AUC = model seeing future. No real predictive power.

---

## CRITICAL ISSUES

### 1. **Time Starts at 1970 (Unix Epoch Bug)**
- **Severity:** High
- **Impact:** Timestamp conversion error, likely milliseconds treated as seconds
- **Fix:** Re-export with correct `pd.to_datetime(time, unit='s')` or `unit='ms'`

### 2. **22 Constant H1 Features**
- **Severity:** Medium
- **Impact:** All `h1_*` features = 0, wasted columns, pipeline failure
- **Fix:** Debug H1 data source or remove features
- **List:** `h1_ret_1b`, `h1_ret_3b`, `h1_atr_pct`, `h1_ema20_pct`, `h1_rsi14`, etc.

### 3. **37% Label Nulls**
- **Severity:** Medium
- **Impact:** Only 63% of dataset usable for training (499K / 789K rows)
- **Fix:** Investigate why `label_6b` missing at ends/gaps, extend coverage

### 4. **Minimal True Predictive Signal**
- **Severity:** **CRITICAL**
- **Impact:** Clean features cannot predict 6-bar M5 returns (AUC=0.54)
- **Root Cause:** Feature/label mismatch
  - Features = slow (60d-252d macro indicators)
  - Label = fast (6-bar M5 = 30 minutes)
- **Fix Options:**
  - Add M5 microstructure features (bid-ask, order flow, tick volume patterns)
  - Switch to daily/H4 labels (align with feature timescales)
  - Add regime filters (only train on high-conviction regimes)
  - Feature engineer tick-level signals

### 5. **Test Period Bias**
- **Severity:** Medium
- **Impact:** Always-long Sharpe=273 inflates baseline expectations
- **Root Cause:** Test period (20% of 499K rows ≈ 100K bars) strongly bullish
- **Fix:** Walk-forward across multiple regime periods (bull/bear/ranging)

---

## RECOMMENDATIONS

### Immediate Actions
1. **Fix timestamp bug** (1970 epoch)
2. **Remove/fix 22 constant H1 features**
3. **Investigate label null rate** (why 37% missing?)
4. **Document excluded forward-looking patterns** (maintain point-in-time safety)

### Feature Engineering Required
Dataset needs M5-scale features to predict M5-scale labels:

**High Priority:**
- Order flow toxicity (VPIN, trade imbalance)
- Bid-ask spread dynamics (roll model, Corwin-Schultz)
- Tick volume patterns (volume bars, tick rule)
- Recent price action (1m-5m momentum, breakout signals)
- Intrabar microstructure (OHLC patterns, wicks, body ratio)

**Current Features:**
- Macro: 60d-252d windows → too slow for 30-min prediction
- ETF z-scores: 60d window → lags intraday moves
- Need sub-hourly features for sub-hourly prediction

### Alternative Approaches
1. **Switch to H4/Daily labels** (align timescales with existing features)
2. **Regime-conditional models** (filter low-conviction periods)
3. **Ensemble with baselines** (previous-bar AUC=0.80 is strong)
4. **Multi-timeframe fusion** (M5 microstructure + H4 macro)

---

## TECHNICAL DETAILS

**Dataset Shape:**
- Raw: 789,257 rows × 1,147 cols
- After label dropna: 499,921 rows (63%)
- Clean features: 812 (after removing 22 constant + 309 labels)
- Usable features: ~600 after null filter

**Top Features (by RF importance):**
- GLD/IAU/SLV z-scores (60d)
- Treasury yields z-scores (252d)
- All slow-moving macro indicators

**Label:**
- `label_6b`: 6-bar forward return (M5 × 6 = 30 minutes)
- Balance: 50.0% up / 50.0% down (perfect)
- Nulls: 36.7% (289K rows)

**Baselines:**
- Previous-bar direction: AUC=0.80 (strong M5 autocorrelation)
- Always-long: Sharpe=273 (test period bullish)
- Momentum(20): Sharpe=273, AUC=0.67

**ML Models (clean):**
- All at random chance: AUC=0.53-0.54
- Negative Sharpe: -19 to -58
- Fail to beat any baseline

---

## FINAL DECISION MATRIX

| Criterion | Pass? | Blocker? |
|-----------|-------|----------|
| Data loads correctly | ✓ | No |
| Time column valid | ⚠ (1970 bug) | **Yes** |
| No duplicates | ✓ | No |
| Acceptable null rate | ✓ (<10%) | No |
| No constant features | ✗ (22 H1 cols) | No |
| No label leakage | ✓ (after fix) | No |
| ML beats baselines | ✗ (AUC 0.54 vs 0.80) | **Yes** |
| Positive Sharpe | ✗ (all negative) | **Yes** |

**Blockers:** 3  
**Verdict:** **DATASET_NEEDS_REPAIR**

---

## COMPARISON TO INITIAL ASSESSMENT

**Initial Claim:** "Production-ready, 789K rows, 1,147 features"

**Reality:**
- Timestamp broken (1970 bug)
- 22 features constant (H1 pipeline dead)
- 309 features are labels (not features)
- 3 features leaked (forward returns)
- 812 clean features, but...
  - No M5-scale predictive power (AUC=0.54)
  - Cannot beat previous-bar baseline (AUC=0.80)
  - Negative Sharpe on all models

**Status:** Not production-ready. Requires major feature engineering.

---

## NEXT STEPS

1. **Fix Critical Bugs:**
   - Correct timestamp (1970 → actual dates)
   - Remove H1 dead features
   - Investigate label nulls

2. **Re-engineer Features:**
   - Add M5 microstructure features
   - OR switch to H4/D1 labels (match feature timescales)

3. **Re-validate:**
   - Run this script again after fixes
   - Target: AUC > 0.80 (beat previous-bar baseline)
   - Target: Sharpe > 1.0 (acceptable risk-adjusted return)

4. **If Still Fails:**
   - Consider dataset unsuitable for M5 prediction
   - Focus on H4/Daily strategies instead
   - Revisit data sources (need tick data for M5 alpha)

---

## REFERENCES

- Validation script: `scripts/training_validation.py`
- Validation report (JSON): `reports/training_validation_report.json`
- Quality check report: `reports/master_validation_report.json`
- Dataset: `data/hydra_xauusd_m5_master.parquet`

---

**Generated:** 2026-05-21 09:51 UTC  
**Validator:** Claude Code (Dominion V2)  
**Protocol:** RAGD validation pipeline
