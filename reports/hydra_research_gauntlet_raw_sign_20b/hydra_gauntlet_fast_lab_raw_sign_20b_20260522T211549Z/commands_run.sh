#!/usr/bin/env bash
set -euo pipefail

python -m py_compile scripts/validate_hydra_nonoverlap.py
python -m py_compile scripts/validate_hydra_signal.py
python3 scripts/validate_clean_dataset.py
python -m pytest tests/test_regime_leakage.py -q
python -m pytest -q ragd_embed/tests ragd_chunker/tests
python scripts/validate_hydra_nonoverlap.py --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet --label-column lab_raw_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --folds 2 --embargo-bars 288 --threshold 0.55 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_raw_sign_20b/hydra_gauntlet_fast_lab_raw_sign_20b_20260522T211549Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.55_cost_2.0_rows_50000 --max-rows 50000
python scripts/validate_hydra_nonoverlap.py --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet --label-column lab_raw_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --folds 2 --embargo-bars 288 --threshold 0.62 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_raw_sign_20b/hydra_gauntlet_fast_lab_raw_sign_20b_20260522T211549Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.62_cost_2.0_rows_50000 --max-rows 50000
python scripts/validate_hydra_nonoverlap.py --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet --label-column lab_raw_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --folds 2 --embargo-bars 288 --threshold 0.65 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_raw_sign_20b/hydra_gauntlet_fast_lab_raw_sign_20b_20260522T211549Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.65_cost_2.0_rows_50000 --max-rows 50000
python scripts/validate_hydra_nonoverlap.py --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet --label-column lab_raw_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --folds 2 --embargo-bars 288 --threshold 0.68 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_raw_sign_20b/hydra_gauntlet_fast_lab_raw_sign_20b_20260522T211549Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.68_cost_2.0_rows_50000 --max-rows 50000
