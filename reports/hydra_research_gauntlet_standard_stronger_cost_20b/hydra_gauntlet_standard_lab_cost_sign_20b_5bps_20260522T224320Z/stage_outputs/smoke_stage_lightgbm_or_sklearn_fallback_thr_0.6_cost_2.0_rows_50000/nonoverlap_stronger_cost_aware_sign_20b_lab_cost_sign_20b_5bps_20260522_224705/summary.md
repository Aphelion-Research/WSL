# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_stronger_cost_aware_sign_20b_lab_cost_sign_20b_5bps_20260522_224705`
- **Verdict:** `NO_EDGE`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet`
- **Label:** `lab_cost_sign_20b_5bps`
- **Return column:** `fwd_ret_20b`
- **Horizon:** 20 bars
- **Threshold:** 0.6
- **Cost:** 2.0 bps
- **Runtime:** 11.15s

## Model Results

- **Trade count:** 1137
- **Win rate:** 0.5321
- **Avg trade return (net):** -0.000175
- **Total return (gross):** 0.027889
- **Total return (net):** -0.199511
- **Max drawdown:** -0.246643
- **Longs:** 518
- **Shorts:** 619

## Baseline Comparison

- **Best baseline:** `random_seed_9`
- **Best baseline return (net):** -0.127068
- **Excess over best baseline:** -0.072443

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
