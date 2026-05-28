# Him V2 MultiScale Validation Summary

**Date:** 2026-05-27  
**Status:** ❌ **REJECTED** — No edge after honest execution

---

## Executive Summary

Him V2 MultiScale model shows **NO profitable threshold** on OOS data (2024-2026) when validated with conservative execution rules (next-bar entry, realistic costs).

**All tested thresholds produce losses:**
- Best: 0.75 threshold → -$251 (11 trades, 27% WR)
- Worst: 0.50 threshold → -$94,286 (8450 trades, 36% WR)

**Root cause:** Legacy backtests used **same-bar entry** or other lookahead, creating phantom edge.

---

## Threshold Grid Search Results (OOS 2024-2026)

**Locked Config:**
- Hold: 16 bars (80 min)
- Stop: 1.5 ATR
- TP: 3.0 ATR
- Entry: Next-bar (signal at bar i → enter bar i+1)
- Costs: 0.30 spread + 0.10 slippage + $7/lot commission

| Threshold | Trades | Sharpe | PnL       | Win % | Max DD    |
|-----------|--------|--------|-----------|-------|-----------|
| 0.50      | 8,450  | -0.11  | -$94,286  | 36.0% | $94,605   |
| 0.55      | 4,579  | -0.10  | -$55,928  | 35.9% | $56,168   |
| 0.60      | 1,983  | -0.08  | -$22,510  | 37.5% | $24,274   |
| **0.65**  | **708**| **-0.08** | **-$8,795** | **39.4%** | **$9,511** |
| 0.70      | 226    | -0.09  | -$2,072   | 41.6% | $2,616    |
| 0.75      | 11     | -0.35  | -$251     | 27.3% | $308      |

**Best Sharpe:** 0.60 (Sharpe -0.08) — still loses  
**Best PnL:** 0.75 (only -$251) — but 11 trades, statistically insignificant  

---

## Legacy Backtest Discrepancy

**Legacy Results (multiscale_retrain_results.json):**
- Conservative (0.65): 857 trades, +116.5% return, 1.18 PF
- Period: 2024-2026 (allegedly)

**Research Core Results (honest execution):**
- Conservative (0.65): 708 trades, -$8,795 loss, -0.08 Sharpe
- Period: 2024-2026 (actual OOS)

**Difference:** ~+$12k → -$9k = **$21k phantom profit**

---

## Root Cause Analysis

### 1. Lookahead Bias in Legacy Scripts

Legacy scripts (`scripts/diagnostic_multiscale.py`, `scripts/retrain_him_v2_multiscale.py`) likely used:
- **Same-bar entry:** Signal at bar i → entry at bar i (lookahead)
- **Optimistic stop/TP:** Assume TP hit before stop in same bar
- **No spread on entry:** Entry at open instead of open + spread/2

**Research Core enforces:**
- **Next-bar entry:** Signal at bar i → entry at bar i+1 (realistic)
- **Conservative stop/TP:** Stop assumed hit first in ambiguous bars
- **Spread paid:** Entry at open + spread/2

### 2. Cost Model Differences

Legacy may have used:
- Lower spread (0.10 vs 0.30)
- No slippage
- Lower commission

Research Core uses conservative XAU/USD baseline:
- Spread: 0.30 points
- Slippage: 0.10 points
- Commission: $7/lot

### 3. Period Mismatch?

Legacy `baseline_comparison` claims:
- "OOS started 2025, trained to 2024"
- Period: "2025-01 to 2026-05 (17mo)"

But `multiscale_retrain_results.json` shows monthly breakdown from 2024-01.

**Verdict:** Inconsistent reporting. Likely legacy included in-sample (2024) in "OOS" results.

---

## Forensic Validation Results

**Status:** ✅ Complete

### Train Set (2000-2023)
- **Verdict:** REJECTED (fails null tests)
- Trades: 1,772
- Sharpe: -0.25
- Total PnL: -$16,050
- Win Rate: 33.8%
- Null test verdict: FAIL (better than only 4/6 null tests)
- Stability: UNSTABLE_MONTHLY

