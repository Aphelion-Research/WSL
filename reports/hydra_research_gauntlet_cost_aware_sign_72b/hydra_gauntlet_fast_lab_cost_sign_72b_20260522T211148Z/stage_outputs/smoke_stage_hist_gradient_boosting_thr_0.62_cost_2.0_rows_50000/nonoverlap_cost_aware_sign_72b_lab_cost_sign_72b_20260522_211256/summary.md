# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_cost_aware_sign_72b_lab_cost_sign_72b_20260522_211256`
- **Verdict:** `NO_EDGE`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_72b.parquet`
- **Label:** `lab_cost_sign_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.62
- **Cost:** 2.0 bps
- **Runtime:** 25.93s

## Model Results

- **Trade count:** 431
- **Win rate:** 0.5290
- **Avg trade return (net):** 0.000017
- **Total return (gross):** 0.093385
- **Total return (net):** 0.007185
- **Max drawdown:** -0.101288
- **Longs:** 105
- **Shorts:** 326

## Baseline Comparison

- **Best baseline:** `random_seed_2`
- **Best baseline return (net):** 0.052593
- **Excess over best baseline:** -0.045408

## Baselines Detail

- `always_long`: trades=436, win_rate=0.4748, return_net=-0.140202
- `always_short`: trades=436, win_rate=0.5252, return_net=-0.034198
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=436, win_rate=0.4977, return_net=-0.011373

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
