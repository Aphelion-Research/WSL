# BOI M15 MTF Research Pipeline

**Status:** Research candidate (v0.1.0)  
**Date:** 2026-05-27  
**Purpose:** Clean XAUUSD M15 scalping with honest validation

---

## Overview

BOI (Baseline Operational Intelligence) replaces rejected Him models with clean research pipeline:

- **Decision timeframe:** M15
- **Context timeframes:** M5, H1, H4, D1
- **Validation:** research_core integration (next-bar entry, cost sensitivity, null tests)
- **Objective:** Cost-aware scalping with strong skip behavior

**Key principle:** Build small, validate brutally, reject fast.

---

## Pipeline Structure

```
boi/
├── __init__.py
├── data.py              # Data loading + validation
├── features.py          # Multi-timeframe feature builder
├── labels.py            # Triple-barrier cost-aware labels
└── resample.py          # M5 → M15 resampling

config/models/
└── boi_m15_mtf.yaml     # Full config

scripts/
├── train_boi_m15_mtf.py       # Training
├── validate_boi_m15_mtf.py    # Validation + null tests
└── diagnose_boi_m15_mtf.py    # Regime breakdown

output_boi/              # Outputs
├── boi_m15_mtf_model.json
├── boi_m15_mtf_metadata.json
├── boi_m15_mtf_features.json
├── validation_report.json
└── diagnostics_report.json
```

---

## Features

### M15 Features (~30 features)
- Returns: 1, 2, 4, 8, 16 bars
- ATR + ATR percentile
- Body/wick/range ratios
- Close position in range
- Volatility percentile (96 bars)
- Distance to rolling high/low (16, 48, 96 bars)
- Compression/expansion (ATR ratio 8, 16 bars)

### M5 Aggregated (~5 features)
- Last 3 M5 returns (point-in-time safe)
- M5 realized volatility
- M5 range expansion
- M5 directional consensus
- M5 wick rejection proxy

### HTF Context (~6 features)
- H1: trend, SMA distance, range position, volatility regime
- H4: trend, compression
- D1: trend

**All HTF features use backward fill (as-of join) — no lookahead.**

### Session (~8 features)
- Asia/London/NY/Late flags
- London-NY overlap
- Hour/day cyclical encoding

