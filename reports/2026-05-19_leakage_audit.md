# Data Leakage Audit Report

**Date:** 2026-05-19  
**Auditor:** Claude Code (Sonnet 4.5)  
**Scope:** Dominion data pipeline feature engineering (data_pipeline/)  
**Status:** **CRITICAL LEAKAGE FOUND**

---

## Executive Summary

**Result:** Data pipeline contains **1 critical leakage** + **3 minor concerns**.

**Critical finding:** HMM regime detection (regime.py) fits model on full dataset and predicts all rows simultaneously, leaking future information into past regime labels.

**Impact:** Any model trained on current features will have inflated performance metrics. Regime-conditioned returns use contaminated labels.

**Required action:** Implement expanding-window HMM fit or remove HMM regime features until fixed.

---

## Leakage Findings

### 1. CRITICAL: HMM Regime Detection Look-Ahead Bias

**File:** `data_pipeline/features/regime.py:52-61`

**Issue:**
```python
# LEAKAGE: Fits HMM on full dataset
model = hmmlearn_hmm.GaussianHMM(n_components=n_states, covariance_type="full", n_iter=100)
model.fit(X_valid)  # <-- Fits on ALL data (past + future)

# Then predicts all rows
states[valid_mask] = model.predict(X_valid)  # <-- Uses future info to label past
probs[valid_mask] = model.predict_proba(X_valid)
```

**Why this is leakage:**
- HMM `.fit()` uses **all available data** (including future) to learn transition probabilities
- When predicting state for time `t`, model already "knows" what happens at `t+1, t+2, ..., T`
- Regime labels at time `t` contain information from the future

**Example contamination:**
- At 2026-01-15, regime labeled "trending_up"
- Model "knew" during fit that price rises sharply on 2026-01-20
- If we use 2026-01-15 regime label to predict 2026-01-16 return, we're using future info

**Correct approach:**
- **Expanding window:** Fit HMM on `[0:t]`, predict only row `t`, slide forward
- **Or:** Remove HMM features entirely until fixed
- **Or:** Use forward-only Viterbi smoothing (expensive, still has small look-ahead)

**Affected features:**
- `regime_tactical` (categorical)
- `regime_prob_trend_up`
- `regime_prob_trend_down`
- `regime_prob_ranging`
- `regime_prob_crisis`

**Downstream contamination:**
- Any model using these features
- `compute_historical_return_by_regime()` (regime.py:145) — uses contaminated labels

---

### 2. MINOR: Forward Fill on External Data

**Files:**
- `data_pipeline/features/store.py:50` — `cot_aligned = cot_indexed.reindex(gold_df.index).ffill()`
- `data_pipeline/features/crossasset.py:167` — `merged = merged.ffill().bfill()`
- `data_pipeline/features/macro.py:161` — `merged = merged.ffill()`

**Issue:**
Forward fill (`ffill()`) carries last known value forward when data is missing.

**Analysis:**
- **OK for features:** COT data is weekly, gold is daily. Assuming "COT sentiment unchanged until next report" is reasonable.
- **NOT OK if used for labels:** Never forward-fill target returns.

**Current usage:** Only for **features** (COT sentiment, macro indicators). No labels forward-filled.

**Verdict:** **PASS** — Forward fill is acceptable for external features with known publication lag.

---

### 3. MINOR: Future FOMC Date Lookup

**File:** `data_pipeline/features/macro.py:139-141`

**Code:**
```python
future_dates = [d for d in fomc_dates if d > ts]
if future_dates:
    days_to_fomc.append((future_dates[0] - ts).days)
```

**Issue:**
Looks ahead to find next FOMC date.

**Analysis:**
- **Intent:** "Days until next Fed meeting" is a legitimate feature (Fed schedule is public knowledge)
- **Is this leakage?** NO — Fed meeting dates are announced months in advance. Traders know them.
- **Analogy:** "Days until Christmas" is not leakage even though we know December 25 is in the future.

**Verdict:** **PASS** — Public calendar events are not leakage.

---

### 4. MINOR: Kalman Filter Predict Step

**File:** `data_pipeline/fusion/kalman.py:156`

**Code:**
```python
pred_price, pred_unc = filt.predict()
```

**Issue:**
Kalman filter has a `predict()` step that forecasts next state.

**Analysis:**
- **Kalman workflow:** `predict(t+1 | t)` → `update(t+1 | observation)` → repeat
- **Is this leakage?** NO — Kalman predict uses only **past** state, not future observations
- **Implementation check:**
  ```python
  def predict(self):
      self.x = self.F @ self.x  # Uses current state (from past)
      self.P = self.F @ self.P @ self.F.T + self.Q
      return self.x[0], self.P[0, 0]
  ```
  ✓ Only uses `self.x` (previous state), no future data

**Verdict:** **PASS** — Kalman predict is a standard forecasting step, not leakage.

