# Dominion Metrics Definition

**Date:** 2026-05-19  
**Author:** Claude Code (Sonnet 4.5)  
**Module:** `scripts/metrics.py`  
**Status:** DEFINED

---

## Executive Summary

**Standard quant metrics defined** for Dominion model evaluation:
1. **IC** (Information Coefficient) — Rank correlation between predictions and actuals
2. **Sharpe Ratio** — Risk-adjusted returns
3. **Maximum Drawdown** — Worst peak-to-trough decline
4. **Turnover** — Position churn rate
5. **Win Rate** — Fraction of profitable trades
6. **Profit Factor** — Ratio of gains to losses

**Target thresholds set** for each metric (excellent / good / acceptable / poor).

**Implementation:** `scripts/metrics.py` — Ready to use.

---

## Metrics Definitions

### 1. Information Coefficient (IC)

**Definition:** Spearman rank correlation between model predictions and actual forward returns.

**Formula:**
```
IC = spearmanr(predictions, actuals)
```

**Why Spearman?**
- Rank-based (robust to outliers)
- Measures monotonic relationship
- Common in quant finance

**Interpretation:**
- IC = 0.10 → 10% rank correlation (excellent for daily prediction)
- IC = 0.05 → 5% rank correlation (tradeable)
- IC = 0.02 → 2% rank correlation (weak signal)
- IC ≤ 0.00 → No predictive power

**Target Thresholds:**
| Rating | IC |
|---|---|
| Excellent | > 0.10 |
| Good | > 0.05 |
| Acceptable | > 0.02 |
| Poor | ≤ 0.00 |

**Why these thresholds?**
- **IC > 0.10:** Publication-worthy, institutional-grade
- **IC > 0.05:** Profitable after costs (typical HFT threshold)
- **IC > 0.02:** Detectable signal, might be profitable with low costs
- **IC ≤ 0.00:** Random or worse

---

### 2. Sharpe Ratio

**Definition:** Annualized risk-adjusted return.

**Formula:**
```
Sharpe = (mean_return - risk_free_rate) / std_return * sqrt(252)
```

**Annualization:**
- Daily data → multiply by sqrt(252)
- Monthly data → multiply by sqrt(12)
- Hourly data → multiply by sqrt(252 * 24)

**Risk-free rate:** Default 0.0 (gold has no cash yield, conservative assumption)

**Interpretation:**
- Sharpe = 2.0 → Return 2x volatility (excellent)
- Sharpe = 1.0 → Return = volatility (good)
- Sharpe = 0.5 → Return = 0.5x volatility (acceptable)
- Sharpe ≤ 0.0 → Losing strategy

**Target Thresholds:**
| Rating | Sharpe |
|---|---|
| Excellent | > 2.0 |
| Good | > 1.0 |
| Acceptable | > 0.5 |
| Poor | ≤ 0.0 |

**Why these thresholds?**
- **Sharpe > 2.0:** Institutional hedge funds target 1.5-2.0+
- **Sharpe > 1.0:** Typical "good" quant strategy
- **Sharpe > 0.5:** Better than buy-and-hold (S&P 500 Sharpe ~0.4)
- **Sharpe ≤ 0.0:** Losing money

---

### 3. Maximum Drawdown

**Definition:** Worst peak-to-trough decline in cumulative returns.

**Formula:**
```
Drawdown[t] = (CumReturn[t] - RunningMax[t]) / RunningMax[t]
MaxDrawdown = min(Drawdown)
```

**Interpretation:**
- Max DD = -5% → Very stable (excellent)
- Max DD = -10% → Acceptable for most investors
- Max DD = -20% → Risky, requires strong conviction
- Max DD = -50% → Catastrophic, unacceptable

**Target Thresholds:**
| Rating | Max DD |
|---|---|
| Excellent | > -5% |
| Good | > -10% |
| Acceptable | > -20% |
| Poor | < -50% |

**Why these thresholds?**
- **> -5%:** Low-vol strategies (market-neutral, stat-arb)
- **> -10%:** Typical quant equity long-short
- **> -20%:** Directional strategies, single-asset
- **< -50%:** Unacceptable risk, likely over-leveraged

---

### 4. Turnover

**Definition:** Average daily position change.

**Formula:**
```
Turnover = mean(abs(Position[t] - Position[t-1]))
```

**Interpretation:**
- Turnover = 0.1 → 10% position change per day (low-frequency)
- Turnover = 0.5 → 50% change per day (medium-frequency)
- Turnover = 1.0 → Full position flip per day (high-frequency)
- Turnover = 2.0 → 200% churn (very expensive)

**Target Thresholds:**
| Rating | Turnover |
|---|---|
| Excellent | < 0.1 |
| Good | < 0.5 |
| Acceptable | < 1.0 |
| Poor | > 2.0 |

**Why these thresholds?**
- **< 0.1:** Low-frequency (swing trading), minimal costs
- **< 0.5:** Medium-frequency (daily rebalance), manageable costs
- **< 1.0:** High-frequency (intraday), requires low latency
- **> 2.0:** Excessive churn, costs dominate returns

**Cost assumptions:**
- Gold futures: ~$0.25/oz round-trip (~0.01% of $2500/oz)
- Daily turnover = 1.0 → ~250 bps/year costs
- Sharpe erosion: -0.02 per 1.0 turnover

