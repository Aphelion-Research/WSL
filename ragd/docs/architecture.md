# RAGD Architecture

## System Diagram

```text
                    +--------------------+
                    |  coding agents     |
                    |  CLI / MCP / HTTP  |
                    +----------+---------+
                               |
                               v
+-----------+        +---------+---------+        +----------------+
| inotify   |------->| HTTP + MCP API    |------->| RagEngine      |
| watcher   |        | localhost:7474    |        | intent/router  |
+-----+-----+        +---------+---------+        +---+--------+---+
      |                        |                      |        |
      v                        v                      v        v
+-----+------+       +---------+---------+        +---+---+ +--+------+
| Indexer    |------>| SQLite WAL store  |<-------| BM25 | | Vector  |
| chunker    |       | chunks/FTS/memory |        | FTS5 | | TF-IDF  |
+-----+------+       +---------+---------+        +-------+ +---------+
      |                        |
      v                        v
+-----+------+       +---------+---------+
| TODO engine|       | handoff/session   |
+------------+       | bus/dead zones    |
                     +-------------------+
```

## Components

- `Watcher`: Linux inotify thread with 300 ms debounce. It registers recursive directory watches and falls back to polling if inotify is unavailable.
- `Indexer`: reads allowed text files, marks old chunks for the file deleted, then inserts fresh active chunks.
- `Chunker`: uses structured regex chunking. Python functions/classes/methods, C-like functions/classes, Markdown heading sections, and config top-level blocks become separate chunks. Unknown files use bounded block chunks.
- `TodoEngine`: extracts `TODO`, `FIXME`, `HACK`, `NOTE`, `BUG`, `OPTIMIZE`, `PERF`, `SECURITY`, `WARN`, and `DEPRECATED`, then assigns priority.
- `Storage`: SQLite WAL database. FTS5 backs BM25 search; other tables persist sessions, decisions, TODOs, bus messages, locks, dead-zone results, and chunk history.
- `RagEngine`: routes intent, recalls BM25 and vector candidates, applies reciprocal-rank fusion, and emits scored JSON results.
- `McpServer`: JSON-RPC 2.0 HTTP transport for native agent tool calls.

## Threading Model

- Main thread: owns HTTP server request handling.
- Watcher thread: receives inotify events, debounces changes, and calls the indexer.
- SQLite access is serialized by request flow and index transactions. The default deployment runs one daemon per user.

## Database Overview

```text
agent_sessions --< session_file_touches >-- files/chunks
agent_sessions --< decisions
agent_sessions --< todos
chunks         --< chunk_history
chunks         --< fts_chunks
bus_messages  -- file_locks
dead_zones
kv_store
```

The schema is created and migrated at daemon startup. Existing MVP databases are upgraded in place with additive columns.

## Embedding Pipeline

The production interface is pluggable. This build always has a zero-dependency TF cosine vector fallback, so retrieval still works without Ollama or an OpenAI-compatible endpoint. The config keeps the Ollama/OpenAI fields for deployment parity and future model-backed embeddings.
