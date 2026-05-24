# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_lab_raw_sign_20b_20260522T211549Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T21:15:49.795682+00:00
- finished UTC: 2026-05-22T21:17:56.554446+00:00
- mode: `fast`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet`
- label/return/horizon: `lab_raw_sign_20b` / `fwd_ret_20b` / 20
- total configs run: 4

## Final verdict

- verdict: `SMOKE_ONLY_WEAK`
- next recommendation: `RUN_FULL_GAUNTLET`
- reason: Smoke produced at least one promoted candidate, but medium/full gates were not run in fast mode.

## Best config

- threshold: 0.55
- model: `hist_gradient_boosting`
- stage: `SMOKE_STAGE`
- cost: 2.0
- total_return_net: -0.163627
- excess_over_best_baseline: -0.013884
- win_rate: 0.4822
- max_drawdown: -0.191659
- trade_count: 1626

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | -0.163627 | -0.013884 | -0.191659 | 1626 | PROMOTED_TO_MEDIUM | NO_EDGE |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | -0.180727 | -0.030984 | -0.225817 | 1416 | FAILED_GATE | NO_EDGE |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | -0.196300 | -0.046557 | -0.228612 | 1508 | FAILED_GATE | NO_EDGE |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | -0.225415 | -0.075672 | -0.240473 | 1292 | FAILED_GATE | NO_EDGE |

## Failed-gate analysis

- net negative: 4
- baseline dominated: 4
- too much drawdown: 4
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.62, "gate_status": "FAILED_GATE", "total_return_net": -0.1962999833862445, "excess_over_best_baseline": -0.04655658585337408}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

RUN_FULL_GAUNTLET
