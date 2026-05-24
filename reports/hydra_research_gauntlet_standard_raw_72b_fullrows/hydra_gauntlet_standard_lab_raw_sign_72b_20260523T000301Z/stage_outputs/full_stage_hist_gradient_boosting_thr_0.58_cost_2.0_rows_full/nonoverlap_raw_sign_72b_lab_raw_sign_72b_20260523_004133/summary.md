# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_raw_sign_72b_lab_raw_sign_72b_20260523_004133`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/raw_sign_72b.parquet`
- **Label:** `lab_raw_sign_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.58
- **Cost:** 2.0 bps
- **Runtime:** 1121.16s

## Model Results

- **Trade count:** 8520
- **Win rate:** 0.5418
- **Avg trade return (net):** 0.000487
- **Total return (gross):** 5.850518
- **Total return (net):** 4.146518
- **Max drawdown:** -0.374303
- **Longs:** 4694
- **Shorts:** 3826

## Baseline Comparison

- **Best baseline:** `always_long`
- **Best baseline return (net):** -0.000580
- **Excess over best baseline:** 4.147098

## Baselines Detail

- `always_long`: trades=9056, win_rate=0.4977, return_net=-0.000580
- `always_short`: trades=9056, win_rate=0.4526, return_net=-3.621820
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=9056, win_rate=0.4790, return_net=-2.260130

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
