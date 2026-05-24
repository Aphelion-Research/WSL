# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_raw_sign_72b_lab_raw_sign_72b_20260522_230400`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet`
- **Label:** `lab_raw_sign_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.72
- **Cost:** 2.0 bps
- **Runtime:** 13.99s

## Model Results

- **Trade count:** 428
- **Win rate:** 0.5374
- **Avg trade return (net):** 0.000104
- **Total return (gross):** 0.129921
- **Total return (net):** 0.044321
- **Max drawdown:** -0.079138
- **Longs:** 97
- **Shorts:** 331

## Baseline Comparison

- **Best baseline:** `random_seed_9`
- **Best baseline return (net):** 0.002320
- **Excess over best baseline:** 0.042001

## Baselines Detail

- `always_long`: trades=460, win_rate=0.4543, return_net=-0.121046
- `always_short`: trades=460, win_rate=0.5022, return_net=-0.062954
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=460, win_rate=0.4913, return_net=-0.099717

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
