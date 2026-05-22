#!/usr/bin/env bash
set -uo pipefail

ROOT="${ROOT:-$HOME/Dominion}"
cd "$ROOT" || exit 1

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="reports/lunch_battery_${STAMP}"
mkdir -p "$OUT"

echo "======================================================================"
echo "HYDRA LUNCH VALIDATION BATTERY"
echo "Started UTC: $(date -u)"
echo "Output dir: $OUT"
echo "======================================================================"

run_step() {
  local name="$1"
  shift

  echo
  echo "======================================================================"
  echo "STEP: $name"
  echo "UTC:  $(date -u)"
  echo "CMD:  $*"
  echo "======================================================================"

  local safe_name
  safe_name="$(echo "$name" | tr ' /:' '___' | tr -cd 'A-Za-z0-9_.-')"
  local log="$OUT/${safe_name}.log"

  "$@" 2>&1 | tee "$log"
  local code="${PIPESTATUS[0]}"

  echo "EXIT_CODE=$code" | tee -a "$log"
  if [[ "$code" -ne 0 ]]; then
    echo "❌ STEP FAILED: $name"
  else
    echo "✅ STEP PASSED: $name"
  fi

  return 0
}

echo "Git SHA: $(git rev-parse HEAD 2>/dev/null || echo UNKNOWN)" | tee "$OUT/git_state.txt"
git status --short | tee -a "$OUT/git_state.txt"

# 1. Syntax/help check for the signal harness.
run_step "01_py_compile_signal_harness" \
  python -m py_compile scripts/validate_hydra_signal.py

run_step "02_signal_harness_help" \
  python scripts/validate_hydra_signal.py --help

# 2. Dataset structural validation.
run_step "03_clean_master_structural_validation" \
  python3 scripts/validate_clean_dataset.py

# 3. Dataset builder contract tests.
run_step "04_dataset_matrix_builder_tests" \
  python3 -m pytest -q tests/dataset/test_matrix_builder.py

# 4. HMM leakage tests.
run_step "05_hmm_leakage_tests" \
  python -m pytest tests/test_regime_leakage.py -v

# 5. RAGD / chunker tests.
run_step "06_ragd_chunker_embed_tests" \
  python -m pytest -q ragd_embed/tests ragd_chunker/tests

# 6. No-trading safety scanner.
run_step "07_no_trading_scanner" \
  python3 domdata/check_no_trading.py

# 7. Return-stream and label audit.
run_step "08_label_return_stream_audit" \
  python3 - <<'PY'
import json
import pandas as pd
from pathlib import Path

path = "data/hydra_xauusd_m5_master_clean.parquet"
df = pd.read_parquet(path)
print(f"{path}: shape={df.shape}")

cols = [
    "label_6b", "label_12b", "label_24b", "label_72b", "label_144b", "label_288b",
    "fwd_ret_5b", "fwd_ret_20b", "fwd_ret_72b",
]
for col in cols:
    if col not in df.columns:
        print(f"\n{col}: MISSING")
        continue
    s = pd.to_numeric(df[col], errors="coerce").dropna()
    print(f"\n{col}")
    print(f"  count={len(s):,} unique={s.nunique():,}")
    print(f"  mean={s.mean():.8f} std={s.std():.8f}")
    print(f"  min={s.min():.8f} p01={s.quantile(0.01):.8f} p50={s.quantile(0.50):.8f} p99={s.quantile(0.99):.8f} max={s.max():.8f}")

schema = Path("data/hydra_xauusd_m5_master_schema.json")
if schema.exists():
    obj = json.loads(schema.read_text())
    labels = [c for c in obj.get("columns", []) if c.get("role") == "label"]
    print(f"\nschema_label_count={len(labels)}")
    print("first_20_schema_labels:")
    for item in labels[:20]:
        print(" ", item.get("name"), "allowed_for_training=", item.get("allowed_for_training"))
PY

# 8. Smoke PnL validation: 72-bar, 50K rows, 2 folds.
run_step "09_signal_smoke_72b_pnl_50k" \
  python scripts/validate_hydra_signal.py \
    --dataset data/hydra_xauusd_m5_master_clean.parquet \
    --label-column label_72b \
    --return-column fwd_ret_72b \
    --folds 2 \
    --embargo-bars 288 \
    --max-rows 50000 \
    --model hist_gradient_boosting \
    --progress-mode auto \
    --log-every-seconds 10 \
    --output-dir "$OUT/signal_72b_pnl_50k"

# 9. Medium PnL validation: 72-bar, 100K rows, 3 folds.
run_step "10_signal_medium_72b_pnl_100k" \
  python scripts/validate_hydra_signal.py \
    --dataset data/hydra_xauusd_m5_master_clean.parquet \
    --label-column label_72b \
    --return-column fwd_ret_72b \
    --folds 3 \
    --embargo-bars 288 \
    --max-rows 100000 \
    --model hist_gradient_boosting \
    --progress-mode auto \
    --log-every-seconds 10 \
    --output-dir "$OUT/signal_72b_pnl_100k"

# 10. Classification-only 288-bar sanity: 100K rows, 3 folds.
run_step "11_signal_medium_288b_classification_100k" \
  python scripts/validate_hydra_signal.py \
    --dataset data/hydra_xauusd_m5_master_clean.parquet \
    --label-column label_288b \
    --folds 3 \
    --embargo-bars 288 \
    --max-rows 100000 \
    --model hist_gradient_boosting \
    --progress-mode auto \
    --log-every-seconds 10 \
    --output-dir "$OUT/signal_288b_classification_100k"

# Optional full run. Disabled by default because it takes ~18 min.
if [[ "${RUN_FULL:-0}" == "1" ]]; then
  run_step "12_OPTIONAL_full_72b_pnl" \
    python scripts/validate_hydra_signal.py \
      --dataset data/hydra_xauusd_m5_master_clean.parquet \
      --label-column label_72b \
      --return-column fwd_ret_72b \
      --folds 5 \
      --embargo-bars 288 \
      --progress-mode auto \
      --log-every-seconds 20 \
      --output-dir "$OUT/signal_72b_pnl_full"
else
  echo
  echo "Skipping optional full run. To enable:"
  echo "RUN_FULL=1 scripts/run_hydra_lunch_battery.sh"
fi

echo
echo "======================================================================"
echo "BATTERY COMPLETE"
echo "Finished UTC: $(date -u)"
echo "Output dir: $OUT"
echo "======================================================================"

echo
echo "Summary files found:"
find "$OUT" -name "summary.md" -o -name "summary.json" -o -name "fold_results.csv" | sort

echo
echo "Quick summaries:"
while IFS= read -r f; do
  echo
  echo "----------------------------------------------------------------------"
  echo "$f"
  echo "----------------------------------------------------------------------"
  sed -n '1,80p' "$f"
done < <(find "$OUT" -name "summary.md" | sort)

echo
echo "Git status after battery:"
git status --short
