# MCP Tools

Endpoint: `http://localhost:7474/mcp`, transport `http`.

## Tools

- `ragd_query`: `{ "q": "text", "top_k": 10, "mode": "hybrid" }`
- `ragd_remember`: `{ "kind": "decision|note|warning", "content": "text", "filepath": "optional", "tags": [] }`
- `ragd_todo_add`: `{ "content": "text", "kind": "FIXME", "priority": 2, "filepath": "optional", "line": 1 }`
- `ragd_todo_list`: `{ "priority_max": 3, "kind": "BUG", "limit": 20 }`
- `ragd_todo_resolve`: `{ "todo_id": 1, "resolution_note": "fixed" }`
- `ragd_handoff_read`: `{}`
- `ragd_handoff_write`: `{ "summary": "done", "handoff_note": "next steps", "session_id": "sess_x" }`
- `ragd_session_start`: `{ "agent_name": "claude-code" }`
- `ragd_temporal_query`: `{ "q": "architecture", "git_commit": "HEAD", "top_k": 5 }`
- `ragd_broadcast`: `{ "topic": "warnings", "kind": "warning", "message": "note", "session_id": "sess_x" }`
- `ragd_deadzone_report`: `{ "path": "/home/Martin/Dominion" }`

## Example Call

```bash
curl -s http://localhost:7474/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ragd_query","arguments":{"q":"agent handoff","top_k":3}}}'
```

## Claude Code

`.claude/mcp_config.json`:

```json
{
  "mcpServers": {
    "ragd": {
      "url": "http://localhost:7474/mcp",
      "transport": "http"
    }
  }
}
```

## Cursor

`.cursor/mcp.json` uses the same shape as the Claude config.

## Zed and Copilot-Compatible Wrappers

Use any MCP client that supports JSON-RPC over HTTP and point it at `/mcp`. For clients without HTTP MCP support, wrap calls with `curl` or the shell commands installed by `scripts/ragd-cli.sh`.

## MCP Methods

RAGD supports `initialize`, `tools/list`, `tools/call`, `prompts/list`, `prompts/get`, and `resources/list`.
