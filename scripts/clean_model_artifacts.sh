#!/bin/bash
# Clean all HYDRA model artifacts

set -e

echo "Cleaning HYDRA model artifacts..."

rm -f runs/models/hydra_long.bin
rm -f runs/models/hydra_long.bin.meta.json
rm -f runs/models/hydra_short.bin
rm -f runs/models/hydra_short.bin.meta.json

echo "✓ Model artifacts cleaned"
