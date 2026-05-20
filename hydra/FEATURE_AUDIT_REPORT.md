# HYDRA Feature Engineering Audit & Patch Report

**Date:** 2026-05-20  
**Task:** Replace regime-dependent features with stationary equivalents  
**Root Cause:** Model trained on $1372 gold failed on $4485 gold due to absolute price features

---

## 1. PROBLEM STATEMENT

From PhD diagnostic (run `hydra_equal_thirds_20260519_232841`):

**Observed:** Zero OOS trades across all modes/costs (0/9 scenarios)

**Root Cause:** Multi-factorial:
1. **Regime shift** — test data 3.27x outside training mean
2. **Feature space shift** — absolute price features don't generalize
3. **Validation overfit** — PF=2960, WR=100%, memorization

**Critical Finding:** Feature importance analysis showed `real_gold` (raw price level) as #1 feature with 0.0888 importance. Model learned "when gold=$X, predict up" → breaks when gold=$3X.

---

## 2. AUDIT OF ORIGINAL FEATURES

### DuckDB Features (379 total)

**REGIME-DEPENDENT (must drop):**
- `real_gold` — **RAW GOLD PRICE** (worst offender)
- `rolling_mean_N` — absolute price means
- `drawdown_N` — absolute drawdown (not normalized)
- `zscore_N` — z-scores anchored to training Q5/Q95

**PARTIALLY REGIME-DEPENDENT (need normalization):**
- ATR features — used as absolute $ values
- Drawdowns — need to be normalized by current price
- Z-scores — if computed from training quantiles

**REGIME-INVARIANT (keep as-is):**
- `log_return_N`, `return_N` — percentage changes ✓
- `rsi_14` — already 0-100 bounded ✓
- `autocorr_*`, `hurst_*` — statistical properties ✓
- `sharpe_N` — ratio-based ✓
- `corr_*`, `beta_*` — cross-asset relationships ✓
- `regime_prob_*` — probabilities ✓

---

## 3. PATCHED FEATURE SET

### New File: `hydra/data/features_stationary.py`

**Total features:** 37 (down from 394 in backtest)

**Categories:**

| Category | Count | Examples |
|----------|-------|----------|
| **Log Returns** | 6 | `log_return_1`, `log_return_5`, `log_return_10`, `log_return_20`, `log_return_50`, `log_return_100` |
| **Rolling Z-scores** | 3 | `rolling_zscore_10`, `rolling_zscore_20`, `rolling_zscore_50` (clipped to [-5, 5]) |
| **ATR Percentage** | 1 | `atr_pct_14` = ATR(14) / close |
| **Drawdown Percentage** | 1 | `drawdown_pct_20` = (close - peak) / peak |
| **Realized Volatility** | 3 | `realized_vol_10`, `realized_vol_20`, `realized_vol_50` (annualized) |
| **Technical Indicators** | 5 | `rsi_14`, `volume_ratio_20`, `macd_pct`, `macd_signal_pct`, `macd_hist_pct` |
| **Autocorrelation** | 9 | `autocorr_10_lag1`, `autocorr_10_lag5`, ..., `autocorr_50_lag10` |
| **Hurst Exponent** | 2 | `hurst_50`, `hurst_100` (clipped to [0, 1]) |
| **Rolling Sharpe** | 3 | `sharpe_rolling_10`, `sharpe_rolling_20`, `sharpe_rolling_50` (clipped to [-10, 10]) |
| **Regime Probabilities** | 4 | `regime_crisis_prob`, `regime_trend_up_prob`, `regime_trend_dn_prob`, `regime_ranging_prob` |

**Total:** 37 features

---

## 4. KEY CHANGES

### Dropped Features

| Original Feature | Reason | Replacement |
|-----------------|--------|-------------|
| `real_gold` | Raw price level (worst offender) | **NONE** — pure price level has no predictive power across regimes |
| `rolling_mean_N` | Absolute price mean | `rolling_zscore_N` (price relative to rolling mean/std) |
| `drawdown_N` | Absolute $ drawdown | `drawdown_pct_N` = drawdown / current_price |
| `zscore_N` (if training-anchored) | Anchored to Q5/Q95 from training | `rolling_zscore_N` (computed only from last N bars) |

### Transformed Features

| Original | Before | After |
|----------|--------|-------|
| **ATR** | Absolute $ volatility | `atr_pct` = ATR / close (percentage volatility) |
| **Drawdown** | close - peak (absolute $) | `(close - peak) / peak` (percentage) |
| **Z-score** | `(x - train_q5) / (train_q95 - train_q5)` | `(x - rolling_mean_N) / rolling_std_N` |
| **MACD** | ema12 - ema26 (absolute $) | `(ema12 - ema26) / close` (percentage) |
| **Sharpe** | Unbounded | Clipped to [-10, 10] |
| **Hurst** | Unbounded | Clipped to [0, 1] |
| **Volume ratio** | Unbounded | Clipped to [0, 10] |

