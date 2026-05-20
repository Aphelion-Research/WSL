# HYDRA Training Pipeline (Agent 2)

**Status:** Ready to train (awaiting Agent 1 gate verdict)  
**Owner:** Agent 2 (HYDRA + ML + Backtest Engineer)  
**Date:** 2026-05-20

---

## Quick Start

### 1. Check Gate Status

```python
from hydra.training.guardrails import check_training_allowed

training_allowed, verdict = check_training_allowed()

if training_allowed:
    print("Ready to train!")
else:
    print(f"Training blocked: {verdict.reason}")
```

### 2. Run Training

```bash
# Default (dataset_v1.parquet, all brains, gate check enabled)
python scripts/run_hydra_training.py

# Custom matrix
python scripts/run_hydra_training.py --matrix /path/to/matrix.parquet

# Train only scalp brain
python scripts/run_hydra_training.py --mode scalp

# Skip gate check (DANGEROUS!)
python scripts/run_hydra_training.py --no-gate-check
```

### 3. Check Results

Artifacts saved to `artifacts/hydra/`:
- `scalp_brain_YYYYMMDD_HHMMSS.pkl` (trained model)
- `metrics_YYYYMMDD_HHMMSS.json` (Sharpe, WR, etc.)
- `config_YYYYMMDD_HHMMSS.json` (hyperparameters)
- `equity_curve_YYYYMMDD_HHMMSS.csv` (bar-by-bar equity)
- `trades_YYYYMMDD_HHMMSS.csv` (entry/exit/pnl)

---

## Module Structure

```
hydra/
├── labels/
│   ├── __init__.py
│   └── triple_barrier.py       # Enhanced labeling (Agent 1 fixes)
├── training/
│   ├── __init__.py
│   ├── splits.py               # Chronological splits + embargo/purge
│   ├── guardrails.py           # Gate checking (training_allowed)
│   ├── hydra_runner.py         # Main training pipeline
│   ├── metrics.py              # ML + cost-aware + backtest metrics
│   └── backtest.py             # Backtest evaluator wrapper
└── tests/
    └── training/
        ├── test_labels.py      # 7 tests (all passing)
        ├── test_splits.py      # 6 tests (all passing)
        └── test_guardrails.py  # 7 tests (all passing)
```

---

## Usage Examples

### Example 1: Full Pipeline (Programmatic)

```python
from hydra.training.hydra_runner import HydraRunner

# Create runner
runner = HydraRunner(
    matrix_path="data/dataset_v1.parquet",
    output_dir="artifacts/hydra",
    check_gates=True,
    mode="all",
)

# Run training (loads, validates, labels, splits, trains, evaluates, saves)
metrics = runner.run()

if "error" in metrics:
    print(f"Training blocked: {metrics['reason']}")
else:
    print(f"Sharpe: {metrics['sharpe']:.2f}")
    print(f"Win Rate: {metrics['win_rate']:.1%}")
    print(f"Profit: ${metrics['profit']:.0f}")
```

### Example 2: Labels Only

```python
from hydra.labels.triple_barrier import TripleBarrierLabeler
import pandas as pd

# Load data
df = pd.read_parquet("data/dataset_v1.parquet")

# Generate labels
labeler = TripleBarrierLabeler(
    atr_window=14,
    horizon_bars=20,
    stop_mult=1.0,
    target_mult=2.0,
    min_atr_pct=0.0020,      # Agent 1 recommendation
    min_hold_bars=3,          # Prevent one-bar spikes
    spread_to_atr_min=0.33,   # Max 33% cost-to-risk
    use_session_spread=True,  # London/NY vs Asian spread
)

labels, metadata = labeler.fit_transform(df)

print(f"Label rate: {metadata.label_rate:.1%}")
print(f"Long rate: {metadata.long_rate:.1%}")
print(f"Mean ATR: ${metadata.mean_atr:.2f}")
```

### Example 3: Splits Only