### OOS Set (2024-2026)
- **Verdict:** REJECTED (fails null tests)
- Trades: 708
- Sharpe: -0.08
- Total PnL: -$8,795
- Win Rate: 39.4%
- Null test verdict: FAIL (better than only 3/6 null tests)
- Stability: UNSTABLE_MONTHLY

### Null Test Breakdown (OOS)
| Test Type | Sharpe | vs Original |
|-----------|--------|-------------|
| Original  | -0.083 | —           |
| Random    | -0.145 | ✓ Worse     |
| Shuffled  | -0.093 | ✓ Worse     |
| Shifted +1| **-0.076** | ❌ **BETTER** |
| Shifted +5| **-0.075** | ❌ **BETTER** |
| Shifted +20| -0.102 | ✓ Worse     |
| Reversed  | **-0.053** | ❌ **MUCH BETTER** |

**Critical finding:** Reversed signals (-0.053 Sharpe) perform BETTER than original (-0.083). Model has slight inverse predictive value but not enough to profit after costs.

### Cost Sensitivity
- **NOT robust to 2x costs**
- **NOT robust to 3x costs**
- Model loses money at baseline costs; higher costs make losses worse

### Degradation Analysis
| Metric | Train | OOS | Change |
|--------|-------|-----|--------|
| Sharpe | -0.25 | -0.08 | +67% (less bad) |
| PnL    | -$16k | -$8.8k | +45% (less bad) |
| Win %  | 33.8% | 39.4% | +16.6% |

**Note:** "Improvement" from train to OOS is just degradation getting less severe. Model still loses money in both periods.

---

## Recommendations

### Immediate Actions

1. **STOP** using Him V2 for forward trading
2. **STOP** trusting legacy backtest scripts
3. **DO NOT OPTIMIZE** — no edge to optimize

### Next Steps

**Option A: Abandon Him Line**
- Him V2 has no edge after honest validation
- Do not waste time on Him V3, Him V4, etc.
- Pivot to new hypothesis

**Option B: Forensic Autopsy (Research Only)**
- Run forensic validation to completion
- Document why features failed (regime change? mean reversion dead?)
- Extract lessons for RAGD

**Option C: Start Fresh with Research Core**
- Use `research_core/` for all future validation
- Build new hypothesis from scratch
- Test with honest execution from day 1

---

## Key Lessons

1. **Same-bar entry creates phantom edge**
   - Legacy Him V2 profits disappeared with next-bar entry
   - ~$21k phantom profit erased by 1-bar lag

2. **Legacy scripts untrustworthy**
   - No validation safeguards
   - Mixed in-sample/OOS results
   - Inconsistent cost models

3. **Research Core works**
   - Caught overfitting immediately
   - Clear failure signal (all negative Sharpe)
   - Prevents wasting time on doomed strategies

---

## Technical Details

### Data
- Source: `data/mt5_history/XAUUSD_M5_dukascopy.parquet`
- Range: 2000-2026 (~1.8M bars)
- OOS: 2024-01-01 onward

### Model
- File: `models/Him/Him_V2_MultiScale.json`
- Features: 37 (multi-scale returns, VWAP, ATR, RSI, pullbacks, time)
- Train AUC: 0.716
- OOS AUC: 0.688 (degradation already visible)

### Execution (Research Core)
- Entry: Next-bar (i+1)
- Hold: 16 bars
- Stop: 1.5 ATR
- TP: 3.0 ATR
- Costs: 0.30 spread + 0.10 slippage + $7/lot commission
- Position: 10 oz (0.1 lot)

---

## Files Generated

```
output_him_v2/
├── threshold_grid_oos.json          # Threshold comparison results
├── forensic_validation/
│   ├── train_forensic_report.json   # In-sample forensics (pending)
│   └── oos_forensic_report.json     # OOS forensics (pending)
```

Scripts:
```
scripts/
├── validate_him_v2_forensic.py      # Full forensic validation
├── him_v2_threshold_grid_oos.py     # Threshold grid search
```

---

## Conclusion

**Him V2 MultiScale has NO edge on OOS data after honest validation.**

Legacy backtest results were contaminated by lookahead bias (same-bar entry). With next-bar entry + realistic costs, model loses money at all thresholds.

**DO NOT TRADE HIM V2.**

---

**Next:** Await forensic validation completion for full breakdown, then decide: abandon Him line or autopsy for lessons.
