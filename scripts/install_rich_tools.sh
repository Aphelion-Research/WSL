#!/bin/bash
# Install Rich for HYDRA console

set -e

echo "Installing Rich..."

if [ -d ".venv" ]; then
    echo "Using .venv"
    .venv/bin/python -m pip install rich
elif command -v python3 &> /dev/null; then
    echo "Using python3 --user"
    python3 -m pip install --user rich
else
    echo "ERROR: No python3 found"
    exit 1
fi

echo "✓ Rich installed"
