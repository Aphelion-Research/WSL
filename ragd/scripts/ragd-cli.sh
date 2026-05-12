#!/usr/bin/env bash
set -euo pipefail
endpoint="${RAGD_ENDPOINT:-http://localhost:7474}"
cmd="$(basename "$0")"
case "$cmd" in
  ragd-query) curl -s "$endpoint/query" -d "{\"query\":\"$*\",\"mode\":\"hybrid\",\"limit\":10}" ;;
  ragd-remember) curl -s "$endpoint/memory/decision" -d "{\"session_id\":\"cli\",\"text\":\"$*\"}" ;;
  ragd-todo|ragd-warn) curl -s "$endpoint/todos" -d "{\"text\":\"$*\",\"tag\":\"TODO\"}" ;;
  ragd-todos) curl -s "$endpoint/todos" ;;
  ragd-handoff) curl -s "$endpoint/handoff" ;;
  ragd-session-start) curl -s "$endpoint/session/start" -d "{\"agent\":\"${1:-agent}\"}" ;;
  ragd-session-end) curl -s "$endpoint/session/end" -d "{\"session_id\":\"${1:-}\"}" ;;
  *) echo "Unknown ragd cli command: $cmd" >&2; exit 2 ;;
esac
