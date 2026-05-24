# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_stronger_cost_aware_sign_20b_lab_cost_sign_20b_5bps_20260522_235121`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet`
- **Label:** `lab_cost_sign_20b_5bps`
- **Return column:** `fwd_ret_20b`
- **Horizon:** 20 bars
- **Threshold:** 0.62
- **Cost:** 2.0 bps
- **Runtime:** 12.08s

## Model Results

- **Trade count:** 1104
- **Win rate:** 0.5498
- **Avg trade return (net):** -0.000091
- **Total return (gross):** 0.120864
- **Total return (net):** -0.099936
- **Max drawdown:** -0.164109
- **Longs:** 499
- **Shorts:** 605

## Baseline Comparison

- **Best baseline:** `random_seed_9`
- **Best baseline return (net):** -0.127068
- **Excess over best baseline:** 0.027132

## Baselines Detail

- `always_long`: trades=1199, win_rate=0.5004, return_net=-0.253758
- `always_short`: trades=1199, win_rate=0.4996, return_net=-0.225842
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=1199, win_rate=0.4962, return_net=-0.279889

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
