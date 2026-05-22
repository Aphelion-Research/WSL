#!/bin/bash
# Run HYDRA C++ fast training in smoke mode (8-core)

set -e

echo "Running HYDRA C++ smoke test (8 threads)..."

OMP_NUM_THREADS=8 ./build/hydra_288b_fast_train \
    --data-dir data/hydra_binary_288b \
    --threads 8 \
    --smoke \
    --verbose \
    --parallel-mode inner \
    --progress-jsonl reports/hydra_cpp_288b_progress.jsonl \
    --output-csv runs/hydra_cpp_288b_results.csv \
    2>&1 | tee reports/hydra_cpp_288b_smoke.log

echo ""
echo "Smoke test complete. Check:"
echo "  runs/hydra_cpp_288b_results.csv"
echo "  reports/hydra_cpp_288b_summary.json"
echo "  reports/hydra_cpp_288b_smoke.log"
