#!/bin/bash
# Run HYDRA C++ benchmark mode (8-core)

set -e

echo "Running HYDRA C++ benchmark (8 threads)..."

OMP_NUM_THREADS=8 ./build/hydra_288b_fast_train \
    --data-dir data/hydra_binary_288b \
    --threads 8 \
    --benchmark \
    --verbose \
    --progress-jsonl reports/hydra_cpp_288b_progress.jsonl \
    2>&1 | tee reports/hydra_cpp_288b_benchmark.log

echo ""
echo "Benchmark complete. Check:"
echo "  reports/hydra_cpp_288b_benchmark.log"
