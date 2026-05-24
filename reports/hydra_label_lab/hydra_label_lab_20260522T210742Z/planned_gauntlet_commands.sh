#!/usr/bin/env bash
set -euo pipefail

# HYDRA label-lab planned commands.
# These are gauntlet dry-runs only. They do not execute validation.

# raw_sign_72b
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_72b.parquet --label-column lab_raw_sign_72b --return-column fwd_ret_72b --horizon-bars 72 --output-dir reports/hydra_research_gauntlet_raw_sign_72b --dry-run

# cost_aware_sign_72b
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_72b.parquet --label-column lab_cost_sign_72b --return-column fwd_ret_72b --horizon-bars 72 --output-dir reports/hydra_research_gauntlet_cost_aware_sign_72b --dry-run

# stronger_cost_aware_sign_72b
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_72b.parquet --label-column lab_cost_sign_72b_5bps --return-column fwd_ret_72b --horizon-bars 72 --output-dir reports/hydra_research_gauntlet_stronger_cost_aware_sign_72b --dry-run

# skipped triple_barrier_aligned_72b: missing high/low/close columns
# raw_sign_20b
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/raw_sign_20b.parquet --label-column lab_raw_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --output-dir reports/hydra_research_gauntlet_raw_sign_20b --dry-run

# cost_aware_sign_20b
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/cost_aware_sign_20b.parquet --label-column lab_cost_sign_20b --return-column fwd_ret_20b --horizon-bars 20 --output-dir reports/hydra_research_gauntlet_cost_aware_sign_20b --dry-run

# stronger_cost_aware_sign_20b
python scripts/hydra_research_gauntlet.py --mode fast --dataset reports/hydra_label_lab/hydra_label_lab_20260522T210742Z/datasets/stronger_cost_aware_sign_20b.parquet --label-column lab_cost_sign_20b_5bps --return-column fwd_ret_20b --horizon-bars 20 --output-dir reports/hydra_research_gauntlet_stronger_cost_aware_sign_20b --dry-run
