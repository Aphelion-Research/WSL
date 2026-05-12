# RAGD Architecture

RAGD is organized into small C++ modules:

- `Storage`: SQLite schema, WAL setup, chunks, FTS, todos, sessions, decisions.
- `Indexer`: recursive scanning, ignore rules, chunking, TODO extraction.
- `TodoEngine`: marker extraction and priority scoring.
- `BM25Engine`: SQLite FTS5 retrieval.
- `VectorStore`: deterministic TF cosine fallback.
- `RagEngine`: hybrid retrieval response assembly.
- `HttpApi`: local REST endpoints.
- `McpServer`: JSON-RPC tool foundation.
- `Watcher`: polling watcher MVP.

The daemon binds to `127.0.0.1:7474` by default.
