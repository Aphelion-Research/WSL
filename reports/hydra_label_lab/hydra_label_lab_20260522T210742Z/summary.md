# HYDRA Label Design Lab Summary

## Run metadata

- run_id: `hydra_label_lab_20260522T210742Z`
- started UTC: 2026-05-22T21:07:42.739107+00:00
- finished UTC: 2026-05-22T21:07:59.128360+00:00
- source dataset: `data/hydra_xauusd_m5_master_clean.parquet`
- source rows loaded: 100000
- max rows: 100000

## Safety

- No files were written under data/.
- No canonical dataset was rebuilt.
- No training or gauntlet validation was run.
- Planned gauntlet commands include --dry-run.

## Candidates

| candidate | available | label | return | horizon | rows | positive_rate | nan_rate | mismatch | dataset |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| raw_sign_72b | True | lab_raw_sign_72b | fwd_ret_72b | 72 | 100000 | 0.4957 | 0.0000 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet |
| cost_aware_sign_72b | True | lab_cost_sign_72b | fwd_ret_72b | 72 | 95285 | 0.4951 | 0.0471 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_72b.parquet |
| stronger_cost_aware_sign_72b | True | lab_cost_sign_72b_5bps | fwd_ret_72b | 72 | 88224 | 0.4950 | 0.1178 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_72b.parquet |
| triple_barrier_aligned_72b | False | label_72b | tb_ret_72b | 72 | None | N/A | N/A | N/A | missing high/low/close columns |
| raw_sign_20b | True | lab_raw_sign_20b | fwd_ret_20b | 20 | 100000 | 0.5025 | 0.0000 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet |
| cost_aware_sign_20b | True | lab_cost_sign_20b | fwd_ret_20b | 20 | 89450 | 0.5029 | 0.1055 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_20b.parquet |
| stronger_cost_aware_sign_20b | True | lab_cost_sign_20b_5bps | fwd_ret_20b | 20 | 74435 | 0.5033 | 0.2556 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet |

## Planned gauntlet commands

- `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/planned_gauntlet_commands.sh`

## Recommendation

Use these datasets only as label-design experiments. Run the gauntlet manually and require baseline-beating non-overlap evidence before making any alpha claim.
