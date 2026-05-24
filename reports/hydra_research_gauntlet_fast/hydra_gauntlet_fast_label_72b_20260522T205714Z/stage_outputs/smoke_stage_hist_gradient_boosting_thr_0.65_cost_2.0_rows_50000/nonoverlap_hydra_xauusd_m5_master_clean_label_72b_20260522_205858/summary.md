# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_hydra_xauusd_m5_master_clean_label_72b_20260522_205858`
- **Verdict:** `NO_EDGE`
- **Dataset:** `data/hydra_xauusd_m5_master_clean.parquet`
- **Label:** `label_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.65
- **Cost:** 2.0 bps
- **Runtime:** 28.34s

## Model Results

- **Trade count:** 422
- **Win rate:** 0.5118
- **Avg trade return (net):** -0.000239
- **Total return (gross):** -0.016501
- **Total return (net):** -0.100901
- **Max drawdown:** -0.127899
- **Longs:** 142
- **Shorts:** 280

## Baseline Comparison

- **Best baseline:** `random_seed_5`
- **Best baseline return (net):** 0.080959
- **Excess over best baseline:** -0.181859

## Baselines Detail

- `always_long`: trades=458, win_rate=0.4476, return_net=-0.126013
- `always_short`: trades=458, win_rate=0.4956, return_net=-0.057187
- `momentum`: trades=0, win_rate=N/A, return_net=N/A
- `random_seed_0`: trades=458, win_rate=0.4847, return_net=-0.089264

## Leakage Controls

- Chronological expanding walk-forward folds only.
- Embargo gap enforced between train and test.
- Imputer, scaler, and model fit on train folds only.
- Non-overlapping trades: one position at a time, hold for horizon bars.
- Forward return used only at entry bar (no overlap accumulation).

## Execution Warning

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.
