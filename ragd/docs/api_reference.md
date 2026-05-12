# HTTP API Reference

Base URL: `http://localhost:7474`. Responses are JSON.

## Health

`GET /health`

Returns daemon status and metrics.

```bash
curl http://localhost:7474/health
```

## Index

`POST /index`

```json
{"path":"/home/Martin/Dominion","recursive":true,"force":false}
```

Returns `queued`, `chunks_indexed`, and `already_current`.

## Query

`POST /query`

```json
{"q":"handoff protocol","top_k":10,"mode":"hybrid"}
```

Modes: `hybrid`, `bm25`, `vector`, `keyword`, `auto`.

## Sessions

- `POST /session/start` with `agent_name`, `git_branch`, optional `parent_session`
- `POST /session/end` with `session_id`, `summary`, `handoff_note`, `status`
- `GET /session/active`
- `GET /session/:session_id`
- `POST /session/touch` with `session_id`, `filepath`, `action`, `note`

## Decisions

- `POST /memory/decision`
- `GET /memory/decisions?limit=20`

Decision body:

```json
{
  "session_id":"sess_x",
  "filepath":"src/file.cpp",
  "decision":"Use SQLite FTS5 for BM25.",
  "rationale":"It is local and reliable.",
  "alternatives":["external search service"],
  "tags":["storage"]
}
```

## TODOs

- `GET /todos?status=open&priority=2&kind=FIXME&limit=50`
- `POST /todos`
- `PATCH /todos/:id`
- `GET /todos/search?q=race+condition`

Add body:

```json
{"filepath":"src/file.cpp","line_number":12,"kind":"FIXME","content":"FIXME: handle retry failure","priority":2}
```

## Handoff

`GET /handoff`

Returns active TODOs, recent decisions, recent sessions, active warnings, dead zones, indexed paths, backend metadata, and version.

## Temporal

- `GET /temporal/commits?limit=20`
- `POST /temporal/query` with `q`, `git_commit`, `top_k`
- `GET /temporal/file-timeline?filepath=...`
- `GET /temporal/diff`
- `GET /temporal/chunk-diff`

Temporal storage is backed by `chunk_history` recorded during live indexing.

## Dead Zones

- `POST /deadzone/scan`
- `GET /deadzone/results?acknowledged=false`

The scanner currently runs inline and stores heuristic findings.

## Session Bus

- `POST /bus/publish`
- `GET /bus/messages?topic=warnings&since=0`
- `GET /bus/locks`

Publish body:

```json
{"topic":"warnings","kind":"warning","message":"file is fragile","session_id":"sess_x","ttl":3600}
```

## Graph

- `GET /graph/file-history/:filepath`
- `GET /graph/decision-chain/:chunk_id`
- `GET /graph/todo-blockers/:todo_id`
- `GET /graph/agent-timeline`
- `GET /graph/symbols?root=MyClass&depth=3`

## MCP

- `GET /mcp`
- `POST /mcp`

Example:

```bash
curl -s http://localhost:7474/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```
