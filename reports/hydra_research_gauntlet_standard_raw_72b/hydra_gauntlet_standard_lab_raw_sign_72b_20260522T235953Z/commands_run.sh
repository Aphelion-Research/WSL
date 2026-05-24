#!/usr/bin/env bash
set -euo pipefail

python -m py_compile scripts/validate_hydra_nonoverlap.py
python -m py_compile scripts/validate_hydra_signal.py
python3 scripts/validate_clean_dataset.py
