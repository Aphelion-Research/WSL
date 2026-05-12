# Agent Integration Guide

Agents should:

1. Start a session through `/session/start` or MCP `ragd_session_start`.
2. Touch important files with `/session/touch`.
3. Store durable decisions with `/memory/decision`.
4. Query context with `/query`.
5. Read `/handoff` before taking over from another agent.
6. End sessions with `/session/end`.

Do not send secrets to RAGD. Do not index `secrets/`, raw market data, normalized Parquet, `.venv`, `build`, or `node_modules`.
