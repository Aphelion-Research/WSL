# HYDRA Label Design Lab Summary

## Run metadata

- run_id: `hydra_label_lab_20260523T000144Z`
- started UTC: 2026-05-23T00:01:44.351203+00:00
- finished UTC: 2026-05-23T00:03:01.293061+00:00
- source dataset: `data/hydra_xauusd_m5_master_clean.parquet`
- source rows loaded: 782825
- max rows: full

## Safety

- No files were written under data/.
- No canonical dataset was rebuilt.
- No training or gauntlet validation was run.
- Planned gauntlet commands include --dry-run.

## Candidates

| candidate | available | label | return | horizon | rows | positive_rate | nan_rate | mismatch | dataset |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| raw_sign_72b | True | lab_raw_sign_72b | fwd_ret_72b | 72 | 782685 | 0.5174 | 0.0000 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/raw_sign_72b.parquet |
| cost_aware_sign_72b | True | lab_cost_sign_72b | fwd_ret_72b | 72 | 743724 | 0.5185 | 0.0499 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/cost_aware_sign_72b.parquet |
| stronger_cost_aware_sign_72b | True | lab_cost_sign_72b_5bps | fwd_ret_72b | 72 | 686133 | 0.5202 | 0.1235 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/stronger_cost_aware_sign_72b.parquet |
| triple_barrier_aligned_72b | False | label_72b | tb_ret_72b | 72 | None | N/A | N/A | N/A | missing high/low/close columns |
| raw_sign_20b | True | lab_raw_sign_20b | fwd_ret_20b | 20 | 782794 | 0.5132 | 0.0000 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/raw_sign_20b.parquet |
| cost_aware_sign_20b | True | lab_cost_sign_20b | fwd_ret_20b | 20 | 697562 | 0.5151 | 0.1089 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/cost_aware_sign_20b.parquet |
| stronger_cost_aware_sign_20b | True | lab_cost_sign_20b_5bps | fwd_ret_20b | 20 | 578277 | 0.5167 | 0.2613 | 0.0000 | reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/datasets/stronger_cost_aware_sign_20b.parquet |

## Planned gauntlet commands

- `reports/hydra_label_lab/hydra_label_lab_20260523T000144Z/planned_gauntlet_commands.sh`

## Recommendation

Use these datasets only as label-design experiments. Run the gauntlet manually and require baseline-beating non-overlap evidence before making any alpha claim.
