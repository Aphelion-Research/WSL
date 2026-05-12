# RAGD MCP Tools

Implemented MCP tool names:

- `ragd_query`
- `ragd_remember`
- `ragd_todo_add`
- `ragd_todo_list`
- `ragd_todo_resolve`
- `ragd_handoff_read`
- `ragd_handoff_write`
- `ragd_session_start`
- `ragd_broadcast`
- `ragd_deadzone_report`
- `ragd_temporal_query`

MVP endpoint:

```bash
curl http://localhost:7474/mcp
curl -s http://localhost:7474/mcp -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
