# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_lab_cost_sign_72b_5bps_20260522T211349Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T21:13:49.990968+00:00
- finished UTC: 2026-05-22T21:15:49.729054+00:00
- mode: `fast`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_72b.parquet`
- label/return/horizon: `lab_cost_sign_72b_5bps` / `fwd_ret_72b` / 72
- total configs run: 4

## Final verdict

- verdict: `SMOKE_ONLY_WEAK`
- next recommendation: `RUN_FULL_GAUNTLET`
- reason: Smoke produced at least one promoted candidate, but medium/full gates were not run in fast mode.

## Best config

- threshold: 0.68
- model: `hist_gradient_boosting`
- stage: `SMOKE_STAGE`
- cost: 2.0
- total_return_net: 0.124069
- excess_over_best_baseline: 0.001141
- win_rate: 0.5478
- max_drawdown: -0.062517
- trade_count: 387

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | 0.124069 | 0.001141 | -0.062517 | 387 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | 0.066581 | -0.056348 | -0.110864 | 391 | PROMOTED_TO_MEDIUM | NO_EDGE |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | 0.030866 | -0.092063 | -0.073741 | 396 | PROMOTED_TO_MEDIUM | NO_EDGE |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | 0.005652 | -0.117277 | -0.077110 | 399 | PROMOTED_TO_MEDIUM | NO_EDGE |

## Failed-gate analysis

- net negative: 0
- baseline dominated: 3
- too much drawdown: 0
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.65, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": 0.06658101493426496, "excess_over_best_baseline": -0.056347662770356716}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

RUN_FULL_GAUNTLET
