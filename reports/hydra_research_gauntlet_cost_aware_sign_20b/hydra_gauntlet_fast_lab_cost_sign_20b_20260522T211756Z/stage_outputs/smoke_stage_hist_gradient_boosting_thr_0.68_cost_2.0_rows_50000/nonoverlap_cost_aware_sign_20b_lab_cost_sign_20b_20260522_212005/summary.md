# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_cost_aware_sign_20b_lab_cost_sign_20b_20260522_212005`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_20b.parquet`
- **Label:** `lab_cost_sign_20b`
- **Return column:** `fwd_ret_20b`
- **Horizon:** 20 bars
- **Threshold:** 0.68
- **Cost:** 2.0 bps
- **Runtime:** 28.98s

## Model Results

- **Trade count:** 1170
- **Win rate:** 0.5530
- **Avg trade return (net):** -0.000084
- **Total return (gross):** 0.135861
- **Total return (net):** -0.098139
- **Max drawdown:** -0.131839
- **Longs:** 479
- **Shorts:** 691

## Baseline Comparison

- **Best baseline:** `random_seed_3`
- **Best baseline return (net):** -0.159879
- **Excess over best baseline:** 0.061740

## Baselines Detail

- `always_long`: trades=1466, win_rate=0.4823, return_net=-0.337315
- `always_short`: trades=1466, win_rate=0.5177, return_net=-0.249085
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=1466, win_rate=0.5095, return_net=-0.200490

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
