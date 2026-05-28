# Research Core Implementation Summary

**Status:** ✅ Complete  
**Date:** 2026-05-27  
**Version:** 0.1.0

---

## What Was Built

Created clean `research_core/` foundation inside existing Dominion repo for honest model validation.

### Structure

```
research_core/
├── __init__.py
├── README.md
├── IMPLEMENTATION_SUMMARY.md
├── data_contracts/
│   ├── __init__.py
│   ├── columns.py           # Forbidden feature patterns
│   └── validation.py         # Timestamp, OHLCV, feature validation
├── execution/
│   ├── __init__.py
│   ├── costs.py              # Cost models (spread, slippage, commission)
│   └── simulator.py          # Conservative trade simulator
├── diagnostics/
│   ├── __init__.py
│   ├── null_tests.py         # Random, shuffled, shifted, reversed
│   ├── cost_sensitivity.py   # 0x, 0.5x, 1x, 2x, 3x cost tests
│   ├── stability.py          # Monthly PF, quarterly Sharpe, concentration
│   └── model_forensics.py    # End-to-end validation workflow
├── hypotheses/
│   └── __init__.py           # Future: research hypothesis registry
├── reports/
│   └── __init__.py           # Future: PDF/HTML report generation
└── examples/
    └── validate_locked_model.py  # Demo script
```

### Tests Added

```
tests/
├── test_research_core_contracts.py    # 8 tests
├── test_research_core_execution.py    # 6 tests
└── test_research_core_diagnostics.py  # 4 tests
```

**Total:** 18 tests, all passing.

---

## Key Features

### 1. Data Contract Guards

**Purpose:** Prevent leakage, enforce point-in-time safety.

**Checks:**
- Monotonic timestamps (no out-of-order data)
- No duplicate timestamps
- Forbidden feature columns (`fwd`, `future`, `next_`, `label`, `target`, `pnl`, etc.)
- Required OHLCV columns (`open`, `high`, `low`, `close`, `spread`)
- Optional: detect potential `bfill` usage (experimental)

**Usage:**
```python
from research_core.data_contracts import validate_features, validate_ohlcv

validate_ohlcv(ohlcv)  # Raises ValidationError if violations
validate_features(features, allow_label=False)
```

**Test Coverage:**
- ✅ Forbidden columns rejected
- ✅ Non-monotonic timestamps rejected
- ✅ Duplicate timestamps rejected
- ✅ Missing OHLCV columns rejected

---

### 2. Execution Simulator

**Purpose:** Conservative trade simulation, no same-bar entry by default.

**Rules:**
- Signal at bar `i` → entry no earlier than bar `i+1`
- Entry price = `open[i+1] + spread/2` (pays full spread)
- Path-dependent stop/TP checks via `low`/`high` breach
- **Conservative ambiguity:** If both stop and TP possible in same bar, assume stop hit first
- Fixed risk per trade (no compounding by default)
- Cost model: spread + slippage + commission

**Cost Model:**
```python
from research_core.execution import CostModel

# Baseline XAU/USD costs
cost_model = CostModel.xauusd_baseline()
# spread_points=0.30, slippage_points=0.10, commission_per_lot=7.0

# Scale costs
cost_model_2x = cost_model.scale(2.0)  # Double costs
```

**Usage:**
```python
from research_core.execution import simulate_trades, SimulationConfig

config = SimulationConfig(
    signal_at_bar_i_entry_at_bar_i_plus_n=1,  # Next-bar entry
    hold_bars=16,  # Fixed hold period
    stop_loss_atr_mult=10.0,  # Catastrophic stop
    cost_model=CostModel.xauusd_baseline(),
)

result = simulate_trades(signals, ohlcv, config, atr=atr)
```

**Test Coverage:**
- ✅ Next-bar entry enforced
- ✅ Same-bar entry disabled by default (raises error)
- ✅ Conservative stop loss (assumes worst case)
- ✅ Cost sensitivity: higher costs worsen or maintain PnL (never improve)
- ✅ Hold bars exit at correct bar count
- ✅ Path-dependent stop/TP ambiguity (stop first)

---

### 3. Diagnostics

**Purpose:** Forensic validation without optimization.

#### Cost Sensitivity

Tests at `0x`, `0.5x`, `1x`, `2x`, `3x` baseline costs.

**Pass Criteria:**
- Robust to 2x costs (still profitable)

**Usage:**
```python
from research_core.diagnostics import run_cost_sensitivity

result = run_cost_sensitivity(signals, ohlcv, config, atr)
print(result["summary"]["robust_to_2x_costs"])
```

#### Null Tests

Tests against:
- Random signals (same frequency, random timing)
- Shuffled signals
- Shifted signals (+1, +5, +20 bars)
- Reversed signals (long ↔ short)

**Pass Criteria:**
- Original Sharpe > all null Sharpe

