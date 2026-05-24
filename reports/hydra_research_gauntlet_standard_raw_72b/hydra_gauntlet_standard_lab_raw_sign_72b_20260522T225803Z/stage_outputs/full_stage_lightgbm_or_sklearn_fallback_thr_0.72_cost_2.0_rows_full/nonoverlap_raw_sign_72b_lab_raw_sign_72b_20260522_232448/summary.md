# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_raw_sign_72b_lab_raw_sign_72b_20260522_232448`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet`
- **Label:** `lab_raw_sign_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.72
- **Cost:** 2.0 bps
- **Runtime:** 65.02s

## Model Results

- **Trade count:** 933
- **Win rate:** 0.5295
- **Avg trade return (net):** 0.000176
- **Total return (gross):** 0.351235
- **Total return (net):** 0.164635
- **Max drawdown:** -0.123358
- **Longs:** 295
- **Shorts:** 638

## Baseline Comparison

- **Best baseline:** `random_seed_9`
- **Best baseline return (net):** 0.075381
- **Excess over best baseline:** 0.089254

## Baselines Detail

- `always_long`: trades=1156, win_rate=0.4706, return_net=-0.109009
- `always_short`: trades=1156, win_rate=0.4862, return_net=-0.353391
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=1156, win_rate=0.4974, return_net=-0.160671

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
