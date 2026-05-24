#!/usr/bin/env bash
set -euo pipefail
cd ~/Dominion

echo '======================================================================'
echo 'RUNNING raw_sign_72b'
echo '======================================================================'
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet --label-column lab_raw_sign_72b --return-column fwd_ret_72b --horizon-bars 72 --output-dir reports/hydra_research_gauntlet_raw_sign_72b

echo '======================================================================'
echo 'RUNNING cost_aware_sign_72b'
echo '======================================================================'
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_72b.parquet --label-column lab_cost_sign_72b --return-column fwd_ret_72b --horizon-bars 72 --output-dir reports/hydra_research_gauntlet_cost_aware_sign_72b

echo '======================================================================'
echo 'RUNNING stronger_cost_aware_sign_72b'
echo '======================================================================'
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_72b.parquet --label-column lab_cost_sign_72b_5bps --return-column fwd_ret_72b --horizon-bars 72 --output-dir reports/hydra_research_gauntlet_stronger_cost_aware_sign_72b

echo '======================================================================'
echo 'RUNNING raw_sign_20b'
echo '======================================================================'
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet --label-column lab_raw_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --output-dir reports/hydra_research_gauntlet_raw_sign_20b

echo '======================================================================'
echo 'RUNNING cost_aware_sign_20b'
echo '======================================================================'
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_20b.parquet --label-column lab_cost_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --output-dir reports/hydra_research_gauntlet_cost_aware_sign_20b

echo '======================================================================'
echo 'RUNNING stronger_cost_aware_sign_20b'
echo '======================================================================'
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet --label-column lab_cost_sign_20b_5bps --return-column fwd_ret_20b --horizon-bars 20 --output-dir reports/hydra_research_gauntlet_stronger_cost_aware_sign_20b