**Usage:**
```python
from research_core.diagnostics import run_null_tests

result = run_null_tests(signals, ohlcv, config, atr)
print(result["summary"]["verdict"])  # PASS or FAIL
```

#### Stability Metrics

Computes:
- Monthly profit factor (per month)
- Quarterly Sharpe (per quarter)
- Yearly return (per year)
- Top 5 trades concentration (% of total PnL)
- Longest win/loss streaks

**Pass Criteria:**
- Top 5 trades < 50% of PnL
- < 30% of months with PF < 1.0

**Usage:**
```python
from research_core.diagnostics import compute_stability_metrics

result = compute_stability_metrics(trades, equity_curve)
print(result["verdict"])  # STABLE or UNSTABLE: ...
```

#### Model Forensics (End-to-End)

Runs all diagnostics in one call, outputs JSON report + terminal summary.

**Usage:**
```python
from research_core.diagnostics import run_model_forensics

report = run_model_forensics(
    predictions=model_predictions,
    ohlcv=ohlcv,
    config=config,
    threshold=0.55,
    atr=atr,
    output_path=Path("output/forensic_report.json"),
)

print(report["verdict"])
# VALIDATED | WEAK: ... | REJECTED: ... | CONTAMINATED: ...
```

**Verdicts:**
- **VALIDATED:** Passed all tests (null, cost, stability)
- **WEAK:** Passed null but warnings (cost fragility, instability)
- **REJECTED:** Failed null tests
- **CONTAMINATED:** Data validation failed (forbidden columns, timestamps)

**Test Coverage:**
- ✅ Null tests supported (random, shuffled)
- ✅ Cost sensitivity degrades with higher costs
- ✅ Stability metrics compute top trades concentration
- ✅ Contaminated metadata blocks VALIDATED verdict

---

## How to Run Tests

```bash
# Install dependencies (if not already)
pip install pytest pandas numpy xgboost

# Run all research_core tests
pytest tests/test_research_core_*.py -v

# Run specific test file
pytest tests/test_research_core_contracts.py -v
pytest tests/test_research_core_execution.py -v
pytest tests/test_research_core_diagnostics.py -v
```

**Test Results:**
```
18 passed, 10 warnings in 0.52s
```

All tests pass. Warnings are pandas deprecation warnings (freq='H' → 'h'), not functional issues.

---

## Demo Script

```bash
python research_core/examples/validate_locked_model.py
```

**Output:**
```
Running model forensics...
This will:
  1. Validate data contracts
  2. Run baseline simulation
  3. Test cost sensitivity (0x, 0.5x, 1x, 2x, 3x)
  4. Run null tests (random, shuffled, shifted, reversed)
  5. Compute stability metrics
  6. Generate verdict

✓ Forensic report saved to output_him_v2/forensic_demo_report.json

============================================================
MODEL FORENSICS REPORT
============================================================
Verdict: REJECTED: FAIL_NULL_TESTS

Baseline Performance:
  Trades: 51
  Sharpe: -0.46
  Total PnL: $-472.23
  Win Rate: 27.45%

Cost Sensitivity:
  Robust to 2x costs: False
  Robust to 3x costs: False

Null Tests:
  Better than null: 4/6
  Verdict: FAIL

Stability:
  Top 5 trades: 0.0% of PnL
  Verdict: STABLE
============================================================
```

Demo correctly rejects synthetic random model (no edge).

---

## Integration with Legacy Scripts

### Legacy Scripts (Reference Only)

These scripts remain for historical reference but should **NOT** be used for new research:

- `scripts/diagnostic_multiscale.py` — Use `research_core.diagnostics` instead
- `scripts/walk_forward_*.py` — Use `research_core.execution` for backtests
- `scripts/retrain_him_*.py` — **Do NOT use** (contains optimization/training)

### Migration Path

1. **Phase 1 (now):** Use `research_core` for new validation workflows
2. **Phase 2:** Refactor working legacy scripts to call `research_core` modules
3. **Phase 3:** Archive/deprecate duplicate validation logic

**Example Migration:**

Before:
```python
# Legacy: scripts/diagnostic_multiscale.py (500+ lines)
# Scattered validation logic, inconsistent cost handling
```

After:
```python
from research_core.diagnostics import run_model_forensics

report = run_model_forensics(predictions, ohlcv, config, threshold, atr)
```

---

## Changed Files

### New Files (All Under `research_core/`)

```
research_core/
├── __init__.py                       # Module root
├── README.md                         # User documentation
├── IMPLEMENTATION_SUMMARY.md         # This file
├── data_contracts/
│   ├── __init__.py
│   ├── columns.py
│   └── validation.py
├── execution/
│   ├── __init__.py
│   ├── costs.py
│   └── simulator.py
├── diagnostics/
│   ├── __init__.py
│   ├── null_tests.py
│   ├── cost_sensitivity.py
│   ├── stability.py
│   └── model_forensics.py
├── hypotheses/
│   └── __init__.py
├── reports/
│   └── __init__.py
└── examples/
    └── validate_locked_model.py

tests/
├── test_research_core_contracts.py    # NEW: 8 tests
├── test_research_core_execution.py    # NEW: 6 tests
└── test_research_core_diagnostics.py  # NEW: 4 tests
```

