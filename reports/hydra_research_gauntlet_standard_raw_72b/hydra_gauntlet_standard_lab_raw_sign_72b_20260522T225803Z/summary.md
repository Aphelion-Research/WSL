# HYDRA Research Gauntlet Summary

## Run metadata

- run_id: `hydra_gauntlet_standard_lab_raw_sign_72b_20260522T225803Z`
- git sha: `40c9242`
- started UTC: 2026-05-22T22:58:03.243169+00:00
- finished UTC: 2026-05-22T23:24:49.053060+00:00
- mode: `standard`
- dataset: `reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet`
- label/return/horizon: `lab_raw_sign_72b` / `fwd_ret_72b` / 72
- total configs run: 36

## Final verdict

- verdict: `NEEDS_NEW_LABELS`
- next recommendation: `TRY_NEW_LABEL_DESIGN`
- reason: Medium candidates did not survive full non-overlap gates. Try aligning labels to raw-return PnL target.

## Best config

- threshold: 0.72
- model: `lightgbm_or_sklearn_fallback`
- stage: `MEDIUM_STAGE`
- cost: 2.0
- total_return_net: 0.129044
- excess_over_best_baseline: 0.093700
- win_rate: 0.5036
- max_drawdown: -0.116466
- trade_count: 838

## Top 10 leaderboard

| rank | stage | model | threshold | cost | net | excess | drawdown | trades | gate | verdict |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | MEDIUM_STAGE | lightgbm_or_sklearn_fallback | 0.72 | 2.0 | 0.129044 | 0.093700 | -0.116466 | 838 | PROMOTED_TO_FULL | WEAK_EDGE_NONOVERLAP |
| 2 | MEDIUM_STAGE | hist_gradient_boosting | 0.65 | 2.0 | 0.072987 | 0.037642 | -0.123226 | 959 | PROMOTED_TO_FULL | WEAK_EDGE_NONOVERLAP |
| 3 | MEDIUM_STAGE | hist_gradient_boosting | 0.58 | 2.0 | 0.054577 | 0.019233 | -0.123827 | 1019 | PROMOTED_TO_FULL | WEAK_EDGE_NONOVERLAP |
| 4 | MEDIUM_STAGE | lightgbm_or_sklearn_fallback | 0.55 | 2.0 | 0.045893 | 0.010549 | -0.137582 | 1031 | PROMOTED_TO_FULL | WEAK_EDGE_NONOVERLAP |
| 5 | MEDIUM_STAGE | hist_gradient_boosting | 0.62 | 2.0 | 0.038867 | 0.003523 | -0.145944 | 983 | PROMOTED_TO_FULL | WEAK_EDGE_NONOVERLAP |
| 6 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.68 | 2.0 | 0.119709 | 0.117390 | -0.078237 | 437 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 7 | SMOKE_STAGE | hist_gradient_boosting | 0.65 | 2.0 | 0.111951 | 0.109631 | -0.108766 | 448 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 8 | SMOKE_STAGE | hist_gradient_boosting | 0.7 | 2.0 | 0.098395 | 0.096075 | -0.076713 | 435 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 9 | SMOKE_STAGE | lightgbm_or_sklearn_fallback | 0.55 | 2.0 | 0.089082 | 0.086762 | -0.069090 | 458 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |
| 10 | SMOKE_STAGE | hist_gradient_boosting | 0.68 | 2.0 | 0.080808 | 0.078488 | -0.083885 | 440 | PROMOTED_TO_MEDIUM | WEAK_EDGE_NONOVERLAP |

## Failed-gate analysis

- net negative: 10
- baseline dominated: 13
- too much drawdown: 23
- too few trades: 0
- cost stress failed: 0
- subprocess errors: 0
- missing summaries: 0

## Cost stress results

No cost stress runs were eligible or executed.

## Stability analysis

- best result isolated: None
- neighboring thresholds: `[]`

## Warning

This is still bar-return validation, not broker/event-driven execution.
Production candidate requires separate broker/event-driven validation.

## Next recommendation

TRY_NEW_LABEL_DESIGN
