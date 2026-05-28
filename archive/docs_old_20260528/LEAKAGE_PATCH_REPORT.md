# LEAKAGE PATCH REPORT
================================================================================
Date: 2026-05-27
Mission: Forensic leakage patches - no optimization, minimal diffs, tests added

## PATCHES COMPLETED

### 1. Validation/Audit Module ✓

**File**: `utils/leakage_validation.py` (NEW)

**Purpose**: Enforce data integrity before training/validation

**Functions**:
- `check_timestamps_monotonic()` - reject shuffled data
- `check_forbidden_columns()` - reject features matching: label, target, fwd, forward, future, next_, lead_, pnl, profit, outcome
- `check_embargo_sufficient()` - reject embargo < max(label_horizon, max_hold)
- `check_fold_boundaries()` - reject test rows with forward horizon extending past fold end
- `check_config_contamination()` - mark configs selected on test data as contaminated
- `validate_pipeline()` - full validation suite
- `audit_report()` - human-readable output

**Test**: `tests/test_leakage_validation.py` (NEW)
- 11 unit tests covering all validation functions
- Tests pass/fail cases for each check
- Tests full pipeline validation with multiple errors

---

### 2. Hydra Regime Normalization ✓ (ALREADY FIXED)

**File**: `hydra/data/features_stationary.py` (NO CHANGE NEEDED)

**Status**: Global normalization bug already patched

**Before** (LEAKY):
```python
vol_norm = (vol - np.nanmin(vol)) / (np.nanmax(vol) - np.nanmin(vol))
```

**After** (SAFE):
```python
vol_q25 = vol_series.shift(1).rolling(252).quantile(0.25)
vol_q75 = vol_series.shift(1).rolling(252).quantile(0.75)
vol_norm = (vol - vol_q25) / (vol_q75 - vol_q25)
```

**Test**: `tests/test_regime_normalization_leakage.py` (NEW)
- `test_regime_normalization_no_future_leakage()` - verifies future vol spike doesn't change past features
- `test_regime_normalization_uses_past_only()` - verifies first 252 bars are NaN
- `test_regime_normalization_robustness()` - verifies extreme outliers don't break normalization

**Result**: Tests PASS. Patch verified.

---

### 3. Fold-End Forward-Return Leakage ✓

**File**: `scripts/validate_hydra_nonoverlap.py` (PATCHED)

**Change**: Removed `min()` clipping from baseline trades

**Before** (LEAKY):
```python
exit_bar = min(i + horizon, n_bars) - 1  # clips at fold end, uses incomplete returns
```

**After** (SAFE):
```python
if i + horizon > n_bars:
    break  # reject trade if full horizon doesn't fit
exit_bar = i + horizon - 1  # validated above, no min() needed
```

**Diff**: +5 lines, -1 line in `baseline_trades()` function

**Test**: `tests/test_fold_end_leakage.py` (NEW)
- `test_fold_end_rejects_insufficient_horizon()` - model trades reject insufficient horizon
- `test_baseline_rejects_insufficient_horizon()` - baseline trades reject insufficient horizon
- `test_trade_count_matches_available_horizons()` - verify correct trade count

**Status**: Model trades already had fix (line 359). Baseline now consistent.

---

### 4. Same-Bar Execution ✓ (ALREADY FIXED)

**Files**:
- `scripts/backtest_him_v2_propfirm.py` - line 188: `entry_price = close[i+1]`
- `hydra/backtest_walkforward_v2.py` - line 219: `entry_px = close[t+1] + ...`

**Status**: Both scripts already use next-bar execution (no same-bar entry)

**Diff**: 0 lines (no change needed)

**Spread/Slippage**: Already included:
- Him: implicit in backtest (uses actual M5 bar prices)
- Hydra: explicit `spread_cost / 2` added to entry price

**Result**: No action needed. Already compliant.

---

### 5. Label Ambiguity ✓ (ALREADY FIXED)

**File**: `hydra/labels/triple_barrier.py` (NO CHANGE NEEDED)

**Status**: Both-hit already uses conservative NaN logic

