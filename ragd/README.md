# ragd

`ragd` is the Dominion local RAG daemon: a C++17 background service that indexes project files, extracts TODOs, stores agent handoffs, and exposes the shared knowledge base over HTTP and MCP.

It exists so a new coding agent can start with the current project memory instead of rediscovering decisions, fragile areas, open TODOs, and recent session context.

## Quick Start

```bash
cd ~/Dominion/ragd
./install.sh
curl http://localhost:7474/health
ragd-query "how does the handoff protocol work"
source scripts/agent-init.sh codex
```

For a local developer build without installing:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
./build/ragd --config scripts/config.default.json --daemon
```

## Feature Overview

```text
filesystem -> watcher -> indexer/chunker -> sqlite chunks + FTS
                         |              -> TODO engine
                         |              -> chunk history
query API -> intent router -> BM25 + TF cosine vector fallback -> RRF results
agents -> sessions/decisions/touches -> handoff context -> MCP tools
agents -> bus messages/locks -> warnings and coordination
```

Implemented surfaces:

- HTTP REST API on `localhost:7474`
- MCP JSON-RPC endpoint at `/mcp`
- SQLite WAL storage with chunks, FTS, sessions, decisions, TODOs, bus messages, locks, dead zones, and chunk history
- Inotify watcher on Linux with polling fallback
- Structured regex chunking for code, Markdown sections, and config blocks
- Hybrid retrieval with BM25, TF cosine vector fallback, and reciprocal-rank fusion
- Agent handoff/session protocol
- Semantic-ish TODO search through the same retrieval pipeline

## Agent Integration

Claude Code, Cursor, Zed, and other MCP clients can point at:

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

At session start, agents should call `ragd_handoff_read`, then `ragd_session_start`. During work they should record touches, decisions, TODOs, and warnings. Before ending they should call `ragd_handoff_write`.

See `docs/agent_integration_guide.md`, `docs/api_reference.md`, and `docs/mcp_tools.md` for the full contract.
