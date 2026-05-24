#!/usr/bin/env bash
set -euo pipefail

python -m py_compile scripts/validate_hydra_nonoverlap.py
python -m py_compile scripts/validate_hydra_signal.py
python3 scripts/validate_clean_dataset.py
python -m pytest tests/test_regime_leakage.py -q
python -m pytest -q ragd_embed/tests ragd_chunker/tests
python scripts/validate_hydra_nonoverlap.py --dataset data/hydra_xauusd_m5_master_clean.parquet --label-column label_72b --return-column fwd_ret_72b --horizon-bars 72 --folds 2 --embargo-bars 288 --threshold 0.55 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_fast/hydra_gauntlet_fast_label_72b_20260522T205714Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.55_cost_2.0_rows_50000 --max-rows 50000
python scripts/validate_hydra_nonoverlap.py --dataset data/hydra_xauusd_m5_master_clean.parquet --label-column label_72b --return-column fwd_ret_72b --horizon-bars 72 --folds 2 --embargo-bars 288 --threshold 0.62 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_fast/hydra_gauntlet_fast_label_72b_20260522T205714Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.62_cost_2.0_rows_50000 --max-rows 50000
python scripts/validate_hydra_nonoverlap.py --dataset data/hydra_xauusd_m5_master_clean.parquet --label-column label_72b --return-column fwd_ret_72b --horizon-bars 72 --folds 2 --embargo-bars 288 --threshold 0.65 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_fast/hydra_gauntlet_fast_label_72b_20260522T205714Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.65_cost_2.0_rows_50000 --max-rows 50000
python scripts/validate_hydra_nonoverlap.py --dataset data/hydra_xauusd_m5_master_clean.parquet --label-column label_72b --return-column fwd_ret_72b --horizon-bars 72 --folds 2 --embargo-bars 288 --threshold 0.68 --cost-bps 2.0 --model hist_gradient_boosting --output-dir reports/hydra_research_gauntlet_fast/hydra_gauntlet_fast_label_72b_20260522T205714Z/stage_outputs/smoke_stage_hist_gradient_boosting_thr_0.68_cost_2.0_rows_50000 --max-rows 50000
