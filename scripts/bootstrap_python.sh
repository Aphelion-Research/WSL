#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f requirements.txt ]; then
  echo "Missing requirements.txt at repo root" >&2
  exit 2
fi

PY="${PYTHON:-python3}"

if [ ! -d .venv ]; then
  "$PY" -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo
echo "Validate: research doctor"
./.venv/bin/python -m research_os.cli doctor

echo
echo "Validate: llm doctor"
./.venv/bin/python -m local_llm.cli doctor

echo
echo "Validate: pytest"
./.venv/bin/python -m pytest -q

echo
echo "Validate: domdata safety"
./.venv/bin/python domdata/check_no_trading.py

