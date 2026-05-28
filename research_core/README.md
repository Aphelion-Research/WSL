# Research Core

Honest validation foundation for Dominion V2 quant research.

## Purpose

Research Core enforces:
- **Point-in-time data contracts:** Prevents future data leakage
- **Conservative execution simulation:** No same-bar entry by default, conservative stop/TP ambiguity
- **Forensic diagnostics:** Cost sensitivity, null tests, stability metrics
- **No optimization, no training, no claims:** Validate locked models only

## Structure

```
research_core/
├── data_contracts/      # Data validation (timestamps, forbidden columns)
│   ├── columns.py
│   └── validation.py
├── execution/           # Conservative trade simulator
│   ├── costs.py
│   └── simulator.py
├── diagnostics/         # Forensic tests
│   ├── null_tests.py
│   ├── cost_sensitivity.py
│   ├── stability.py
│   └── model_forensics.py
├── hypotheses/          # Research hypothesis registry (future)
├── reports/             # Report generation (future)
└── examples/            # Usage examples
    └── validate_locked_model.py
```

## Quick Start

### 1. Validate Data Contracts

```python
from research_core.data_contracts import validate_features, validate_ohlcv

# Validate OHLCV
ohlcv = pd.read_parquet("data/mt5_history/XAUUSD_M5_dukascopy.parquet")
validate_ohlcv(ohlcv)  # Raises ValidationError if missing columns

# Validate features
features = build_features(ohlcv)
validate_features(features, allow_label=False)  # Raises if forbidden columns found
```

### 2. Run Conservative Execution Simulation

```python
from research_core.execution import simulate_trades, SimulationConfig, CostModel

config = SimulationConfig(
    signal_at_bar_i_entry_at_bar_i_plus_n=1,  # Next-bar entry (default)
    hold_bars=16,  # Fixed hold period
    stop_loss_atr_mult=10.0,  # Catastrophic stop
    cost_model=CostModel.xauusd_baseline(),
)

result = simulate_trades(signals, ohlcv, config, atr=atr)

print(f"Trades: {len(result['trades'])}")
print(f"Sharpe: {result['metrics']['sharpe']:.2f}")
print(f"Total PnL: ${result['metrics']['total_pnl_net']:.2f}")
```

### 3. Run Forensic Diagnostics

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

print(f"Verdict: {report['verdict']}")
```

## Data Contract Rules

### Forbidden Feature Column Patterns

The following patterns indicate forward-looking or outcome data and are **forbidden** in feature columns:

- `label`, `target`
- `fwd`, `forward`, `future`
- `next_`, `lead_`
- `pnl`, `profit`, `outcome`
- `return_` (forward return)

Exception: `label` is allowed when `allow_label=True` (for label-context only).

### Required OHLCV Columns

- `open`, `high`, `low`, `close`
- `spread` (bid-ask spread in points)

### Timestamp Requirements

- Must be `DatetimeIndex`
- Must be monotonic increasing
- No duplicates

## Execution Simulator Rules

### Entry Timing

- **Default:** Signal at bar `i` → entry at bar `i+1` (next-bar)
- **Conservative:** No same-bar entry by default
- **Entry price:** `open[i+1] + spread/2` (pays full spread)

### Exit Logic

- **Hold bars:** Fixed hold period (e.g., 16 bars = 80 min)
- **Stop loss:** ATR-based catastrophic stop (e.g., 10 ATR)
- **Take profit:** ATR-based target (optional)

### Path-Dependent Stop/TP

- Stop/TP checked via `low`/`high` breach
- **Same-bar ambiguity:** If both stop and TP possible in same bar, assume stop hit first (conservative)

### Cost Model

- **Spread:** Bid-ask spread (e.g., 0.30 points)
- **Slippage:** Additional slippage per side (e.g., 0.10 points)
- **Commission:** Per-lot commission (e.g., $7/lot)

### Risk Controls

- **Daily drawdown breach:** Stop trading after daily loss exceeds threshold
- **Total drawdown breach:** Stop all trading after total loss exceeds threshold

## Forensic Diagnostics

### Cost Sensitivity

Tests performance at:
- `0x` costs (ideal)
- `0.5x` costs
- `1x` costs (baseline)
- `2x` costs
- `3x` costs

**Pass criteria:** Robust to 2x costs (still profitable).

### Null Tests

Tests against:
- **Random signals:** Same frequency, random timing
- **Shuffled signals:** Shuffle original signals
- **Shifted signals:** Shift forward by +1, +5, +20 bars
- **Reversed signals:** Flip long ↔ short

**Pass criteria:** Original Sharpe > all null Sharpe.

### Stability Metrics

- **Monthly profit factor:** Per-month wins/losses ratio
- **Quarterly Sharpe:** Per-quarter Sharpe ratio
- **Yearly return:** Per-year total return
- **Top 5 trades concentration:** % of PnL from top 5 trades
- **Win/loss streaks:** Longest consecutive wins/losses

**Pass criteria:** 
- Top 5 trades < 50% of PnL
- < 30% of months with PF < 1.0

## Model Forensics Verdict

The `run_model_forensics()` function returns a verdict:

- **VALIDATED:** Passed all tests (null, cost, stability)
- **WEAK:** Passed null tests but warnings (cost fragility, instability)
- **REJECTED:** Failed null tests
- **CONTAMINATED:** Data validation failed (forbidden columns, timestamps)

## Running Tests

```bash
# Install dependencies
pip install pytest pandas numpy xgboost

# Run all research_core tests
pytest tests/test_research_core_*.py -v

# Run specific test file
pytest tests/test_research_core_contracts.py -v
```

## Example Usage

See `research_core/examples/validate_locked_model.py` for full example.

```bash
python research_core/examples/validate_locked_model.py
```

## Integration with Legacy Scripts

Research Core is designed to **replace** scattered validation logic in legacy scripts over time:

### Legacy Scripts (Keep as Reference)

- `scripts/diagnostic_multiscale.py` → Use `research_core.diagnostics` instead
- `scripts/walk_forward_*.py` → Use `research_core.execution` for backtests
- `scripts/retrain_him_*.py` → **Do not use for new research** (optimization/training)

### Migration Path

1. **Phase 1 (now):** Use `research_core` for new validation workflows
2. **Phase 2:** Refactor working legacy scripts to use `research_core` modules
3. **Phase 3:** Archive/deprecate duplicate validation logic

## Design Principles

1. **Read-only validation:** No model training, no optimization
2. **Pessimistic execution:** Conservative assumptions prevent overstating edge
3. **Fail-fast contracts:** Reject contaminated data before simulation
4. **Transparent verdicts:** Clear pass/fail criteria, no ambiguity

## Future Enhancements

- [ ] Regime breakdown (session, volatility, trend)
- [ ] Hypothesis registry (track research decisions)
- [ ] PDF/HTML report generation
- [ ] Integration with RAGD (remember validation results)
- [ ] Walk-forward validation framework
- [ ] Multi-asset support

## Contributing

When adding new validation logic:
1. Add focused pytest tests first
2. Use conservative defaults
3. Document pass/fail criteria
4. Update this README

---

**Status:** Foundation complete (v0.1.0)  
**Last Updated:** 2026-05-27
