# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_standard_lab_cost_sign_20b_5bps_20260522T224320Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T22:43:20.192188+00:00
- finished UTC: 2026-05-22T22:58:03.173654+00:00
- mode: `standard`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet`
- label/return/horizon: `lab_cost_sign_20b_5bps` / `fwd_ret_20b` / 20
- total configs run: 30

## Final verdict

- verdict: `SMOKE_ONLY_WEAK`
- next recommendation: `TRY_NEW_LABEL_DESIGN`
- reason: Smoke candidates failed medium promotion. Given prior overlapping WEAK_EDGE, try label design before feature spam.

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
| 2 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.68 | 2.0 | -0.041858 | 0.085210 | -0.107639 | 966 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 3 | SMOKE_STAGE | hist_gradient_boosting | 0.72 | 2.0 | -0.046068 | 0.081000 | -0.081945 | 866 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 4 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.65 | 2.0 | -0.064378 | 0.062689 | -0.127384 | 1044 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 5 | SMOKE_STAGE | hist_gradient_boosting | 0.7 | 2.0 | -0.066201 | 0.060867 | -0.104593 | 923 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 6 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.72 | 2.0 | -0.070337 | 0.056731 | -0.132373 | 865 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 7 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.55 | 2.0 | -0.080101 | 0.046967 | -0.170317 | 1180 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 8 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.7 | 2.0 | -0.083421 | 0.043647 | -0.157489 | 913 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 9 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | -0.086106 | 0.040961 | -0.140515 | 1040 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 10 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | -0.086816 | 0.040251 | -0.138611 | 979 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |

## Failed-gate analysis

- net negative: 29
- baseline dominated: 3
- too much drawdown: 26
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[{"threshold": 0.58, "gate_status": "PROMOTED_TO_MEDIUM", "total_return_net": -0.1250065145269119, "excess_over_best_baseline": 0.0020611961950513513}]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

TRY_NEW_LABEL_DESIGN