**Total:** 17 new files, 18 new tests.

### No Legacy Files Modified

No existing scripts were modified. `research_core/` is a clean addition.

---

## Design Principles

1. **Read-only validation:** No model training, no optimization, no threshold tuning
2. **Pessimistic execution:** Conservative assumptions prevent overstating edge
3. **Fail-fast contracts:** Reject contaminated data before simulation
4. **Transparent verdicts:** Clear pass/fail criteria, no ambiguity
5. **No claims:** Report results, do not claim profitability

---

## Future Enhancements

- [ ] Regime breakdown (session, volatility, trend)
- [ ] Hypothesis registry (track research decisions via RAGD)
- [ ] PDF/HTML report generation
- [ ] Walk-forward validation framework
- [ ] Multi-asset support (FX, crypto, equities)
- [ ] Integration with domdata CLI
- [ ] Feature importance forensics (SHAP integration)

---

## How Research Core Replaces Legacy Validation

### Before (Legacy)

```
scripts/diagnostic_multiscale.py       # 500+ lines
scripts/walk_forward_*.py              # 600+ lines each
scripts/retrain_him_*.py               # 800+ lines (training + validation)
```

**Problems:**
- Validation scattered across multiple scripts
- Inconsistent cost handling
- Duplicate null test logic
- No standardized verdicts
- Easy to bypass safety checks

### After (Research Core)

```python
from research_core.diagnostics import run_model_forensics

report = run_model_forensics(
    predictions=predictions,
    ohlcv=ohlcv,
    config=config,
    threshold=0.55,
    atr=atr,
    output_path=Path("output/report.json"),
)
```

**Benefits:**
- Single entry point for validation
- Standardized cost models
- Consistent null test logic
- Clear pass/fail verdicts
- Data contract enforcement at validation time

---

## Example Workflow: Validate Him V2 MultiScale

```python
import pandas as pd
import xgboost as xgb
from pathlib import Path
from research_core.execution import SimulationConfig, CostModel
from research_core.diagnostics import run_model_forensics

# 1. Load data
ohlcv = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")

# 2. Load locked model (no retraining)
model = xgb.Booster()
model.load_model("models/Him/Him_V2_MultiScale.json")

# 3. Build features (existing function)
features = build_multiscale_features(ohlcv)

# 4. Get predictions
import xgboost as xgb
dmat = xgb.DMatrix(features.dropna())
predictions = pd.Series(model.predict(dmat), index=features.dropna().index)

# 5. Compute ATR
tr = pd.concat([
    ohlcv["high"] - ohlcv["low"],
    (ohlcv["high"] - ohlcv["close"].shift(1)).abs(),
    (ohlcv["low"] - ohlcv["close"].shift(1)).abs(),
], axis=1).max(axis=1)
atr = tr.rolling(14).mean()

# 6. Configure simulation
config = SimulationConfig(
    signal_at_bar_i_entry_at_bar_i_plus_n=1,
    hold_bars=16,
    stop_loss_atr_mult=10.0,
    cost_model=CostModel.xauusd_baseline(),
)

# 7. Run forensics
report = run_model_forensics(
    predictions=predictions,
    ohlcv=ohlcv,
    config=config,
    threshold=0.55,  # Locked from walk-forward
    atr=atr,
    features=features,  # Validate features for forbidden columns
    output_path=Path("output_him_v2/him_v2_forensic_report.json"),
)

# 8. Check verdict
if report["verdict"].startswith("VALIDATED"):
    print("✅ Model passed all validation tests")
elif report["verdict"].startswith("WEAK"):
    print("⚠️ Model passed null tests but has warnings")
elif report["verdict"].startswith("REJECTED"):
    print("❌ Model failed null tests")
else:
    print("🚫 Data validation failed (contaminated)")
```

---

## Key Takeaways

1. **Foundation complete:** `research_core/` provides honest validation without optimization
2. **All tests pass:** 18 tests validate core functionality
3. **Demo works:** `validate_locked_model.py` correctly rejects random model
4. **No legacy modification:** Clean addition to repo, no disruption
5. **Migration path clear:** Replace scattered validation logic with `research_core` over time

---

**Status:** ✅ Ready for use  
**Next Steps:**
1. Validate existing Him/Him V2 models with `run_model_forensics()`
2. Document results in `output_him_v2/`
3. Decide: continue Him line or pivot based on forensic results
4. Future: extend with regime breakdown, hypothesis registry, walk-forward framework

---

**Questions?** See `research_core/README.md` for API documentation and usage examples.
