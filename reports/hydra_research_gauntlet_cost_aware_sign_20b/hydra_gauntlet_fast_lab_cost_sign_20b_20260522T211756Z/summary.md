# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_fast_lab_cost_sign_20b_20260522T211756Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T21:17:56.631689+00:00
- finished UTC: 2026-05-22T21:20:06.191425+00:00
- mode: `fast`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_20b.parquet`
- label/return/horizon: `lab_cost_sign_20b` / `fwd_ret_20b` / 20
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
- total_return_net: -0.065827
- excess_over_best_baseline: 0.094052
- win_rate: 0.5479
- max_drawdown: -0.162591
- trade_count: 1442

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | SMOKE_STAGE | hist_gradient_boosting | 0.55 | 2.0 | -0.065827 | 0.094052 | -0.162591 | 1442 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 2 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | -0.095390 | 0.064489 | -0.131645 | 1259 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | -0.098139 | 0.061740 | -0.131839 | 1170 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 4 | SMOKE_STAGE | hist_gradient_boosting | 0.62 | 2.0 | -0.139570 | 0.020309 | -0.191148 | 1334 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |

## Failed-gate analysis

- net negative: 4
- baseline dominated: 0
- too much drawdown: 4
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.62, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": -0.13957037568363248, "excess_over_best_baseline": 0.020308802867811643}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

RUN_FULL_GAUNTLET
