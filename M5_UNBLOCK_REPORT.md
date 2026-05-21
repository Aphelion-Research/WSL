# M5 Dataset Unblock Report

**Date:** 2026-05-21  
**Status:** M5 DATA ACQUIRED, TRAINING STILL BLOCKED (70/100 features)

---

## Executive Summary

**M5 Data:** ✅ ACQUIRED (100K bars, 1.4 years)  
**M5 Dataset:** ✅ BUILT (100K rows x 3,001 cols)  
**Quality Gates:** ❌ FAIL (70/100 features)  
**Training Status:** BLOCKED (insufficient features)

---

## M5 Data Acquisition

### Method Used
**Command:** `python scripts/fetch_m5_history.py`  
**Source:** domdata CLI (`domdata rates-pos XAUUSD M5`)  
**Broker:** MT5 terminal via Wine

### M5 Data Stats
```
File: data/mt5_history/XAUUSD_M5.parquet
Size: 3.0 MB
Rows: 100,000 bars
Columns: 8 (time, open, high, low, close, tick_volume, spread, real_volume)
Date range: 2024-12-18 to 2026-05-21
Duration: 1.4 years
Validation: PASSED
```

### Why MT5 Script Failed
- `hydra/download_mt5_history.py` tries M5 via Wine subprocess
- MT5 broker returns empty data for M1/M5/M15 timeframes
- Only H4/D1 available via Wine bridge
- **Fix:** Used domdata CLI directly (works)

### M5 Validation Results
```
✓ No missing columns
✓ No duplicate timestamps
✓ OHLC valid (high >= max(open,close), low <= min(open,close))
✓ Prices > 0
✓ Date range sufficient (1.4 years)
```

---

## M5 Dataset Build

### Command
```bash
python scripts/build_full_dataset.py \
  --timeframe M5 \
  --output data/hydra_m5_dataset.parquet \
  --max-rows 100000 \
  --run-gates
```

### Dataset Stats
```
File: data/hydra_m5_dataset.parquet
Size: 31.2 MB
Shape: 100,000 rows x 3,001 columns
Timeframe: M5 (5-minute bars) ✓ CORRECT
Date range: 2024-12-18 to 2026-05-21 (1.4 years)
Non-null features: 74
Null placeholders: 2,927
```

### Feature Breakdown
**Materialized (74 columns):**
- Block A: 5 OHLCV (open, high, low, close, volume)
- Block C: 9 rolling stats (close/high/low, 3 windows, 3 stats each)
- Block D: 19 technical (EMA x7, RSI x4, ATR x4, BB x4)
- Block G: 5 time features (hour, weekday, day, month, quarter)
- Block I: 10 macro (FRED series)
- Block Q: 5 COT positioning
- Block H: 9 regime labels
- Block Z4: 12 forward return labels

**Unavailable (695 columns):**
- Block B: 195 tick microstructure (no tick data)
- Block F: 100 order flow (no LOB data)
- Block K: 150 execution metrics (no execution data)
- Block P: 100 LOB snapshots (no LOB data)
- Block X: 100 cross-asset (not implemented)
- Block Y: 50 sentiment (not implemented)

**Placeholders (2,182 columns):**
- Blocks E, L-W: Statistical features (not implemented)

---

## Quality Gate Results

```
✓ PASS | SHAPE
  Shape OK: 100,000 x 3,001

✗ FAIL | AVAILABLE_FEATURES
  Only 70 trainable features (need >= 100)
  Missing: 30 features

✓ PASS | LEAKAGE
  No future leakage detected

✓ PASS | LABELS
  12 valid label columns
```

**VERDICT:** TRAINING BLOCKED

---

## Blocker Analysis

### Critical Blocker: Insufficient Features (70/100)

**Root cause:** Limited feature implementation

**Missing 30 features can come from:**

1. **More rolling windows (easy, +18 features):**
   - Current: 3 windows (5, 10, 20)
   - Add: 60, 120, 240 bars
   - Each window × 3 stats × 3 signals = 9 features per window
   - Total: +18 features (2 new windows)

2. **More technical indicators (easy, +15 features):**
   - Stochastic (2 lines) × 3 periods = 6
   - CCI × 3 periods = 3
   - Williams %R × 3 periods = 3
   - MACD (3 lines) = 3
   - Total: +15 features

3. **Volatility features (medium, +10 features):**
   - Realized volatility × 3 windows = 3
   - Parkinson volatility × 2 windows = 2
   - Garman-Klass volatility × 2 windows = 2
   - Rolling correlation (close vs volume) × 3 windows = 3
   - Total: +10 features

