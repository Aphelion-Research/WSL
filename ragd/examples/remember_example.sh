#!/usr/bin/env bash
set -euo pipefail
curl -s "${RAGD_ENDPOINT:-http://localhost:7474}/memory/decision" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"example","decision":"Use ragd for cross-agent handoff context.","rationale":"Agents need persistent local memory.","tags":["handoff","memory"]}' | jq .
