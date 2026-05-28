# HYDRA Dataset Infrastructure Audit Report

**Date:** 2026-05-20  
**Status:** TRAINING BLOCKED — Infrastructure repairs in progress

---

## Executive Summary

**VERDICT: Current dataset is SMOKE-TEST ONLY. Training blocked by:**
1. ❌ H1 timeframe (target: M5)
2. ❌ 70 trainable features (minimum: 100)
3. ❌ Sequential naming (not semantic)
4. ❌ M5 data does not exist

**Quality gate result:** FAIL (70/100 features)

---

## Current State

### Dataset: `data/hydra_full_dataset.parquet`
- **Shape:** 50,000 rows x 3,001 columns
- **Timeframe:** H1 (1-hour bars) ← WRONG
- **Date range:** 2018-04-18 to 2026-05-20 (8 years)
- **Non-null features:** 70-74
- **Null placeholders:** 2,927
- **Column naming:** A_0000, B_0000, C_0000 (sequential) ← WRONG

### Quality Gates (NEW — now working)
```
✓ PASS | SHAPE: 50,000 x 3,001
✗ FAIL | AVAILABLE_FEATURES: 70 trainable (need >= 100)
✓ PASS | LEAKAGE: No future leakage detected
✓ PASS | LABELS: 12 valid label columns
```

**Verdict:** TRAINING BLOCKED

### M5 Data Availability
```
❌ data/mt5_history/XAUUSD_M5.parquet: DOES NOT EXIST
✓  data/mt5_history/XAUUSD_H1.parquet: EXISTS (50K bars)
✓  data/mt5_history/XAUUSD_H4.parquet: EXISTS (26K bars)
✓  data/mt5_history/XAUUSD_D1.parquet: EXISTS (7K bars)
⚠️  DuckDB gold_ticks: EXISTS (~2K rows, TOO SMALL)
```

---

## Violations Found

### 1. TIMEFRAME VIOLATION
**Severity:** CRITICAL  
**Status:** BLOCKED

- **Target:** M5 (5-minute bars)
- **Actual:** H1 (1-hour bars)
- **Root cause:** M5 data does not exist
- **Impact:** Wrong granularity for intraday trading, 12x fewer bars

**Blocker message:**
```
M5 DATA MISSING

Required: data/mt5_history/XAUUSD_M5.parquet
Status: FILE NOT FOUND

To generate M5 data:
  1. Check if domdata CLI can fetch M5
  2. If MT5 broker supports M5, fetch history
  3. OR resample from tick data (need more ticks)
  4. OR use H1 for smoke testing only (add --allow-smoke flag)
```

### 2. SEMANTIC NAMING VIOLATION
**Severity:** HIGH  
**Status:** FIXED (infrastructure ready, not applied)

- **Current:** A_0000, A_0001, B_0000, C_0000, Z4_0000
- **Required:** `{scope}__{family}__{signal}__{window}__{unit}`
- **Examples:**
  - `ohlcv__base__close__1__price`
  - `rolling__stats__mean__60__bars`
  - `technical__momentum__rsi__14__index`
  - `reserved__expansion__slot_001__none__null`

**Root cause:**
- Registry (`dominion/dataset/registries.py`) uses sequential numbering
- Block A has partial semantic names (`A_open`) but wrong format
- No semantic name generator implemented until now

**Fix implemented:**
- Created `dominion/dataset/semantic_names.py` with generators
- Not yet applied to dataset build

### 3. QUALITY GATES BYPASSED
**Severity:** HIGH  
**Status:** FIXED

- **Problem:** Gates expected Polars, build used Pandas
- **Impact:** Gates crashed, dataset saved anyway
- **Fix:** Added `_to_polars()` converter, gates now accept both formats

**Test result:**
```
✗ FAIL | AVAILABLE_FEATURES: 70 trainable (need >= 100)
```
Training correctly blocked.

### 4. INSUFFICIENT FEATURES
**Severity:** HIGH  
**Status:** BLOCKED