---

### 5. Win Rate

**Definition:** Fraction of trades with positive returns.

**Formula:**
```
WinRate = count(return > 0) / count(return)
```

**Interpretation:**
- Win Rate = 60% → More wins than losses (good for morale)
- Win Rate = 50% → Break-even (neutral)
- Win Rate = 40% → More losses, but can be profitable if wins are larger

**Not a primary metric:** Can be misleading (many small wins + few large losses = high win rate but losing strategy).

**Use:** Supplementary metric for understanding strategy character.

---

### 6. Profit Factor

**Definition:** Ratio of total gains to total losses.

**Formula:**
```
ProfitFactor = sum(returns[returns > 0]) / abs(sum(returns[returns < 0]))
```

**Interpretation:**
- Profit Factor = 2.0 → Gains are 2x losses (excellent)
- Profit Factor = 1.5 → Gains are 1.5x losses (good)
- Profit Factor = 1.0 → Gains = losses (break-even)
- Profit Factor < 1.0 → Losses exceed gains (losing)

**Target:** > 1.2 for profitable strategy.

---

## Implementation

### Module: `scripts/metrics.py`

**Functions:**

```python
# Individual metrics
compute_sharpe(returns, risk_free_rate=0.0, annualization_factor=252) -> float
compute_ic(predictions, actuals) -> (float, float)  # Returns (IC, p-value)
compute_turnover(positions) -> float
compute_max_drawdown(cumulative_returns) -> (float, str, str)  # Returns (max_dd, start, end)
compute_win_rate(returns) -> float
compute_profit_factor(returns) -> float

# Aggregate
compute_all_metrics(predictions, actuals, returns=None, positions=None) -> Dict[str, float]

# Evaluation
evaluate_model(metrics) -> Dict[str, str]  # Returns ratings (excellent/good/acceptable/poor)
print_metrics(metrics, title="Metrics")
```

### Example Usage

```python
from scripts.metrics import compute_all_metrics, print_metrics, evaluate_model
import pandas as pd

# Load data
val_df = pd.read_parquet("data/val_v1.parquet")

# Predict
predictions = model.predict(val_df[feature_cols])

# Compute metrics
metrics = compute_all_metrics(
    predictions=pd.Series(predictions),
    actuals=val_df["target_return_1"],
    returns=val_df["strategy_return"],
    positions=val_df["position"],
)

# Print
print_metrics(metrics, title="Validation Set Metrics")

# Evaluate
ratings = evaluate_model(metrics)
print(f"IC Rating: {ratings['ic']}")
print(f"Sharpe Rating: {ratings['sharpe']}")
```

---

## Comparison: Train vs Val vs Test

**Never compute test metrics until final evaluation.**

### Workflow

1. **Train:** Train model on train set
2. **Val:** Compute metrics on val set → tune hyperparameters
3. **Test:** After model selection, compute metrics on test set **once**

### Expected Degradation

- **Train IC:** Often inflated (in-sample overfitting)
- **Val IC:** Realistic estimate
- **Test IC:** Final unbiased estimate

**Typical degradation:**
- Train IC = 0.08
- Val IC = 0.05 (-38%)
- Test IC = 0.04 (-50% from train)

**If test IC ≫ val IC:** Lucky test set (or leakage!)

---

## Baseline Targets (Task #11)

### Ridge Regression Baseline

**Expected metrics:**
- IC: 0.02 - 0.04 (weak signal)
- Sharpe: 0.3 - 0.6 (acceptable)
- Max DD: -15% to -25%
- Turnover: 0.5 - 1.0 (medium-frequency)

**Rating:** Acceptable (establishes floor)

### Random Forest Baseline

**Expected metrics:**
- IC: 0.04 - 0.06 (good)
- Sharpe: 0.6 - 1.0 (good)
- Max DD: -10% to -20%
- Turnover: 0.5 - 1.0 (medium-frequency)

**Rating:** Good (non-linear beats linear)

### Neural Network (Future)

**Target metrics:**
- IC: 0.06 - 0.10 (excellent)
- Sharpe: 1.0 - 2.0 (excellent)
- Max DD: -5% to -15%
- Turnover: 0.5 - 1.0 (same frequency)

**Rating:** Excellent (goal for deep learning)

---

## Regime-Conditioned Metrics (Task #15)

**Split metrics by regime:**
- London session (high volatility)
- NY session (high volume)
- Asian session (low activity)
- Overlap (highest liquidity)
- Dead zone (illiquid)

**Expected:**
- Higher IC during overlap (more information)
- Higher turnover during NY (more rebalancing)
- Higher drawdown during asian (fewer trades, larger moves)

**Implementation:**
```python
for regime in ["london", "ny", "asian", "overlap", "dead_zone"]:
    subset = val_df[val_df["regime_micro"] == regime]
    metrics_regime = compute_all_metrics(...)
    print_metrics(metrics_regime, title=f"Metrics - {regime.upper()}")
```

---

## Next Steps

1. ✓ Define metrics (this report)
2. → Build baseline models (Task #11)
3. → Compute metrics on val set
4. → Compare baselines
5. → Build dataset v1 (Task #13)
6. → Feature stability monitoring (Task #14)
7. → Regime-conditioned metrics (Task #15)

---

**Metrics defined.** Ready for baseline modeling (Task #11).