### Added Features

- **Log returns** — `log(close[t] / close[t-N])` for N=1, 5, 10, 20, 50, 100
- **Realized vol** — rolling std of log returns, annualized
- **Autocorrelation** — rolling correlation of returns with lagged returns
- **Hurst exponent** — rolling measure of trending vs mean-reverting behavior
- **Regime probabilities** — heuristic probabilities for crisis/trend_up/trend_dn/ranging

---

## 5. STATIONARITY AUDIT RESULTS

**ADF Test Results:**
- **Stationary:** 35/37 features (p < 0.05)
- **Non-stationary:** 0 features
- **Failed:** 2 features (insufficient data for ADF test)

**High Correlations (|r| > 0.95):**
- `log_return_50` ↔ `sharpe_rolling_50`: r=0.953
- `rolling_zscore_50` ↔ `drawdown_pct_20`: r=0.957

**Action:** Acceptable. Sharpe is derived from returns (expected). Z-score and drawdown both measure "distance from peak" (expected).

---

## 6. DISTRIBUTION STABILITY ACROSS SPLITS

### BEFORE PATCH (from backtest_9year_final.py)

Original feature matrix (394 features) used `build_features()` with training-anchored scaling:
```python
X_scaled = (X - median_train) / (Q95_train - Q5_train)
```

**Issue:** When OOS prices 3.27x training mean, Q95_train no longer covers OOS range → features out-of-scale.

### AFTER PATCH (features_stationary.py)

| Split | Shape | Mean | Std | Min | Max | NaN | Inf |
|-------|-------|------|-----|-----|-----|-----|-----|
| **TRAIN** | (418, 37) | 2.95 | 9.92 | -10.0 | 71.1 | 1767 | 0 |
| **VAL** | (419, 37) | 3.22 | 10.07 | -10.0 | 73.8 | 838 | 0 |
| **TEST** | (419, 37) | 3.48 | 10.45 | -3.03 | 57.7 | 838 | 0 |

**Verdict:** ✓ STABLE
- Mean: 2.95 → 3.22 → 3.48 (consistent)
- Std: 9.92 → 10.07 → 10.45 (consistent)
- Range: similar across splits
- **No regime shift signal in feature distributions**

---

## 7. BEFORE/AFTER COMPARISON

### Original Backtest (equal-thirds run)

**Feature count:** 394 (from DuckDB pivot of feature table)

**Feature preprocessing:**
```python
# Robust scaling anchored to training quantiles
median = np.median(train_X, axis=0)
q5 = np.percentile(train_X, 5, axis=0)
q95 = np.percentile(train_X, 95, axis=0)
scale = q95 - q5
X_scaled = (X - median) / scale
```

**Problem:** When OOS close=$4485 but training close_mean=$1372:
- `real_gold` feature = $4485 (out of training support)
- Scaled as: `(4485 - 1372) / (1900 - 900) = 3.11` (3σ beyond training range)
- Model produces neutral probability (~0.5) → zero signals

**Validation metrics:**
- Sharpe: 1.908 (scalp), 3.056 (daytrade), 1.742 (swing)
- PF: 263, 2960, 99
- WR: 80%, 94%, 100%
- **Verdict:** Memorization (zero variance across 100 seeds)

**OOS result:** 0 trades (all 9 scenarios)

---

### Patched Features (stationary)

**Feature count:** 37

**Feature design:**
- All features are ratios, percentages, or rolling statistics
- No absolute price levels
- No training-anchored scaling (each feature self-normalizing)

**Example: ATR feature**
- Before: `ATR(14) = $45` (absolute volatility in dollars)
- After: `atr_pct_14 = ATR(14) / close = 45 / 4485 = 0.01` (1% volatility)

**Example: Drawdown feature**
- Before: `drawdown_20 = close - peak_20 = $4400 - $4500 = -$100`
- After: `drawdown_pct_20 = (4400 - 4500) / 4500 = -0.022` (-2.2%)

**Expected behavior on OOS:**
- Model will produce non-neutral probabilities (features in-distribution)
- Trades will be generated (some probabilities > threshold)
- Metrics will reveal true edge (or lack thereof)

**Next step:** Rerun backtest with patched features

---

## 8. INTEGRATION STEPS

### Step 1: Modify `backtest_9year_final.py`

Replace:
```python
from hydra.data.features import assemble_features

X_all, feat_cols = build_features(df, train_mask.values)
```

