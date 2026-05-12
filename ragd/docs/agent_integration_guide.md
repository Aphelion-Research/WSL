# Agent Integration Guide

## Contract

Every agent should do four things:

1. Start by reading `GET /handoff`.
2. Register with `POST /session/start`.
3. During work, record file touches, decisions, TODOs, and warnings.
4. Before ending, call `POST /session/end` or MCP `ragd_handoff_write`.

This keeps the next agent from rediscovering context.

## Startup Script

```bash
source ~/Dominion/ragd/scripts/agent-init.sh codex
```

The script starts a session, exports `RAGD_SESSION_ID`, and prints handoff JSON.

## Good Handoff Notes

A useful handoff answers:

- What changed.
- What was intentionally left unfinished and why.
- The most dangerous or fragile thing known.
- The first action the next agent should take.
- TODOs created or resolved.

Example:

```text
Summary: Implemented watcher debounce and API session endpoints.
Handoff: WebSocket transport remains HTTP-backed only; next agent should decide whether to replace the HTTP stack or add websocketpp on a second port.
Danger: Do not index secrets/; the indexer ignore list intentionally skips it.
First: Run ctest and HTTP smoke before installing the service.
```

## Session Bus

Use warnings for dangerous findings and locks for advisory file coordination:

```bash
ragd-warn "Do not edit ragd/src/storage.cpp during migration"
curl -s -X POST "$RAGD_ENDPOINT/bus/publish" \
  -H 'Content-Type: application/json' \
  -d '{"topic":"ragd/src/storage.cpp","kind":"lock","message":"editing storage migration","session_id":"'"$RAGD_SESSION_ID"'","ttl":3600}'
```

Locks are advisory. Check them with `GET /bus/locks`.

## System Prompt Addition

Agents should include:

```text
At startup, read $RAGD_ENDPOINT/handoff and start a ragd session. Record important file touches, decisions, TODOs, and warnings. Before ending, write a concise handoff note with summary, unfinished work, risk, and first next action.
```
