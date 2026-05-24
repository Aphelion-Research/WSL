# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_lab_cost_sign_72b_20260522T211148Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T21:11:48.607557+00:00
- finished UTC: 2026-05-22T21:13:49.925315+00:00
- mode: `fast`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_72b.parquet`
- label/return/horizon: `lab_cost_sign_72b` / `fwd_ret_72b` / 72
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
- total_return_net: 0.043962
- excess_over_best_baseline: -0.008631
- win_rate: 0.5343
- max_drawdown: -0.082527
- trade_count: 423

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | 0.043962 | -0.008631 | -0.082527 | 423 | PROMOTED_TO_MEDIUM | NO_EDGE |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | 0.019533 | -0.033060 | -0.067396 | 427 | PROMOTED_TO_MEDIUM | NO_EDGE |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | 0.007185 | -0.045408 | -0.101288 | 431 | PROMOTED_TO_MEDIUM | NO_EDGE |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | -0.048386 | -0.100979 | -0.154418 | 434 | FAILED_GATE | NO_EDGE |

## Failed-gate analysis

- net negative: 1
- baseline dominated: 4
- too much drawdown: 1
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.65, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": 0.019532689139845554, "excess_over_best_baseline": -0.03305989258809221}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

RUN_FULL_GAUNTLET
