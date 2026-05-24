# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_stronger_cost_aware_sign_20b_lab_cost_sign_20b_5bps_20260522_225530`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet`
- **Label:** `lab_cost_sign_20b_5bps`
- **Return column:** `fwd_ret_20b`
- **Horizon:** 20 bars
- **Threshold:** 0.55
- **Cost:** 2.0 bps
- **Runtime:** 28.69s

## Model Results

- **Trade count:** 2716
- **Win rate:** 0.5394
- **Avg trade return (net):** -0.000096
- **Total return (gross):** 0.281753
- **Total return (net):** -0.261447
- **Max drawdown:** -0.296419
- **Longs:** 1546
- **Shorts:** 1170

## Baseline Comparison

- **Best baseline:** `random_seed_3`
- **Best baseline return (net):** -0.339718
- **Excess over best baseline:** 0.078271

## Baselines Detail

- `always_long`: trades=2779, win_rate=0.4987, return_net=-0.531460
- `always_short`: trades=2779, win_rate=0.5013, return_net=-0.580140
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=2779, win_rate=0.5027, return_net=-0.532852

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
