# RAGD API Reference

Endpoints:

- `GET /health`
- `POST /index` with `{"paths":["/path"]}`
- `POST /query` with `{"query":"text","mode":"hybrid","limit":10}`
- `GET /handoff`
- `POST /session/start`
- `POST /session/end`
- `POST /session/touch`
- `POST /memory/decision`
- `GET /memory/decisions`
- `GET /todos`
- `POST /todos`
- `GET /todos/search?q=text`
- `GET /metrics`
- `GET /mcp`
- `POST /mcp`

Responses are JSON. Errors are still basic in the MVP and should be hardened next.
