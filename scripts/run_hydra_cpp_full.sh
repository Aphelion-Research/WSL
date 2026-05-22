#!/bin/bash
# Run HYDRA C++ fast training (full, 8-core)

set -e

echo "Running HYDRA C++ full training (8 threads)..."

OMP_NUM_THREADS=8 ./build/hydra_288b_fast_train \
    --data-dir data/hydra_binary_288b \
    --folds 5 \
    --horizon 288 \
    --commission-per-lot 5.0 \
    --lot-size 1.0 \
    --threads 8 \
    --parallel-mode inner \
    --verbose \
    --progress-jsonl reports/hydra_cpp_288b_progress.jsonl \
    --output-csv runs/hydra_cpp_288b_results.csv \
    2>&1 | tee reports/hydra_cpp_288b_full.log

echo ""
echo "Full training complete. Check:"
echo "  runs/hydra_cpp_288b_results.csv"
echo "  reports/hydra_cpp_288b_summary.json"
echo "  reports/hydra_cpp_288b_full.log"
