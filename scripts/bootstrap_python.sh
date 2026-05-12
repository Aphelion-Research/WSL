#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f requirements.txt ]; then
  echo "Missing requirements.txt at repo root" >&2
  exit 2
fi

PY="${PYTHON:-python3}"

if [ ! -d .venv ]; then
  if ! "$PY" -c 'import venv' >/dev/null 2>&1; then
    echo "Python venv support is missing." >&2
    echo "Fix:" >&2
    echo "  sudo apt update && sudo apt install -y python3-venv" >&2
    exit 3
  fi
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
