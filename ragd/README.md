# RAGD

RAGD is a C++17 persistent retrieval and agent-memory daemon for Dominion.

Current MVP:

- SQLite storage with WAL and FTS5.
- Recursive file indexing with ignore rules.
- Markdown/code chunking using pragmatic heuristics.
- TODO extraction and priority scoring.
- BM25/FTS retrieval.
- TF-style vector fallback and hybrid retrieval foundation.
- Agent sessions, file touches, decisions, handoff JSON.
- HTTP API and MCP JSON-RPC endpoint foundation.
- Polling watcher interface.

Build:

```bash
cmake -S ~/Dominion/ragd -B ~/Dominion/ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ~/Dominion/ragd/build -j$(nproc)
cd ~/Dominion/ragd/build && ctest --output-on-failure
```

Run:

```bash
~/Dominion/ragd/build/ragd --db ~/.ragd/ragd.sqlite --path ~/Dominion/docs
```

Deferred honestly:

- Tree-sitter symbol graph.
- HNSW vector index.
- Git temporal indexing.
- WebSocket session bus.
