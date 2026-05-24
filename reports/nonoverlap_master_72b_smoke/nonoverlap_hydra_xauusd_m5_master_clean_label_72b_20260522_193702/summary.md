# HYDRA Non-Overlapping Event Validation

> WARNING: This is bar-return validation, NOT live execution. Does NOT model spread, slippage, partial fills, requotes, OHLC path risk, margin calls, swap costs, or broker execution mechanics. Results are an UPPER BOUND on real-world performance.

- **Run ID:** `nonoverlap_hydra_xauusd_m5_master_clean_label_72b_20260522_193702`
- **Verdict:** `NO_EDGE`
- **Dataset:** `data/hydra_xauusd_m5_master_clean.parquet`
- **Label:** `label_72b`
- **Return column:** `fwd_ret_72b`
- **Horizon:** 72 bars
- **Threshold:** 0.55
- **Cost:** 2.0 bps
- **Runtime:** 15.59s

## Model Results

- **Trade count:** 453
- **Win rate:** 0.5055
- **Avg trade return (net):** -0.000133
- **Total return (gross):** 0.030253
- **Total return (net):** -0.060347
- **Max drawdown:** -0.087418
- **Longs:** 193
- **Shorts:** 260

## Baseline Comparison

- **Best baseline:** `random_seed_5`
- **Best baseline return (net):** 0.080959
- **Excess over best baseline:** -0.141305

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