---

## Rolling Window Analysis

### Implementation
All rolling windows in `price.py`, `microstructure.py`, `cot_features.py` use standard pandas `.rolling(w)` API.

**Default behavior:**
```python
price.rolling(w).mean()
```
- Pandas default: `min_periods=w` (requires full window)
- First `w-1` rows → NaN (correct, no partial windows)
- Row `w` onwards → uses only `[i-w+1:i]` (past data only)

**Verdict:** **PASS** — No look-ahead in rolling windows.

---

## Feature Engineering Correctness

### What's Safe (✓)

| Operation | File | Why It's Safe |
|---|---|---|
| `pct_change(w)` | price.py | Uses `price[t] / price[t-w] - 1` |
| `rolling(w).mean()` | price.py | Uses `[t-w+1:t]` window |
| `shift(lag)` | microstructure.py | Explicit lag (e.g., `returns.shift(1)`) |
| `diff(w)` | cot_features.py | `value[t] - value[t-w]` |
| `ffill()` on COT | store.py | COT is weekly, gold is daily. Assumption: sentiment persists. |
| FOMC date lookup | macro.py | Public calendar events |
| Kalman predict | kalman.py | Uses past state only |

### What's Broken (✗)

| Operation | File | Why It's Leakage | Fix |
|---|---|---|---|
| `HMM.fit(X_all)` | regime.py:53 | Learns from future | Expanding window fit |
| `HMM.predict(X_all)` | regime.py:57 | Uses future-trained model | Predict row-by-row |

---

## Recommendations

### Immediate (Before Training)

1. **Remove HMM regime features** from feature set:
   ```python
   # Drop these columns
   drop_cols = [
       "regime_tactical",
       "regime_prob_trend_up",
       "regime_prob_trend_down",
       "regime_prob_ranging",
       "regime_prob_crisis",
   ]
   ```

2. **Add expanding-window HMM** (if regime features needed):
   ```python
   def detect_tactical_regime_hmm_expanding(df: pd.DataFrame) -> pd.DataFrame:
       states = []
       for i in range(len(df)):
           if i < 100:
               states.append("unknown")
               continue
           
           # Fit on [0:i] only
           X_train = prepare_features(df.iloc[:i])
           model = GaussianHMM(n_components=4)
           model.fit(X_train)
           
           # Predict only row i
           X_test = prepare_features(df.iloc[i:i+1])
           state = model.predict(X_test)[0]
           states.append(map_state_to_regime(state))
       
       return pd.Series(states, index=df.index)
   ```

3. **Verify no regime features used** in current models:
   ```bash
   grep -r "regime_tactical\|regime_prob" dominion_ai/ exec_features/ lob/ tca/ toxicity/
   ```

### Short-Term (Dataset v1)

4. **Document safe features** in dataset manifest:
   - List all features
   - Mark HMM features as "EXCLUDED (leakage)"
   - Document why each feature is safe

5. **Add leakage tests** to test suite:
   ```python
   def test_no_future_data_in_features():
       """Verify features use only past data."""
       df = load_test_data()
       features = compute_all_features(df)
       
       # Check: feature[t] should not change if we add row t+1
       features_t = compute_all_features(df[:100])
       features_t_plus = compute_all_features(df[:101])
       
       assert features_t.equals(features_t_plus[:100])
   ```

### Long-Term (Production)

6. **Streaming feature computation**:
   - Refactor all feature functions to accept `df[:t]` and compute only row `t`
   - Enforce via API: `compute_features(df_history, current_timestamp)`

7. **Online HMM**:
   - Use online Bayesian HMM (e.g., `pyhsmm` library)
   - Or: ensemble of expanding-window HMMs (expensive)

---

## Testing Checklist

Before claiming "no leakage":

- [ ] Remove HMM features from dataset
- [ ] Run `grep -r "regime_tactical" data_pipeline/` → verify not used
- [ ] Train baseline model on cleaned features
- [ ] Check IC stays reasonable (not 0.3+)
- [ ] Split by regime using **micro regime** (time-of-day, no leakage) instead of HMM
- [ ] Document all excluded features in dataset manifest

---

## Feature Count

**Total features:** ~400+ (per AGENT_HANDOFF.md)

**Leakage-contaminated:** 5 (regime_tactical + 4 probs)

**Safe to use:** ~395

**Impact:** Low feature count loss, but **regime conditioning is broken** until fixed.

---

## Conclusion

**Verdict:** Pipeline has **1 critical leakage** (HMM regime detection).

**Severity:** HIGH — Affects regime-conditioned performance analysis, inflates metrics if used in models.

**Action:** Remove HMM features. Use micro regime (time-of-day) or expanding-window HMM.

**Next task:** Implement temporal split (Task #10).

---

**Audit complete.** See `data_pipeline/features/regime.py` for fix location.
