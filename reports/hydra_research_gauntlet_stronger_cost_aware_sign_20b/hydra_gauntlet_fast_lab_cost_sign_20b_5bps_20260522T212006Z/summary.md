# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_lab_cost_sign_20b_5bps_20260522T212006Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T21:20:06.257142+00:00
- finished UTC: 2026-05-22T21:22:37.339892+00:00
- mode: `fast`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet`
- label/return/horizon: `lab_cost_sign_20b_5bps` / `fwd_ret_20b` / 20
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
- total_return_net: 0.016126
- excess_over_best_baseline: 0.143194
- win_rate: 0.5650
- max_drawdown: -0.115797
- trade_count: 1177

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | 0.016126 | 0.143194 | -0.115797 | 1177 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | -0.086106 | 0.040961 | -0.140515 | 1040 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | -0.086816 | 0.040251 | -0.138611 | 979 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | -0.131432 | -0.004364 | -0.195449 | 1099 | PROMOTED_TO_MEDIUM | NO_EDGE |

## Failed-gate analysis

- net negative: 3
- baseline dominated: 1
- too much drawdown: 3
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.62, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": -0.13143200186310441, "excess_over_best_baseline": -0.0043642911411411744}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

RUN_FULL_GAUNTLET