**Total: ~50 compact features** (vs Him's 37)

---

## Labels

**Triple-barrier with cost awareness:**

1. Signal at bar i → entry at bar i+1 (next-bar, no lookahead)
2. Entry price = open[i+1]
3. Scan forward 8 M15 bars (default horizon)
4. Stop: 1.0 ATR
5. Target: 2.0 ATR
6. Cost included in PnL calculation
7. Ambiguity handling: Stop hit first if both touched (conservative)

**Classes:**
- 0 = short
- 1 = skip/no-trade (when neither direction profitable after costs)
- 2 = long

**Expected distribution:** Skip class dominates (60-70%) → use class weights.

---

## Training

**Model:** XGBoost multiclass

**Config:**
- max_depth: 5 (small tree → avoid overfit)
- learning_rate: 0.05
- n_estimators: 300
- early_stopping: 30 rounds
- class_weights: Automatic balancing

**Data splits:**
- Train: 2015-2022 (8 years)
- Validation: 2023 (1 year)
- OOS: 2024-2026 (2+ years, research OOS)

**Quick mode:** `--quick` flag trains on 10k sample for testing.

---

## Validation

research_core integration enforces:

### 1. Cost Sensitivity
Test at 0x, 0.5x, 1x, 2x, 3x baseline costs.

**Pass criteria:**
- PF > 1.15 at 1x costs
- PF >= 1.03 at 2x costs

### 2. Null Tests
- Random probabilities
- Shuffled probabilities
- Shifted +1, +5, +20 bars
- Reversed signal

**Pass criteria:** Original Sharpe > all null Sharpe.

### 3. Stability Metrics
- Monthly profit factor
- Quarterly Sharpe
- Yearly return
- Top 5 trades contribution
- Longest win/loss streaks

**Pass criteria:**
- Top 5 trades < 50% of total PnL
- >= 40% of months profitable

### 4. Execution
- Next-bar entry (lag = 1)
- Hold: 8 bars (match label horizon)
- Stop: 1.0 ATR
- Target: 2.0 ATR
- Conservative stop/TP ambiguity

---

## Diagnostics

Extended analysis includes:

### Regime Breakdown
- **Monthly:** PnL, trades, average per month
- **Session:** Asia, London, NY, Late performance
- **Volatility regime:** High/low vol performance (if applicable)

### Trade Distribution
- Mean/median/std PnL
- Win/loss distribution
- Top/bottom 5 trades impact
- Exit reason breakdown (stop, target, timeout)

### Baselines (Future)
- Random regime-matched entries
- Previous candle direction
- Simple momentum
- Simple mean reversion

**BOI must beat baselines.**

---

## Rejection Criteria

BOI v0 is REJECTED unless:

✓ Sharpe >= 0.3 OOS  
✓ PF > 1.15 at 1x costs  
✓ PF >= 1.03 at 2x costs  
✓ Beats all null tests  
✓ Top 5 trades < 50% of PnL  
✓ >= 40% of months profitable  
✓ Works across sessions (not just one regime)  
✓ Uses next-bar entry only  
✓ No contamination flags  

**If rejected:** Document why, extract lessons, move to next hypothesis.

---

## Usage

### 1. Generate M15 Data (if needed)
```bash
python boi/resample.py
```

### 2. Train Model
```bash
# Quick test (10k samples)
python scripts/train_boi_m15_mtf.py --quick

# Full training
python scripts/train_boi_m15_mtf.py
```

### 3. Validate
```bash
python scripts/validate_boi_m15_mtf.py
```

### 4. Diagnose
```bash
python scripts/diagnose_boi_m15_mtf.py
```

---

## Key Differences from Him

| Aspect | Him V2 | BOI v0 |
|--------|--------|--------|
| **Entry** | Same-bar (lookahead) | Next-bar (honest) |
| **Features** | 37 | ~50 (more compact HTF) |
| **Labels** | Forward return | Cost-aware triple-barrier |
| **Validation** | Legacy scripts | research_core integration |
| **Stop/TP** | Optimistic ambiguity | Conservative ambiguity |
| **Skip class** | No | Yes (dominant) |
| **Result** | Fake +116% → Real -$8.8k | TBD (honest from start) |

---

## Research Philosophy

### Don't
- Optimize on OOS
- Claim profitability before validation
- Train huge models
- Use same-bar entry
- Reuse Him assumptions
- Call v0 "production"

### Do
- Validate brutally
- Reject fast
- Document failures
- Extract lessons
- Build small
- Test honestly

---

## Expected Outcome

**Most likely:** BOI v0 will be REJECTED.

**Why:** XAU/USD M15 scalping is hard. Cost-aware labels + next-bar entry + realistic costs = high bar.

**If rejected:** Learn why, iterate to BOI v1 with improvements.

**If validated (preliminary):** Still research only. Need walk-forward, regime tests, longer OOS before considering production.

---

## Tests Added

```python
tests/
└── test_boi_pipeline.py
    ├── test_no_forbidden_columns
    ├── test_point_in_time_htf_joins
    ├── test_next_bar_entry
    ├── test_conservative_ambiguity
    ├── test_label_horizon_no_cross_split
    └── test_cost_sensitivity_degrades
```

Run: `pytest tests/test_boi_pipeline.py -v`

---

## Status

**Created:** 2026-05-27  
**Training:** In progress (quick mode)  
**Validation:** Pending  
**Verdict:** TBD

---

## Files

- Config: `config/models/boi_m15_mtf.yaml`
- Pipeline: `boi/*.py`
- Scripts: `scripts/train_boi_m15_mtf.py`, `validate_boi_m15_mtf.py`, `diagnose_boi_m15_mtf.py`
- Docs: `BOI_RESEARCH_PIPELINE.md` (this file)

---

**Next:** Await training completion → validate → reject or iterate.