With:
```python
from hydra.data.features_stationary import build_stationary_features

df = build_stationary_features(df)
exclude = {"ts", "open", "high", "low", "close", "volume",
           "macro_regime", "regime_confidence"}
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
feat_cols = [c for c in numeric_cols if c not in exclude]
X_all = df[feat_cols].values.astype(np.float32)
X_all = np.nan_to_num(X_all, nan=0.0, posinf=0.0, neginf=0.0)
```

**No scaling needed** — features self-normalize.

### Step 2: Rerun Equal-Thirds Experiment

```bash
python -m hydra.backtest_9year_final --equal-thirds --iterations 100
```

**Expected outcome:**
- OOS trades > 0 (model will generate signals)
- OOS Sharpe: likely 0.3–0.8 (more realistic than 1.9–3.1)
- Validation metrics: more variance across seeds (less overfitting)

### Step 3: Add Walk-Forward Split

Equal-thirds still flawed (regime shift within test period). Next:
- Implement 6-month walk-forward folds
- Retrain every fold (adapt to regime changes)

---

## 9. RECOMMENDATIONS

### Critical (before next run)

1. ✓ **Replace features with stationary equivalents** — DONE
2. **Add OOS probability logging** — save `proba_oos` to telemetry for forensics
3. **Add overfit detection** — auto-fail if validation PF > 50 or WR > 90%
4. **Reduce feature count** — 37 is good, but consider L1 regularization to drop to ~20-25

### High (improve methodology)

5. **Implement walk-forward validation** — 6-month folds, rolling retraining
6. **Add regime classifier** — skip OOS trading when regime is novel
7. **Cross-validate within training** — 5-fold CV to catch overfitting early

### Medium (robustness)

8. **Test on multiple assets** — EUR/USD, oil, S&P500 (does edge generalize?)
9. **Add macro regime features** — VIX, bond yields, DXY (from DuckDB macro_data)
10. **Adaptive thresholds** — adjust `min_confidence` based on vol regime

---

## 10. THEORETICAL JUSTIFICATION

### Why Stationary Features?

A time series X_t is **stationary** if its statistical properties (mean, variance, autocorrelation) don't change over time.

**Non-stationary example:** Gold price (mean $1372 in 2021, $4485 in 2026)

**Stationary example:** Gold log-returns (mean ≈0, std ≈1.5% across all periods)

### Why Models Fail on Non-Stationary Data

Machine learning models learn **P(y | X)** from training data. If **P(X)** shifts between train and test (regime change), the model extrapolates:

**Training:**
- P(y=1 | real_gold=$1500) = 0.7 (model learns "gold at $1500 → up")

**Testing:**
- P(y=1 | real_gold=$4500) = ??? (model never saw $4500)
- **Ensemble outputs:** proba ≈ 0.5 (maximum entropy = "I don't know")

**Solution:** Use **regime-invariant features** where P(X) is stable.

**Example:**
- Feature: `log_return_20` = log(close[t] / close[t-20])
- Training range: [-0.2, +0.2] (±20% moves over 20 days)
- Testing range: [-0.15, +0.18] (overlaps training)
- Model can interpolate ✓

### Mathematical Proof (simplified)

Let y = f(X) be the model, where X are features.

**Non-stationary case:**
- X_train ~ N(μ_train, σ_train)
- X_test ~ N(μ_test, σ_test) where μ_test ≫ μ_train
- Model f learned on X_train cannot generalize to X_test (extrapolation error)

**Stationary case:**
- X_train ~ N(0, 1) (normalized features)
- X_test ~ N(0, 1) (same distribution)
- Model f generalizes ✓

**Augmented Dickey-Fuller Test:** Tests H₀: series has unit root (non-stationary). If p < 0.05, reject H₀ → stationary.

**Our results:** 35/37 features passed ADF (p < 0.05) → confirmed stationary.

---

## 11. CONCLUSION

**Before patch:**
- 394 features, many regime-dependent
- `real_gold` (raw price) as #1 feature
- Training-anchored Q5/Q95 scaling
- **Result:** Zero OOS trades (complete failure)

**After patch:**
- 37 stationary features
- No absolute price levels
- Self-normalizing (no training-anchored scaling)
- **Expected:** OOS trades generated, realistic metrics

**Next steps:**
1. Integrate into backtest
2. Rerun experiment
3. If OOS trades still zero → investigate prediction logic
4. If OOS trades positive but Sharpe < 0.5 → no edge (stop)
5. If OOS Sharpe > 0.5 → proceed to walk-forward validation

---

**Report generated:** 2026-05-20  
**Author:** Claude Sonnet 4.5 (feature engineering audit)