```python
from hydra.training.splits import ChronologicalSplit
import pandas as pd

# Load data
df = pd.read_parquet("data/dataset_v1.parquet")

# Create splitter
splitter = ChronologicalSplit(
    n_splits=3,
    expanding_window=True,
    embargo_bars=32,
    purge_bars=48,
)

# Generate splits
splits = splitter.split(df)

for i, (train_idx, val_idx, test_idx, meta) in enumerate(splits):
    print(f"Fold {i + 1}:")
    print(f"  Train: {meta.train_size:,} bars ({meta.train_date_range[0]} to {meta.train_date_range[1]})")
    print(f"  Val: {meta.val_size:,} bars")
    print(f"  Test: {meta.test_size:,} bars")
```

### Example 4: Guardrails Only

```python
from hydra.training.guardrails import TrainingGuardrails

# Check Agent 1's gate verdict
guardrails = TrainingGuardrails()
verdict = guardrails.check_gate_verdict()

if verdict.training_allowed:
    print("Gates passed, ready to train!")
else:
    print(f"Training blocked: {verdict.reason}")
    print(f"Failed gates: {verdict.gates_failed}")
    
    # Write blocked report
    guardrails.write_blocked_report(verdict)
```

---

## Gate Verdict Format

**File:** `/data/training_gate_verdict.json` (Agent 1 writes this)

```json
{
  "training_allowed": true,
  "reason": "All quality gates passed",
  "gates_passed": ["quality", "stationarity", "no_leakage", "sufficient_data"],
  "gates_failed": [],
  "matrix_rows": 5000,
  "matrix_cols": 3000,
  "date_range": "2021-01-01 to 2026-05-20"
}
```

**If training_allowed=false:**
- Agent 2 writes blocked report to `reports/training_blocked_YYYYMMDD.md`
- Training does NOT proceed
- User must fix blockers and re-run Agent 1 gate check

---

## Agent 1 Adversarial Fixes

Agent 2 training pipeline addresses all Agent 1 concerns:

1. **Embargo too short (10 bars for 20-bar horizon)** → Fixed: `embargo_bars = max(20 + 12, 32) = 32`
2. **min_atr_pct=0.0005 too permissive** → Fixed: `min_atr_pct=0.0020`
3. **Both-barriers-hit assigned as long** → Fixed: assigned as NaN
4. **No min hold bars** → Fixed: `min_hold_bars=3`
5. **Fixed spread ($0.30)** → Fixed: session-conditional (London/NY=$0.15, Asian=$0.50)
6. **No spread-to-ATR filter** → Fixed: max 33% cost-to-risk

See `docs/agent_reports/agent_1_quant_finance.md` for full adversarial review.

---

## Metrics Reference

### ML Metrics
- **Accuracy:** % correct predictions
- **Precision:** % true positives among predicted positives
- **Recall:** % true positives among actual positives
- **F1:** Harmonic mean of precision/recall
- **ROC-AUC:** Area under ROC curve
- **Log Loss:** Negative log-likelihood

### Cost-Aware Metrics
- **Gross Profit:** Total profit from winning trades
- **Gross Loss:** Total loss from losing trades
- **Net Profit:** Gross profit - gross loss
- **Profit/Trade:** Net profit / num trades
- **Cost/Trade:** Spread + slippage + commission
- **Cost/Stop Ratio:** Transaction cost / stop distance (%)
- **Break-Even Accuracy:** Required accuracy to be profitable after costs

### Backtest Metrics
- **Sharpe:** Risk-adjusted return (annualized)
- **Sortino:** Downside-adjusted return
- **Calmar:** Return / max drawdown
- **Win Rate:** % winning trades
- **Avg RR:** Mean winner / mean loser
- **Profit Factor:** Gross profit / gross loss
- **Max Drawdown:** Largest peak-to-trough equity decline (%)
- **Profit:** Total P&L ($)
- **Trades:** Number of trades

---

## Safety Checks

### Split Safety Validation

```python
from hydra.training.splits import validate_split_safety

checks = validate_split_safety(train_idx, val_idx, test_idx, horizon_bars=20, embargo_bars=32)

# All checks must pass:
assert checks["no_train_val_overlap"]
assert checks["no_train_test_overlap"]
assert checks["chronological_train_val"]
assert checks["embargo_train_val_sufficient"]
assert checks["no_label_leakage_train_val"]
```

