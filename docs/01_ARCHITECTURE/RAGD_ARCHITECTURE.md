---
doc_type: architecture
system: RAGD
ragd_priority: 9
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - ragd
  - architecture
  - internals
---

# RAGD Architecture Deep-Dive

**Purpose:** Internal architecture of RAGD (Retrieval-Augmented Graph Database).

---

## System Overview

RAGD is a hybrid graph + vector database optimized for code/doc retrieval.

**Key capabilities:**
- **Graph storage:** Nodes (files, functions, classes) + edges (calls, imports, defines)
- **Vector search:** HNSW index for semantic similarity
- **Chunking:** AST-aware document splitting
- **Embeddings:** Cached embeddings (nomic-embed-text via Ollama)
- **Vault integration:** Obsidian knowledge graph

**Implementation:** Native C++ core + Python bindings

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                   Python API Layer                      │
│  ragd_graph, ragd_hnsw, ragd_embed, ragd_chunker       │
└───────────────┬─────────────────────────────────────────┘
                │ (Python bindings)
┌───────────────▼─────────────────────────────────────────┐
│                 Native C++ Core                         │
│  Graph engine, HNSW index, SQLite bridge                │
└───────────────┬─────────────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────────────┐
│                   Storage Layer                         │
│  SQLite (graph), HNSW .bin (vectors), embed_cache.db   │
└─────────────────────────────────────────────────────────┘
```

---

## C++ Core Components

### File Structure

```
ragd/
├── src/                    # C++ source files
│   ├── graph.cpp           # Graph storage engine
│   ├── hnsw.cpp            # HNSW vector index
│   ├── bridge.cpp          # Python↔C++ bridge
│   ├── chunker.cpp         # AST-aware chunking
│   ├── vault.cpp           # Obsidian integration
│   └── doctor.cpp          # Health checks
├── include/                # Header files
│   ├── graph.h
│   ├── hnsw.h
│   └── ...
├── tests/                  # 24 C++ tests
├── build/                  # CMake build artifacts
└── vendor/                 # Third-party libs
```

**Lines of code:** ~5000 C++ LOC (estimated)

---

## Graph Storage (graph.cpp)

### Schema

**Nodes:**
```sql
CREATE TABLE nodes (
    id INTEGER PRIMARY KEY,
    type TEXT,              -- 'file', 'function', 'class', 'chunk'
    name TEXT,
    path TEXT,
    content TEXT,
    metadata JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Edges:**
```sql
CREATE TABLE edges (
    id INTEGER PRIMARY KEY,
    source_id INTEGER,
    target_id INTEGER,
    relation TEXT,          -- 'calls', 'imports', 'defines', 'contains'
    weight REAL,
    metadata JSON,
    FOREIGN KEY(source_id) REFERENCES nodes(id),
    FOREIGN KEY(target_id) REFERENCES nodes(id)
);
```

### Supported Queries

**Node lookup:**
```cpp
Node* get_node(int id);
std::vector<Node*> find_nodes_by_type(const std::string& type);
std::vector<Node*> find_nodes_by_path(const std::string& path);
```

**Graph traversal:**
```cpp
std::vector<Edge*> get_outgoing_edges(int node_id);
std::vector<Edge*> get_incoming_edges(int node_id);
std::vector<Node*> get_neighbors(int node_id, const std::string& relation);
```

**Batch operations:**
```cpp
void add_nodes(const std::vector<Node>& nodes);
void add_edges(const std::vector<Edge>& edges);
void delete_orphan_nodes();  // Nodes with no edges
```

---

## HNSW Vector Index (hnsw.cpp)

### Implementation

**Library:** Custom HNSW implementation (based on hnswlib)

**Index structure:**
```
HNSW Index (M=16, ef_construction=200)
├── Layer 0 (all vectors)       [7161 vectors]
├── Layer 1 (50% sample)        [~3580 vectors]
├── Layer 2 (25% sample)        [~1790 vectors]
└── ...
```

**Parameters:**
- `M=16` — Max neighbors per node (higher = better recall, more memory)
- `ef_construction=200` — Construction time beam width (higher = better quality)
- `ef_search=50` — Query time beam width (higher = better recall, slower)

### Operations

**Add vectors:**
```cpp
void add_items(const std::vector<float*>& embeddings, const std::vector<int>& ids);
```

**Search:**
```cpp
std::vector<SearchResult> search(const float* query_embedding, int top_k);
```

**Persist:**
```cpp
void save_index(const std::string& path);
void load_index(const std::string& path);
```

### Storage

**File:** `~/.ragd/hnsw_ollama_nomic-embed-text_768.bin`

**Size:** ~50MB for 7161 vectors (768-dim)

**Format:** Custom binary format (header + layers)

---

## Embedding Cache (ragd_embed)

### Cache Schema

```sql
CREATE TABLE embeddings (
    content_hash TEXT PRIMARY KEY,
    provider TEXT,          -- 'ollama', 'openai', 'cohere'
    model TEXT,             -- 'nomic-embed-text', 'text-embedding-3-small'
    embedding BLOB,         -- Serialized float array
    dimension INTEGER,
    created_at TIMESTAMP
);
```

### Cache Hit Rate

**Current stats (2026-05-19):**
- Entries: 7161
- Size: 21MB
- Provider: `ollama`
- Model: `nomic-embed-text` (768-dim)
- Hit rate: ~95% (most docs already embedded)

### Providers

**Ollama (default):**
```python
from ragd_embed.providers import OllamaProvider
provider = OllamaProvider(model="nomic-embed-text")
embedding = provider.embed("query text")
```

**OpenAI (if API key set):**
```python
from ragd_embed.providers import OpenAIProvider
provider = OpenAIProvider(model="text-embedding-3-small", api_key="...")
embedding = provider.embed("query text")
```

---

## Chunker (ragd_chunker)

### AST-Aware Chunking

**Strategy:** Parse code with Tree-sitter, split by AST nodes.

**Supported languages:**
- Python
- JavaScript/TypeScript
- C/C++
- Go
- Rust

**Chunk types:**
- `function` — Individual functions
- `class` — Classes with methods
- `module` — Top-level module

**Markdown strategy:**
- Split by `##` headers (heading-based)
- Preserve code blocks intact
- Target size: 500-2000 chars

### Implementation

```python
from ragd_chunker import ChunkerFactory

chunker = ChunkerFactory.create("path/to/file.py")
chunks = chunker.chunk(content)

# Output:
# [
#   {"type": "function", "name": "compute_returns", "content": "...", "start_line": 10, "end_line": 22},
#   {"type": "class", "name": "KalmanFilter", "content": "...", "start_line": 24, "end_line": 83},
# ]
```

---

## Vault Integration (ragd_vault)

### Obsidian Vault Structure

```
vault/
├── notes/                  # 878 markdown notes
├── .obsidian/              # Obsidian config
└── attachments/            # Images, PDFs
```

### Features

**Link resolution:**
- Parse `[[wikilinks]]`
- Build bidirectional link graph
- Detect broken links

**Frontmatter extraction:**
```yaml
---
tags: [architecture, ragd]
created: 2026-05-19
---
```

**Health checks:**
```python
from ragd_vault import VaultDoctor

doctor = VaultDoctor("path/to/vault")
report = doctor.run()

# report = {
#   "notes": 878,
#   "broken_links": 0,
#   "orphan_notes": 12,
#   "invalid_frontmatter": 0,
# }
```

---

## REST API (ragd daemon)

### Endpoints

**Health:**
```
GET /health
Response: {"status": "ok", "version": "0.1.0", "uptime_seconds": 12345}
```

**Query:**
```
POST /query
Body: {"q": "agent workflow", "top_k": 5, "filters": {...}}
Response: {
  "results": [
    {"chunk_id": "abc", "content": "...", "score": 0.92, "metadata": {...}},
    ...
  ]
}
```

**Index:**
```
POST /index
Body: {"path": "docs/new_doc.md", "content": "..."}
Response: {"chunk_ids": ["abc", "def"], "indexed_at": "2026-05-19T..."}
```

**Graph:**
```
GET /graph?node_id=123
Response: {
  "node": {...},
  "neighbors": [
    {"id": 456, "relation": "calls", "name": "compute_sharpe"},
    ...
  ]
}
```

---

## Python Bindings Architecture

### Binding Layer

**ragd_graph (Python wrapper):**
```python
# Python → C++ bridge
class GraphStore:
    def __init__(self, db_path: str):
        self._handle = _ragd_native.create_graph(db_path)  # C++ handle
    
    def add_node(self, node: Node) -> int:
        return _ragd_native.add_node(self._handle, node)
    
    def query(self, query: str) -> List[Node]:
        return _ragd_native.query_nodes(self._handle, query)
```

**Binding technology:** pybind11 (C++11 → Python)

**Performance:** ~10µs overhead per call (negligible)

---

## Data Flow

### Indexing Flow

```
┌─────────────┐
│ Source File │
└──────┬──────┘
       │
       ▼
┌────────────────┐
│ ragd_chunker   │  Split by AST nodes
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ ragd_embed     │  Generate embeddings
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ ragd_graph     │  Store nodes/edges
│ ragd_hnsw      │  Index vectors
└────────────────┘
```

### Query Flow

```
┌─────────────┐
│ User Query  │
└──────┬──────┘
       │
       ▼
┌────────────────┐
│ ragd_embed     │  Embed query
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ ragd_hnsw      │  Vector search (top-k)
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ ragd_graph     │  Fetch node metadata
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ Rerank + Filter│  Apply filters, rerank
└──────┬─────────┘
       │
       ▼
┌────────────────┐
│ Return Results │
└────────────────┘
```

---

## Performance Characteristics

### Query Latency

- **Vector search (HNSW):** ~10-20ms for top-10
- **Graph lookup:** ~1-5ms per node
- **Embedding:** ~100ms (Ollama), cached if seen before
- **Total:** <50ms for cached query

### Index Build Time

- **Full scan:** ~20s for 1282 files
- **Chunk:** ~5s for 1282 files
- **Embed:** ~2 hours for 7161 chunks (Ollama, no cache)
- **HNSW build:** ~30s for 7161 vectors

### Memory Usage

- **HNSW index:** ~50MB (in-memory)
- **Graph database:** ~10MB (SQLite, on-disk)
- **Embedding cache:** ~21MB (SQLite, on-disk)
- **Python process:** ~100MB resident

---

## Concurrency Model

### Read Concurrency

- **SQLite:** WAL mode → multiple concurrent readers
- **HNSW:** Lock-free reads (C++ shared_ptr)
- **Embedding cache:** SQLite WAL mode

**Result:** Multiple agents can query RAGD simultaneously.

### Write Concurrency

- **SQLite:** Single writer at a time
- **HNSW:** Write lock required
- **Embedding cache:** Single writer

**Result:** Index updates are serialized.

---

## Failure Modes

### Chunker Unreachable

**Symptom:** `<urlopen error [Errno 111] Connection refused>`

**Cause:** Chunker service not running

**Impact:** Can't chunk new files (but can still query existing)

**Fix:** Start chunker service or use static chunking

### Embedding API Key Missing

**Symptom:** `api_key_present: false`

**Cause:** `RAGD_EMBED_API_KEY` not set

**Impact:** Can't embed new docs (but cached embeddings work)

**Fix:** Set API key or use Ollama (no key needed)

### HNSW Index Corrupt

**Symptom:** Segfault on query

**Cause:** Index file corrupted (disk failure, incomplete write)

**Impact:** Vector search fails

**Fix:** Rebuild index from scratch

---

## Testing

### Unit Tests (C++)

**Location:** `ragd/tests/`

**Count:** 24 tests

**Coverage:** ~80%

**Run:**
```bash
cd ragd/build
ctest --output-on-failure
```

**Sample tests:**
- `test_graph_add_node`
- `test_hnsw_search`
- `test_chunker_python`
- `test_embedding_cache`

### Integration Tests (Python)

**Location:** `dominion_ai/tests/test_eval.py`

**Tests:**
- End-to-end retrieval
- Recall@10 = 1.0
- MRR = 1.0

---

## Future Enhancements

1. **WebSocket support:** Replace REST with WebSocket for real-time updates
2. **Distributed RAGD:** Shard graph across multiple nodes
3. **GPU acceleration:** Use FAISS GPU for vector search
4. **Incremental indexing:** Update index without full rebuild
5. **Query caching:** Cache frequent queries
6. **Compression:** Compress embeddings (PQ, OPQ)

---

## Related Docs

- [RAGD_OVERVIEW.md](../02_RAGD/RAGD_OVERVIEW.md) — High-level overview
- [RAGD_AGENT_USAGE.md](../02_RAGD/RAGD_AGENT_USAGE.md) — How agents use RAGD
- [DEPENDENCY_MAP.md](DEPENDENCY_MAP.md) — Module dependencies

---

**RAGD architecture documented.** Use for deep understanding of RAGD internals.
