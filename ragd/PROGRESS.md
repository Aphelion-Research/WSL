# RAGD Progress

Status: MVP foundation implemented and unit-tested.

Working:

- CMake C++17 build.
- SQLite runtime linking without system `sqlite3.h`.
- Storage schema, FTS, chunks, todos, sessions, decisions, bus messages.
- Indexer, TODO engine, BM25, vector fallback, hybrid response, HTTP API, MCP tools list/call.
- Eight unit tests currently pass.

Known limitations:

- SQLite compatibility declarations are local because `libsqlite3-dev` is not installed.
- Vector search is in-memory brute-force TF cosine fallback.
- Watcher is polling.
- Temporal/dead-zone advanced analysis is a structured MVP response, not full analysis.
