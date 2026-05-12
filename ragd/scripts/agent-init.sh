#!/bin/bash
# AGENT INITIALIZATION - source this at the start of every coding session.
# Usage: source scripts/agent-init.sh [agent_name]

AGENT_NAME="${1:-unknown-agent}"
RAGD="${RAGD_ENDPOINT:-http://localhost:7474}"

echo "Starting agent session: $AGENT_NAME"

SESSION_ID=$(curl -sf -X POST "$RAGD/session/start" \
  -H "Content-Type: application/json" \
  -d "{\"agent_name\":\"$AGENT_NAME\",\"git_branch\":\"$(git branch --show-current 2>/dev/null || echo unknown)\"}" \
  | jq -r '.session_id')

export RAGD_SESSION_ID="$SESSION_ID"
echo "Session ID: $SESSION_ID"

echo "Loading project context..."
curl -sf "$RAGD/handoff" | jq '.'

echo ""
echo "Agent session initialized. RAGD_SESSION_ID=$SESSION_ID"
echo "Before ending, run: ragd-session-end \$RAGD_SESSION_ID 'summary' 'handoff note'"
