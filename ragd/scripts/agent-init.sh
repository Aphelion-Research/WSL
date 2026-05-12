#!/usr/bin/env bash
set -euo pipefail
endpoint="${RAGD_ENDPOINT:-http://localhost:7474}"
curl -s "$endpoint/session/start" -d "{\"agent\":\"${1:-codex}\"}"
echo
curl -s "$endpoint/handoff"
echo