- **Available:** 70 trainable features
- **Required:** 100 minimum
- **Missing:** 30 features (or 2,930 if counting nulls)
- **Root cause:** Limited feature implementation (OHLCV + rolling + technical + time + macro + COT + regime)

**Unavailable blocks:**
- B: Tick microstructure (195 cols) — no tick data
- F: Order flow (100 cols) — no LOB data
- K: Execution metrics (150 cols) — no execution data
- P: LOB snapshots (100 cols) — no LOB data
- X: Cross-asset (100 cols) — not implemented
- Y: Sentiment (50 cols) — not implemented
- E, L-W: Statistical placeholders (1,750 cols) — not implemented

### 5. RESERVED COLUMN NAMING
**Severity:** MEDIUM  
**Status:** FIXED (infrastructure ready, not applied)

- **Current:** Z1_0000, Z1_0001, Z2_0000
- **Required:** `reserved__expansion__slot_001__none__null`
- **Fix:** Implemented in `semantic_names.py`, not yet applied

### 6. LABEL SMOKE STATUS
**Severity:** MEDIUM  
**Status:** NOT MARKED

- **Current labels:** Z4_0000-Z4_0011 (forward returns 1/5/10/15/30/60 bars)
- **Type:** Simple forward returns (SMOKE LABELS)
- **Problem:** Not distinguished from production labels
- **Required:** Mark as `label__fwd_return__{h}bar__smoke__pct`

### 7. TRAINING SCRIPT BYPASSED GATES
**Severity:** HIGH  
**Status:** NEEDS FIX

- **Problem:** `scripts/run_multiple_training.py` never checked gate verdict
- **Impact:** Trained on blocked dataset, got random results
- **Required:** Check `training_allowed` before training

---

## What Is Valid

✓ **Column count:** Exactly 3,001 (time + 3,000)  
✓ **Registry allocation:** Sums to 3,000 exactly  
✓ **C++ kernels:** Built, functional, 10-100x faster  
✓ **Point-in-time joins:** Asof backward only, no future data  
✓ **No duplicate timestamps**  
✓ **Chronological ordering**  
✓ **Train/val/test split:** Chronological, no shuffle  
✓ **Quality gates:** Now working, correctly block training

---

## What Is Smoke-Test Only

⚠️  **H1 timeframe** (not M5)  
⚠️  **70 features** (below minimum)  
⚠️  **Sequential naming** (not semantic)  
⚠️  **Simple forward return labels** (not triple-barrier)  
⚠️  **50% accuracy** (random baseline)  
⚠️  **No cost-aware metrics**

---

## Files Changed

### Created:
- `dominion/dataset/semantic_names.py` — Semantic naming generators
- `dominion/dataset/m5_requirements.py` — M5 availability checker
- `DATASET_AUDIT_REPORT.md` — This file

### Modified:
- `dominion/quality/gates.py` — Added pandas support, fixed imports

### Needs Modification:
- `scripts/build_full_dataset.py` — Apply semantic naming, check M5, enforce gates
- `scripts/run_multiple_training.py` — Check gate verdict, mark smoke vs production
- `dominion/dataset/registries.py` — Use semantic name generator

---

## Required Fixes

### Priority 1: M5 Data Source
**Blocker:** No M5 data exists

**Options:**
1. **Fetch from MT5 broker** (if supported):
   ```bash
   domdata xaurates  # Check if M5 available
   python scripts/fetch_mt5_m5.py  # To be created
   ```

2. **Resample from ticks** (need more tick data):
   ```bash
   # Current: 2,100 ticks (insufficient)
   # Need: ~500K+ ticks for meaningful M5 resample
   python scripts/resample_ticks_to_m5.py  # To be created
   ```

3. **Use H1 for smoke testing** (temporary):
   ```bash
   python scripts/build_full_dataset.py --timeframe H1 --allow-smoke
   ```

### Priority 2: Semantic Naming
**Status:** Infrastructure ready