4. **Statistical features (medium, +10 features):**
   - Skewness × 3 windows = 3
   - Kurtosis × 3 windows = 3
   - Autocorrelation (lag 1,5,10) = 3
   - Hurst exponent = 1
   - Total: +10 features

**Easiest path to 100 features:** Options 1+2 = +33 features → 103 total ✓

---

## Builder Changes Made

### Added M5 Support
- Default timeframe: M5 (was H1)
- Default output: `data/hydra_m5_dataset.parquet` (was `data/hydra_full_dataset.parquet`)
- Added M15 to choices
- Added `--allow-smoke` flag for non-M5 timeframes

### Timeframe Enforcement
```python
if args.timeframe != 'M5' and not args.allow_smoke:
    print("ERROR: Non-M5 timeframe requires --allow-smoke flag")
    sys.exit(1)
```

**H1 smoke testing:**
```bash
python scripts/build_full_dataset.py --timeframe H1 --allow-smoke
```

---

## Files Changed

### Created:
- `scripts/fetch_m5_history.py` — M5 fetch via domdata CLI
- `data/mt5_history/XAUUSD_M5.parquet` — 100K M5 bars
- `data/hydra_m5_dataset.parquet` — M5 training matrix (100K x 3,001)
- `M5_UNBLOCK_REPORT.md` — This report

### Modified:
- `scripts/build_full_dataset.py` — M5 default, --allow-smoke flag, M15 support

### From Previous Audit:
- `dominion/dataset/semantic_names.py` — Semantic naming (not yet applied)
- `dominion/dataset/m5_requirements.py` — M5 checker (not used, domdata worked)
- `dominion/quality/gates.py` — Pandas support (working)
- `DATASET_AUDIT_REPORT.md` — Audit documentation

---

## Next Steps (Exact Order)

### OPTION A: Add 30 Features (Recommended)

Unblocks training with minimal work.

**Step 1: Add more rolling windows (+18 features)**
```python
# In scripts/build_full_dataset.py, line ~244
windows = [5, 10, 20, 60, 120, 240]  # Add 60, 120, 240
```

**Step 2: Add more technical indicators (+15 features)**
```python
# Add to compute_technical_features():
# - Stochastic (fast %K, %D) x3 periods = 6
# - CCI x3 periods = 3
# - Williams %R x3 periods = 3
# - MACD (macd, signal, hist) = 3
```

**Step 3: Rebuild M5 dataset**
```bash
python scripts/build_full_dataset.py --timeframe M5 --run-gates
```

**Step 4: Verify gates pass**
```
Expected:
  ✓ PASS | AVAILABLE_FEATURES: 103 trainable (>= 100)
  VERDICT: TRAINING ALLOWED
```

**Step 5: Run 1 smoke training**
```bash
# Only if gates pass
python scripts/run_multiple_training.py \
  --dataset data/hydra_m5_dataset.parquet \
  --runs 1 \
  --iterations 100
```

### OPTION B: Accept 70 Features with --allow-smoke

Acknowledges insufficient features but trains anyway for research.

**Not recommended** — violates quality gates, defeats audit purpose.

---

## Commands Reference

### Check M5 data:
```bash
python3 -c "
import pandas as pd
df = pd.read_parquet('data/mt5_history/XAUUSD_M5.parquet')
print(f'M5 bars: {len(df)}')
print(f'Date range: {df[\"time\"].min()} to {df[\"time\"].max()}')
print(f'Columns: {df.columns.tolist()}')
"
```

### Check M5 dataset:
```bash
python3 -c "
import pandas as pd
from dominion.quality.gates import run_all_gates, print_gate_report

df = pd.read_parquet('data/hydra_m5_dataset.parquet')
print(f'Dataset: {df.shape}')

training_allowed, results = run_all_gates(df)
print_gate_report(results)
"
```

### Rebuild M5 dataset:
```bash
python scripts/build_full_dataset.py \
  --timeframe M5 \
  --output data/hydra_m5_dataset.parquet \
  --max-rows 100000 \
  --run-gates
```

### Build H1 smoke dataset:
```bash
python scripts/build_full_dataset.py \
  --timeframe H1 \
  --output data/hydra_h1_smoke.parquet \
  --allow-smoke \
  --run-gates
```

---

## Conclusion

**M5 blocker:** RESOLVED ✅  
**Training blocker:** INSUFFICIENT FEATURES (70/100)

**Unblock strategy:** Add 30+ features (rolling windows + technical indicators)

**Estimated effort:** 30 minutes to add features, 5 minutes to rebuild

**After unblock:** Training allowed, no smoke mode required

---

**Report completed:** 2026-05-21  
**M5 data acquired:** ✅  
**M5 dataset built:** ✅  
**Quality gates enforced:** ✅  
**Training cleared:** ❌ (blocked on features)
