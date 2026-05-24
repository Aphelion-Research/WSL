# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_raw_sign_20b_lab_raw_sign_20b_20260522_211701`
- **Verdict:** `NO_EDGE`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet`
- **Label:** `lab_raw_sign_20b`
- **Return column:** `fwd_ret_20b`
- **Horizon:** 20 bars
- **Threshold:** 0.62
- **Cost:** 2.0 bps
- **Runtime:** 27.68s

## Model Results

- **Trade count:** 1508
- **Win rate:** 0.4821
- **Avg trade return (net):** -0.000130
- **Total return (gross):** 0.105300
- **Total return (net):** -0.196300
- **Max drawdown:** -0.228612
- **Longs:** 517
- **Shorts:** 991

## Baseline Comparison

- **Best baseline:** `random_seed_4`
- **Best baseline return (net):** -0.149743
- **Excess over best baseline:** -0.046557

## Baselines Detail

- `always_long`: trades=1653, win_rate=0.4301, return_net=-0.359738
- `always_short`: trades=1653, win_rate=0.4428, return_net=-0.301462
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=1653, win_rate=0.4374, return_net=-0.367864

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
