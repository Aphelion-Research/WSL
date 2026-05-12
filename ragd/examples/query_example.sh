#!/usr/bin/env bash
set -euo pipefail
curl -s "${RAGD_ENDPOINT:-http://localhost:7474}/query" \
  -H "Content-Type: application/json" \
  -d '{"q":"agent handoff protocol","top_k":5,"mode":"hybrid"}' | jq .
