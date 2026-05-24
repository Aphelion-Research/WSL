# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_stronger_cost_aware_sign_72b_lab_cost_sign_72b_5bps_20260522_232946`
- **Verdict:** `NO_EDGE`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_72b.parquet`
- **Label:** `lab_cost_sign_72b_5bps`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.68
- **Cost:** 2.0 bps
- **Runtime:** 12.36s

## Model Results

- **Trade count:** 383
- **Win rate:** 0.5144
- **Avg trade return (net):** 0.000184
- **Total return (gross):** 0.147200
- **Total return (net):** 0.070600
- **Max drawdown:** -0.073906
- **Longs:** 103
- **Shorts:** 280

## Baseline Comparison

- **Best baseline:** `random_seed_4`
- **Best baseline return (net):** 0.122929
- **Excess over best baseline:** -0.052329

## Baselines Detail

- `always_long`: trades=400, win_rate=0.4650, return_net=-0.107138
- `always_short`: trades=400, win_rate=0.5350, return_net=-0.052862
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=400, win_rate=0.4925, return_net=-0.066487

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
