#!/bin/bash
# Build HYDRA C++ fast training (optimized for 8-core)

set -euo pipefail

echo "Building HYDRA C++ fast training (8-core optimized)..."

mkdir -p build reports runs

# Delete stale binary to prevent accidental execution
rm -f build/hydra_288b_fast_train

# Base flags
FLAGS="-O3 -march=native -std=c++20 -DNDEBUG"

# Try advanced flags
if g++ -mtune=native -E - </dev/null &>/dev/null; then
    FLAGS="$FLAGS -mtune=native"
fi

if g++ -funroll-loops -E - </dev/null &>/dev/null; then
    FLAGS="$FLAGS -funroll-loops"
fi

TMP_BIN="build/hydra_288b_fast_train.tmp"
rm -f "$TMP_BIN"

BUILD_SUCCESS=0
COMPILER_USED=""
FLAGS_USED=""

# Try g++ with OpenMP first (best option)
if g++ $FLAGS -fopenmp cpp/hydra_288b_fast_train.cpp -o "$TMP_BIN" 2>&1; then
    BUILD_SUCCESS=1
    COMPILER_USED="g++ $(g++ -dumpversion)"
    FLAGS_USED="$FLAGS -fopenmp"
# Try clang++ with OpenMP
elif command -v clang++ &> /dev/null && clang++ $FLAGS -fopenmp cpp/hydra_288b_fast_train.cpp -o "$TMP_BIN" 2>&1; then
    BUILD_SUCCESS=1
    COMPILER_USED="clang++ $(clang++ --version | head -1)"
    FLAGS_USED="$FLAGS -fopenmp"
# Try g++ with LTO, no OpenMP
elif g++ $FLAGS -flto cpp/hydra_288b_fast_train.cpp -o "$TMP_BIN" 2>&1; then
    BUILD_SUCCESS=1
    COMPILER_USED="g++ $(g++ -dumpversion)"
    FLAGS_USED="$FLAGS -flto"
    echo "  WARNING: Hot loops will not use all cores"
# Try clang++ with LTO, no OpenMP
elif command -v clang++ &> /dev/null && clang++ $FLAGS -flto cpp/hydra_288b_fast_train.cpp -o "$TMP_BIN" 2>&1; then
    BUILD_SUCCESS=1
    COMPILER_USED="clang++ $(clang++ --version | head -1)"
    FLAGS_USED="$FLAGS -flto"
    echo "  WARNING: Hot loops will not use all cores"
# Fallback basic g++
elif g++ $FLAGS cpp/hydra_288b_fast_train.cpp -o "$TMP_BIN" 2>&1; then
    BUILD_SUCCESS=1
    COMPILER_USED="g++ $(g++ -dumpversion)"
    FLAGS_USED="$FLAGS"
    echo "  WARNING: Hot loops will not use all cores"
# Fallback basic clang++
elif command -v clang++ &> /dev/null && clang++ $FLAGS cpp/hydra_288b_fast_train.cpp -o "$TMP_BIN" 2>&1; then
    BUILD_SUCCESS=1
    COMPILER_USED="clang++ $(clang++ --version | head -1)"
    FLAGS_USED="$FLAGS"
    echo "  WARNING: Hot loops will not use all cores"
fi

if [ "$BUILD_SUCCESS" -eq 0 ]; then
    echo "✗ Build failed - all compiler attempts failed"
    rm -f "$TMP_BIN"
    exit 1
fi

# Move tmp to final binary only if compile succeeded
mv "$TMP_BIN" build/hydra_288b_fast_train

echo "✓ Built successfully"
echo "  Compiler: $COMPILER_USED"
echo "  Flags: $FLAGS_USED"

# Verify binary is newer than source
SRC_MTIME=$(stat -c %Y cpp/hydra_288b_fast_train.cpp)
BIN_MTIME=$(stat -c %Y build/hydra_288b_fast_train)

echo "  Source mtime: $SRC_MTIME"
echo "  Binary mtime: $BIN_MTIME"

if [ "$BIN_MTIME" -lt "$SRC_MTIME" ]; then
    echo "✗ ERROR: Binary older than source (stale build)"
    rm -f build/hydra_288b_fast_train
    exit 1
fi

echo "✓ Binary freshness verified"

# Test binary
if ./build/hydra_288b_fast_train --help 2>&1 | grep -q "data-dir"; then
    echo "✓ Binary works"
else
    echo "  Binary test skipped"
fi

echo "✓ build/hydra_288b_fast_train ready"