**Apply:**
1. Modify `dominion/dataset/registries.py` to use `semantic_names.py` generators
2. Rebuild dataset with semantic names
3. Update all column references in training scripts

### Priority 3: More Features
**Blockerif M5 exists:** Need 30+ more features

**Options:**
1. Implement placeholder blocks E, L-W (statistical features)
2. Add more rolling windows (currently only 3)
3. Add more technical indicators
4. Implement regime-conditional features

### Priority 4: Training Guardrails
**Status:** Urgent

**Fix `scripts/run_multiple_training.py`:**
```python
# Check gate verdict
training_allowed, results = run_all_gates(df)
if not training_allowed and not args.allow_smoke:
    print("TRAINING BLOCKED BY QUALITY GATES")
    print_gate_report(results)
    sys.exit(1)

# Mark smoke vs production
if args.allow_smoke or not all_gates_passed:
    print("⚠️  SMOKE TEST MODE")
else:
    print("✓ PRODUCTION VALIDATED MODE")
```

---

## Next Steps (Exact Order)

### DO NOT TRAIN MORE MODELS YET

### Step 1: Decide on M5 source strategy
- [ ] Check if domdata can fetch M5
- [ ] OR accept H1 smoke mode with `--allow-smoke`
- [ ] OR wait for more tick data

### Step 2: Fix semantic naming
- [ ] Update `registries.py` to use `semantic_names.py`
- [ ] Test registry validation
- [ ] Rebuild smoke dataset with semantic names

### Step 3: Fix training script
- [ ] Add `--allow-smoke` flag
- [ ] Check gate verdict before training
- [ ] Print SMOKE_TEST or PRODUCTION_VALIDATED

### Step 4: Run smoke validation
- [ ] Build H1 dataset with semantic names + --allow-smoke
- [ ] Run quality gates (expect BLOCKED due to features)
- [ ] Run 1 smoke training run with --allow-smoke
- [ ] Verify 50% baseline (confirms no phantom edge)

### Step 5: Generate M5 data (if possible)
- [ ] Implement fetch_mt5_m5.py or resample_ticks_to_m5.py
- [ ] Build M5 dataset
- [ ] Run quality gates
- [ ] If still blocked on features, implement more blocks

### Step 6: Expand features (if M5 + gates pass)
- [ ] Implement block E (volatility)
- [ ] Implement block L (statistical properties)
- [ ] Add more rolling windows
- [ ] Reach 100+ trainable features
- [ ] Re-run gates

### Step 7: Production training (only if gates pass)
- [ ] No --allow-smoke flag
- [ ] Gates must pass
- [ ] Cost-aware metrics
- [ ] Walk-forward validation

---

## Commands to Run

### Check current status:
```bash
python3 -c "
from dominion.quality.gates import run_all_gates, print_gate_report
from dominion.dataset.m5_requirements import require_m5_or_block
import pandas as df

# Gates
df = pd.read_parquet('data/hydra_full_dataset.parquet')
training_allowed, results = run_all_gates(df)
print_gate_report(results)

# M5 status
status = require_m5_or_block()
print(status.blocker_message if status.blocker_message else 'M5 AVAILABLE')
"
```

### Validate registry:
```bash
python3 -c "
from dominion.dataset.registries import HydraRegistry
r = HydraRegistry()
print(r.summary())
"
```

---

## Conclusion

**Current dataset status:** SMOKE-TEST ONLY

**Training verdict:** BLOCKED (70/100 features)

**Critical blocker:** M5 data does not exist

**Infrastructure status:** Quality gates working, semantic naming ready, M5 checker ready

**Next action:** Decide M5 source strategy OR accept H1 smoke mode with `--allow-smoke`

**DO NOT:** Train more models until gates pass OR smoke mode explicitly acknowledged

---

**Audit completed:** 2026-05-20 18:48 UTC  
**Auditor:** Claude (HYDRA Dataset Infrastructure Engineer)
