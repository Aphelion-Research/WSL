# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_raw_sign_72b_lab_raw_sign_72b_20260523_002132`
- **Verdict:** `NO_EDGE`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/raw_sign_72b.parquet`
- **Label:** `lab_raw_sign_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.65
- **Cost:** 2.0 bps
- **Runtime:** 40.08s

## Model Results

- **Trade count:** 952
- **Win rate:** 0.5063
- **Avg trade return (net):** -0.000083
- **Total return (gross):** 0.111439
- **Total return (net):** -0.078961
- **Max drawdown:** -0.170647
- **Longs:** 440
- **Shorts:** 512

## Baseline Comparison

- **Best baseline:** `random_seed_8`
- **Best baseline return (net):** 0.035344
- **Excess over best baseline:** -0.114305

## Baselines Detail

- `always_long`: trades=1040, win_rate=0.4654, return_net=-0.106743
- `always_short`: trades=1040, win_rate=0.4856, return_net=-0.309257
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=1040, win_rate=0.4875, return_net=-0.334732

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
