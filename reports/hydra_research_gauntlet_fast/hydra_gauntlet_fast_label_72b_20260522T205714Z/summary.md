# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_label_72b_20260522T205714Z`
- git sha: `784d27b`
- started UTC: 2026-05-22T20:57:14.749782+00:00
- finished UTC: 2026-05-22T20:59:26.710715+00:00
- mode: `fast`
- dataset: `data/hydra_xauusd_m5_master_clean.parquet`
- label/return/horizon: `label_72b` / `fwd_ret_72b` / 72
- total configs run: 4

## Final verdict

- verdict: `NO_EDGE`
- next recommendation: `TRY_NEW_LABEL_DESIGN`
- reason: No smoke configs promoted. Positive net alone is insufficient; configs must beat the best baseline.

## Best config

- threshold: 0.55
- model: `hist_gradient_boosting`
- stage: `SMOKE_STAGE`
- cost: 2.0
- total_return_net: -0.004650
- excess_over_best_baseline: -0.085608
- win_rate: 0.4791
- max_drawdown: -0.092865
- trade_count: 455

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | -0.004650 | -0.085608 | -0.092865 | 455 | FAILED_GATE | NO_EDGE |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | -0.005314 | -0.086272 | -0.054459 | 395 | FAILED_GATE | NO_EDGE |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | -0.086536 | -0.167495 | -0.156322 | 434 | FAILED_GATE | NO_EDGE |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | -0.100901 | -0.181859 | -0.127899 | 422 | FAILED_GATE | NO_EDGE |

## Failed-gate analysis

- net negative: 4
- baseline dominated: 4
- too much drawdown: 2
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.62, "gate_status": "FAILED_GATE", "total_return_net": -0.08653600467462688, "excess_over_best_baseline": -0.16749462997794023}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

TRY_NEW_LABEL_DESIGN
