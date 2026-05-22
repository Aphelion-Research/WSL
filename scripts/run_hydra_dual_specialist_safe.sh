#!/bin/bash
# Safe dual-specialist run with build verification

set -euo pipefail

cd ~/Dominion

echo "================================"
echo "HYDRA Dual-Specialist Safe Run"
echo "================================"

# Build
echo ""
echo "[1/4] Building C++ binary..."
if ! bash scripts/build_hydra_cpp.sh; then
    echo "✗ Build failed - aborting"
    exit 1
fi

# Verify binary exists and is executable
if [ ! -f build/hydra_288b_fast_train ]; then
    echo "✗ Binary missing after build - aborting"
    exit 1
fi

if [ ! -x build/hydra_288b_fast_train ]; then
    echo "✗ Binary not executable - aborting"
    exit 1
fi

echo "✓ Binary ready"

# Clean output CSVs
echo ""
echo "[2/4] Cleaning output CSVs..."
rm -f runs/hydra_dual_specialist_results.csv
rm -f runs/hydra_cpp_288b_results.csv
rm -f runs/hydra_cpp_288b_trades.csv
rm -f runs/hydra_cpp_288b_oos_equity.csv
echo "✓ CSVs cleaned"

# Run dual-specialist
echo ""
echo "[3/4] Running dual-specialist inference..."

OMP_NUM_THREADS=8 ./build/hydra_288b_fast_train \
  --data-dir data/hydra_binary_288b \
  --threads 8 \
  --horizon 288 \
  --split-mode train-oos \
  --train-years 10 \
  --oos-years 1 \
  --direction-mode dual-specialist \
  --load-long-model runs/models/hydra_long.bin \
  --load-short-model runs/models/hydra_short.bin \
  --dual-combiner edge \
  --min-edge-gap 0.0 \
  --starting-balance 10000 \
  --leverage 50 \
  --max-loss-pct 0.06 \
  --hard-stop-on-drawdown \
  --lot-size 0.01 \
  --max-open-positions 1 \
  --max-holding-bars 288 \
  --require-bracket-orders \
  --allow-long \
  --allow-short \
  --allow-close-and-reverse \
  --min-long-confidence 0.02 \
  --min-short-confidence 0.02 \
  --confidence-rr \
  --min-rr 1.0 \
  --max-rr 3.0 \
  --risk-per-trade-pct 0.00010 \
  --trailing-stop \
  --trail-activate-r 1.0 \
  --trail-distance-r 0.5 \
  --move-sl-to-breakeven-at-r 1.0 \
  --normalize-features \
  --calibrate-proba \
  --regime-filter \
  --objective excess_utility \
  --reject-constant-proba \
  --max-saturation-rate 0.95 \
  --min-proba-std 0.001 \
  --min-confidence 0.02 \
  --verbose \
  2>&1 | tee reports/hydra_dual_specialist_audit.log

echo "✓ Inference complete"

# Verify CSV outputs
echo ""
echo "[4/4] Verifying CSV outputs..."

if [ ! -f runs/hydra_dual_specialist_results.csv ]; then
    echo "✗ Dual results CSV missing"
    exit 1
fi

if [ ! -f runs/hydra_cpp_288b_trades.csv ]; then
    echo "✗ Trades CSV missing"
    exit 1
fi

# Count result rows (excluding header)
RESULT_ROWS=$(tail -n +2 runs/hydra_dual_specialist_results.csv | wc -l)
if [ "$RESULT_ROWS" -ne 1 ]; then
    echo "✗ Dual results CSV must have exactly 1 data row, found $RESULT_ROWS"
    exit 1
fi

# Verify header/row column count match
HEADER_COLS=$(head -1 runs/hydra_dual_specialist_results.csv | tr ',' '\n' | wc -l)
ROW_COLS=$(tail -1 runs/hydra_dual_specialist_results.csv | tr ',' '\n' | wc -l)
if [ "$HEADER_COLS" -ne "$ROW_COLS" ]; then
    echo "✗ Dual results CSV schema mismatch: header=$HEADER_COLS row=$ROW_COLS"
    exit 1
fi

# Count trade rows (excluding header)
TRADE_ROWS=$(tail -n +2 runs/hydra_cpp_288b_trades.csv | wc -l)
if [ "$TRADE_ROWS" -lt 1 ]; then
    echo "✗ Trades CSV has no data rows"
    exit 1
fi

# Check direction column exists and not None
if ! head -1 runs/hydra_cpp_288b_trades.csv | grep -q "direction"; then
    echo "✗ Trades CSV missing direction column"
    exit 1
fi

# Check for None in direction column (indicates misaligned CSV)
if tail -n +2 runs/hydra_cpp_288b_trades.csv | cut -d',' -f5 | grep -q "None"; then
    echo "✗ Trades CSV has None in direction column (misaligned)"
    exit 1
fi

# Extract total_trades from dual results
TOTAL_TRADES=$(tail -1 runs/hydra_dual_specialist_results.csv | cut -d',' -f16)
if [ "$TRADE_ROWS" -ne "$TOTAL_TRADES" ]; then
    echo "✗ Trade count mismatch: CSV has $TRADE_ROWS rows but result says $TOTAL_TRADES"
    exit 1
fi

echo "✓ CSV verification passed"
echo "  Result rows: $RESULT_ROWS (header=$HEADER_COLS cols, row=$ROW_COLS cols)"
echo "  Trade rows: $TRADE_ROWS (matches total_trades=$TOTAL_TRADES)"

echo ""
echo "================================"
echo "✓ Dual-specialist run complete"
echo "================================"
echo ""
echo "Next: python3 scripts/verify_direction_results.py"
