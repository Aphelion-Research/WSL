#!/bin/bash
# SYSTEM OPTIMIZATION FOR MAX SPEED

set -e

echo "🚀 OPTIMIZING SYSTEM FOR TRAINING..."

# 1. CPU performance mode
if [ -d /sys/devices/system/cpu/cpu0/cpufreq ]; then
    echo "⚡ Setting CPU to performance mode..."
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || echo "  (need sudo)"
fi

# 2. Increase file descriptors
echo "📁 Increasing file descriptor limits..."
ulimit -n 65536 2>/dev/null || echo "  (already set)"

# 3. Disable swap (if RAM available)
FREE_RAM=$(free -g | awk '/^Mem:/{print $7}')
if [ "$FREE_RAM" -gt 8 ]; then
    echo "💾 Disabling swap (enough RAM)..."
    sudo swapoff -a 2>/dev/null || echo "  (need sudo)"
fi

# 4. Thread affinity
export OMP_NUM_THREADS=$(nproc)
export MKL_NUM_THREADS=$(nproc)
export OPENBLAS_NUM_THREADS=$(nproc)

# 5. Python optimizations
export PYTHONUNBUFFERED=1
export MALLOC_TRIM_THRESHOLD_=100000

echo "✅ System optimized"
echo "  CPUs: $(nproc)"
echo "  RAM: $(free -h | awk '/^Mem:/{print $2}')"
echo "  GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo 'none')"
