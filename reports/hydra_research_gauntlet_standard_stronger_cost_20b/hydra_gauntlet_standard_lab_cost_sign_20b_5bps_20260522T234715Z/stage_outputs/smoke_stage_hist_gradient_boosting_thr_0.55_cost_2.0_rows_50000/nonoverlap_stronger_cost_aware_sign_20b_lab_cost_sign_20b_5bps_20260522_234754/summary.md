# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_stronger_cost_aware_sign_20b_lab_cost_sign_20b_5bps_20260522_234754`
- **Verdict:** `WEAK_EDGE_NONOVERLAP`
- **Dataset:** `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet`
- **Label:** `lab_cost_sign_20b_5bps`
- **Return column:** `fwd_ret_20b`
- **Horizon:** 20 bars
- **Threshold:** 0.55
- **Cost:** 2.0 bps
- **Runtime:** 21.91s

## Model Results

- **Trade count:** 1177
- **Win rate:** 0.5650
- **Avg trade return (net):** 0.000014
- **Total return (gross):** 0.251526
- **Total return (net):** 0.016126
- **Max drawdown:** -0.115797
- **Longs:** 533
- **Shorts:** 644

## Baseline Comparison

- **Best baseline:** `random_seed_9`
- **Best baseline return (net):** -0.127068
- **Excess over best baseline:** 0.143194

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