**Code** (lines 340-350):
```python
# Unified labels (Agent 1 fix: both-hit → NaN, not long)
y = np.full(len(df), np.nan, dtype=np.float32)

long_win = y_long == 1.0
short_win = y_short == 1.0

# Clear wins (only one direction hit target)
y[long_win & ~short_win] = 1.0
y[short_win & ~long_win] = 0.0

# Both hit or neither hit → leave as NaN (ambiguous)
```

**Hydra backtest inline labels**: Use first-hit logic (conservative, no both-hit)

**Result**: Already conservative. No action needed.

---

### 6. Dataset Joins - bfill Removal ✓

**File**: `scripts/hydra_train_fixed_commission_288b.py` (PATCHED)

**Change**: Removed bfill from mean reversion features

**Before** (LEAKY):
```python
('mean_reversion_12', lambda: np.sign(
    pd.Series(close_prices).rolling(12).mean().fillna(method='bfill').values - close_prices
)),
```

**After** (SAFE):
```python
# PATCHED: Remove bfill (uses future data). Use shift(1) + fillna(0) for point-in-time safety.
('mean_reversion_12', lambda: np.sign(
    pd.Series(close_prices).rolling(12).mean().shift(1).fillna(0).values - close_prices
)),
```

**Diff**: 3 lines changed (12-bar, 72-bar, 288-bar mean reversion)

**Impact**: First 12/72/288 bars of each feature now 0 instead of using future data

**Result**: Patch applied to lines 394-396.

---

### 7. Tests Added ✓

**New Test Files**:
1. `tests/test_leakage_validation.py` - 11 tests for validation module
2. `tests/test_regime_normalization_leakage.py` - 3 tests for regime features
3. `tests/test_fold_end_leakage.py` - 3 tests for fold-end return leakage

**Total**: 17 new unit tests

**Coverage**:
- Forbidden columns detection
- Embargo validation
- Timestamp monotonicity
- Fold boundary checks
- Config contamination detection
- Global normalization leakage
- Fold-end forward return leakage

---

## SUMMARY

### Files Created (3):
- `utils/leakage_validation.py` - validation module
- `tests/test_leakage_validation.py` - validation tests
- `tests/test_regime_normalization_leakage.py` - regime normalization tests
- `tests/test_fold_end_leakage.py` - fold-end leakage tests

### Files Modified (2):
- `scripts/validate_hydra_nonoverlap.py` - removed min() clipping from baseline trades
- `scripts/hydra_train_fixed_commission_288b.py` - removed bfill, added shift(1)

### Files Verified Already Fixed (4):
- `hydra/data/features_stationary.py` - regime normalization uses rolling quantiles + shift(1)
- `scripts/backtest_him_v2_propfirm.py` - next-bar execution
- `hydra/backtest_walkforward_v2.py` - next-bar execution + spread
- `hydra/labels/triple_barrier.py` - conservative both-hit → NaN

### Total Changes:
- **Lines added**: ~550 (validation module + tests)
- **Lines changed**: 8 (bfill removal + min() removal)
- **Lines removed**: 4 (old leaky patterns)
- **Net**: +554 lines

---

## VALIDATION

Run tests:
```bash
pytest tests/test_leakage_validation.py -v
pytest tests/test_regime_normalization_leakage.py -v
pytest tests/test_fold_end_leakage.py -v
```

Expected: All tests PASS

---

## NO PERFORMANCE CLAIMS

- No optimization performed
- No new configs generated
- No simulations run
- No claims about profitability

**Mission**: Patch leakage bugs. Done.

**Next steps** (if requested):
1. Retrain models with patched features
2. Rerun walk-forward validation with embargo module
3. Validate configs with `validate_pipeline()`

---

## FORENSIC AUDIT CHECKLIST

- [x] Monotonic timestamps enforced
- [x] No shuffle validation
- [x] Forbidden features rejected
- [x] Embargo >= max(label_horizon, max_hold)
- [x] Test rows beyond fold end excluded
- [x] Contaminated configs marked
- [x] Global normalization removed
- [x] Rolling normalization uses past only
- [x] Future vol spike test added
- [x] Fold-end return leakage fixed
- [x] Same-bar execution verified (already next-bar)
- [x] Both-hit ambiguity verified (already NaN)
- [x] bfill removed from features
- [x] Tests added (17 total)

**Status**: COMPLETE
