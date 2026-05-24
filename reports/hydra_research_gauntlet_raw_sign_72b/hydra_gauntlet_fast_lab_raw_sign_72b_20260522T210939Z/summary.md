# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_lab_raw_sign_72b_20260522T210939Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T21:09:39.033107+00:00
- finished UTC: 2026-05-22T21:11:48.544036+00:00
- mode: `fast`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet`
- label/return/horizon: `lab_raw_sign_72b` / `fwd_ret_72b` / 72
- total configs run: 4

## Final verdict

- verdict: `SMOKE_ONLY_WEAK`
- next recommendation: `RUN_FULL_GAUNTLET`
- reason: Smoke produced at least one promoted candidate, but medium/full gates were not run in fast mode.

## Best config

- threshold: 0.65
- model: `hist_gradient_boosting`
- stage: `SMOKE_STAGE`
- cost: 2.0
- total_return_net: 0.111951
- excess_over_best_baseline: 0.109631
- win_rate: 0.5357
- max_drawdown: -0.108766
- trade_count: 448

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | 0.111951 | 0.109631 | -0.108766 | 448 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | 0.080808 | 0.078488 | -0.083885 | 440 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | 0.075934 | 0.073614 | -0.107925 | 459 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | 0.041346 | 0.039026 | -0.127532 | 453 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |

## Failed-gate analysis

- net negative: 0
- baseline dominated: 0
- too much drawdown: 1
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: True
- neighboring thresholds: `[{"threshold": 0.62, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": 0.04134584559412829, "excess_over_best_baseline": 0.039025911304298035}, {"threshold": 0.68, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": 0.08080841274825544, "excess_over_best_baseline": 0.07848847845842519}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

RUN_FULL_GAUNTLET
