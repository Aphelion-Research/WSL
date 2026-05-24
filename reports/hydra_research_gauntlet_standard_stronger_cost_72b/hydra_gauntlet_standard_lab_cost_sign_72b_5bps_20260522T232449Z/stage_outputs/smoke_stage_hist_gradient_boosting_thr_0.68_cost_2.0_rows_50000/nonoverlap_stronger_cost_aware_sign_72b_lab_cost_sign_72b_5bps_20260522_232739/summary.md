# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_stronger_cost_aware_sign_72b_lab_cost_sign_72b_5bps_20260522_232739`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_72b.parquet`
- **Label:** `lab_cost_sign_72b_5bps`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.68
- **Cost:** 2.0 bps
- **Runtime:** 24.4s

## Model Results

- **Trade count:** 387
- **Win rate:** 0.5478
- **Avg trade return (net):** 0.000321
- **Total return (gross):** 0.201469
- **Total return (net):** 0.124069
- **Max drawdown:** -0.062517
- **Longs:** 108
- **Shorts:** 279

## Baseline Comparison

- **Best baseline:** `random_seed_4`
- **Best baseline return (net):** 0.122929
- **Excess over best baseline:** 0.001141

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
