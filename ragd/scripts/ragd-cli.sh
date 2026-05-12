#!/usr/bin/env bash
set -euo pipefail

endpoint="${RAGD_ENDPOINT:-http://localhost:7474}"
cmd="$(basename "$0")"

json_string() {
  if command -v jq >/dev/null 2>&1; then
    jq -Rn --arg v "$1" '$v'
  else
    printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
  fi
}

post_json() {
  local path="$1"
  local payload="$2"
  curl -sf -X POST "$endpoint$path" -H "Content-Type: application/json" -d "$payload"
}

case "$cmd" in
  ragd-query)
    q="$(json_string "$*")"
    post_json /query "{\"q\":$q,\"mode\":\"hybrid\",\"top_k\":10}"
    ;;
  ragd-remember)
    content="$(json_string "$*")"
    post_json /memory/decision "{\"session_id\":\"${RAGD_SESSION_ID:-cli}\",\"decision\":$content}"
    ;;
  ragd-todo)
    priority=5
    text=()
    while [ "$#" -gt 0 ]; do
      case "$1" in
        --priority) priority="${2:-5}"; shift 2 ;;
        *) text+=("$1"); shift ;;
      esac
    done
    content="$(json_string "${text[*]}")"
    post_json /todos "{\"filepath\":\"manual\",\"kind\":\"TODO\",\"content\":$content,\"priority\":$priority,\"session_id\":\"${RAGD_SESSION_ID:-cli}\"}"
    ;;
  ragd-handoff)
    curl -sf "$endpoint/handoff"
    ;;
  ragd-warn)
    message="$(json_string "$*")"
    post_json /bus/publish "{\"topic\":\"warnings\",\"kind\":\"warning\",\"message\":$message,\"session_id\":\"${RAGD_SESSION_ID:-cli}\"}"
    ;;
  ragd-todos)
    curl -sf "$endpoint/todos?status=open&limit=100"
    ;;
  ragd-session-start)
    agent="$(json_string "${1:-unknown-agent}")"
    branch="$(json_string "$(git branch --show-current 2>/dev/null || echo unknown)")"
    post_json /session/start "{\"agent_name\":$agent,\"git_branch\":$branch}"
    ;;
  ragd-session-end)
    session="${1:-${RAGD_SESSION_ID:-}}"
    summary_text="${2:-session ended from CLI}"
    handoff_text="${3:-$summary_text}"
    summary="$(json_string "$summary_text")"
    handoff="$(json_string "$handoff_text")"
    post_json /session/end "{\"session_id\":\"$session\",\"summary\":$summary,\"handoff_note\":$handoff,\"status\":\"completed\"}"
    ;;
  *)
    echo "Unknown ragd cli command: $cmd" >&2
    exit 2
    ;;
esac