### Column Exclusion

```python
from hydra.training.guardrails import exclude_non_features

# Remove label/quality/reserved columns before training
df_features = exclude_non_features(
    df,
    label_col_pattern="label",
    quality_col_pattern="quality",
    reserved_cols=["timestamp", "open", "high", "low", "close", "volume"],
)
```

---

## Testing

```bash
# Run all training tests
python -m pytest tests/training/ -v

# Run specific test module
python -m pytest tests/training/test_labels.py -v
python -m pytest tests/training/test_splits.py -v
python -m pytest tests/training/test_guardrails.py -v

# Run single test
python -m pytest tests/training/test_labels.py::test_triple_barrier_basic -v -s
```

**Test coverage:**
- Labels: 7 tests (session detection, spread, triple-barrier, both-hit, min-hold, spread-filter, statistics)
- Splits: 6 tests (embargo/purge, expanding window, OOS split, safety validation, overlap detection, insufficient data)
- Guardrails: 7 tests (verdict missing/pass/fail, quality pass/fail, column exclusion, blocked report)

**All tests passing: 20/20 ✅**

---

## Troubleshooting

### "Training blocked: Gate verdict file not found"

**Cause:** Agent 1 has not written `/data/training_gate_verdict.json`

**Fix:**
1. Wait for Agent 1 to complete matrix build + quality gates
2. OR use `--no-gate-check` (DANGEROUS - bypasses safety checks)

```bash
python scripts/run_hydra_training.py --no-gate-check
```

### "Label rate too low (< 30%)"

**Cause:** Too few bars pass ATR/spread filters

**Fix:** Adjust labeler parameters:
- Lower `min_atr_pct` (e.g., 0.0015 instead of 0.0020)
- Lower `spread_to_atr_min` (e.g., 0.25 instead of 0.33)
- Check session distribution (Asian session has low label rate due to wide spread)

### "Insufficient data for split"

**Cause:** Not enough rows for train/val/test split with embargo/purge

**Fix:**
- Use longer date range (Agent 1 matrix)
- Reduce embargo/purge bars (NOT recommended - risks leakage)
- Use single train/OOS split instead of walk-forward

### "All-NaN columns detected"

**Cause:** Feature has no valid data

**Fix:** Check feature computation pipeline (Agent 1 issue)

---

## Integration with Existing HYDRA

Agent 2 training pipeline is **additive** (does not break existing code):

**Preserved:**
- `hydra/loop/improver.py` (original autonomous loop)
- `hydra/data/targets.py` (original triple-barrier)
- `hydra/data/cv.py` (original CV splits)
- `hydra/backtest/engine_py.py` (original backtest)
- `hydra/brains/*.py` (scalp/day/swing brains)

**Added:**
- `hydra/labels/triple_barrier.py` (enhanced labeling, supplements original)
- `hydra/training/*.py` (new training pipeline, alternative to improver.py)

**Both workflows coexist:**
- **Old:** `python hydra/loop/improver.py` (uses original code)
- **New:** `python scripts/run_hydra_training.py` (uses Agent 2 code)

---

## Contact

- **Agent 2 Owner:** Martin (HYDRA Training Engineer)
- **Agent 1 Contact:** (Matrix Builder)
- **RAGD Integration:** `hydra/ragd/memory.py` (remember() calls)
- **Storage:** `hydra/storage/duckdb_writer.py` (HydraDB)

---

## References

- **Agent 1 Report:** `docs/agent_reports/agent_1_quant_finance.md` (adversarial review)
- **Agent 2 Report:** `docs/agent_reports/agent_2_hydra_training.md` (deliverables)
- **CLAUDE.md:** `CLAUDE.md` (platform contract)
- **HYDRA Config:** `hydra/config.py` (hyperparameters)
- **Backtest Metrics:** `hydra/backtest/metrics.py` (Sharpe/Sortino/Calmar)

---

**Last Updated:** 2026-05-20  
**Status:** Ready to train (awaiting Agent 1 gate verdict)
