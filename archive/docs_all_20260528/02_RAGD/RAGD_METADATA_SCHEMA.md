---
doc_type: ragd
system: RAGD
ragd_priority: 8
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - ragd
  - metadata
  - schema
---

# RAGD Metadata Schema

**Purpose:** Standard metadata for all RAGD chunks.

---

## Chunk Metadata

Every chunk has:

```json
{
  "chunk_id": "abc123def456",
  "document_id": "docs/AGENT_README.md",
  "chunk_index": 2,
  "chunk_type": "markdown_section",
  "content": "... chunk text ...",
  
  "heading": "## Step 2: Query RAGD",
  "start_line": 45,
  "end_line": 67,
  "char_count": 1234,
  "word_count": 234,
  
  "doc_type": "workflow",
  "system": "Dominion",
  "ragd_priority": 10,
  "audience": ["ai_agent", "maintainer"],
  "status": "current",
  "last_reviewed": "2026-05-19",
  "tags": ["agent", "workflow", "ragd"],
  
  "indexed_at": "2026-05-19T17:30:00Z",
  "content_hash": "sha256:...",
  "embedding": [0.123, -0.456, ...]
}
```

---

## Field Definitions

### Core Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `chunk_id` | string | YES | Unique chunk identifier (UUID or hash) |
| `document_id` | string | YES | Source document path (relative to repo root) |
| `chunk_index` | int | YES | Chunk number within document (0-indexed) |
| `chunk_type` | enum | YES | Type: `markdown_section`, `python_function`, `python_class`, `cpp_function`, `full_doc`, `paragraph` |
| `content` | string | YES | Actual chunk text |

### Location Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `heading` | string | NO | Section heading (markdown only) |
| `start_line` | int | NO | Starting line number in source file |
| `end_line` | int | NO | Ending line number in source file |
| `char_count` | int | YES | Character count |
| `word_count` | int | YES | Word count (whitespace-split) |

### Document Metadata (from frontmatter)

| Field | Type | Required | Description |
|---|---|---|---|
| `doc_type` | enum | YES | Document type: `architecture`, `feature`, `workflow`, `roadmap`, `research`, `backlog`, `adr`, `testing`, `safety` |
| `system` | string | YES | Subsystem: `Dominion`, `RAGD`, `domdata`, `data_pipeline`, `agent_os`, etc. |
| `ragd_priority` | int | YES | Priority 1-10 (10 = highest) |
| `audience` | array | YES | Intended audience: `ai_agent`, `maintainer`, `owner`, `auditor` |
| `status` | enum | YES | Status: `current`, `planned`, `deprecated`, `archived` |
| `last_reviewed` | date | YES | Last review date (YYYY-MM-DD) |
| `tags` | array | YES | Free-form tags |

### Indexing Metadata

| Field | Type | Required | Description |
|---|---|---|---|
| `indexed_at` | datetime | YES | When chunk was indexed (ISO 8601) |
| `content_hash` | string | YES | SHA-256 hash of content (for change detection) |
| `embedding` | array | NO | Embedding vector (if semantic search enabled) |
| `embedding_model` | string | NO | Model used for embedding (e.g., `text-embedding-3-small`) |

---

## Frontmatter Schema

Every documentation file should have:

```yaml
---
doc_type: architecture | feature | workflow | roadmap | research | backlog | adr | testing | safety | ragd | development
system: Dominion | RAGD | domdata | data_pipeline | agent_os | vault | microstructure
ragd_priority: 1-10
audience:
  - ai_agent
  - maintainer
  - owner
  - auditor
status: current | planned | deprecated | archived
last_reviewed: YYYY-MM-DD
tags:
  - tag1
  - tag2
---
```

**Validation:**
- `doc_type`: required, one of enum
- `system`: required, string
- `ragd_priority`: required, integer 1-10
- `audience`: required, array of strings
- `status`: required, one of enum
- `last_reviewed`: required, date format YYYY-MM-DD
- `tags`: required, array of strings (at least 1 tag)

---

## Filtering Examples

**Get all agent workflow docs:**
```python
chunks = ragd_query(
    text="agent workflow",
    filters={
        "doc_type": "workflow",
        "audience": {"$in": ["ai_agent"]},
        "status": "current"
    }
)
```

**Get high-priority architecture docs:**
```python
chunks = ragd_query(
    text="system architecture",
    filters={
        "doc_type": "architecture",
        "ragd_priority": {"$gte": 8},
        "status": "current"
    }
)
```

**Get docs reviewed in last 30 days:**
```python
chunks = ragd_query(
    text="recent updates",
    filters={
        "last_reviewed": {"$gte": "2026-04-19"},
        "status": "current"
    }
)
```

---

## Boosting by Priority

High-priority docs get relevance boost:

```python
# Priority 10 → 2.0x boost
# Priority 9 → 1.5x boost
# Priority 8 → 1.2x boost
# Priority 7 → 1.0x (baseline)
# Priority 1-6 → 0.8x

boost_factor = {
    10: 2.0,
    9: 1.5,
    8: 1.2,
    7: 1.0,
    6: 0.8,
    5: 0.8,
    4: 0.8,
    3: 0.8,
    2: 0.8,
    1: 0.8
}
```

Result: P10 docs appear higher in retrieval results.

---

## Schema Evolution

**Adding new field:**
1. Add to schema definition
2. Update chunker to populate field
3. Reindex affected docs
4. Update query code to use new field

**Deprecating field:**
1. Mark as deprecated (keep for 30 days)
2. Update docs
3. Stop populating field
4. After 30 days, remove from schema

**Current version:** v1.0 (2026-05-19)

---

## Validation

**Python:**
```python
from ragd.schema import validate_metadata

metadata = {
    "chunk_id": "abc123",
    "document_id": "docs/test.md",
    # ... more fields
}

errors = validate_metadata(metadata)
if errors:
    raise ValueError(f"Invalid metadata: {errors}")
```

**CLI:**
```bash
# Validate all chunks
python -m ragd.cli validate --db data/ragd.db
```

---

## Related Docs

- [RAGD_OVERVIEW.md](RAGD_OVERVIEW.md)
- [RAGD_INDEXING_STRATEGY.md](RAGD_INDEXING_STRATEGY.md)
- [RAGD_CHUNKING_GUIDE.md](RAGD_CHUNKING_GUIDE.md)

---

## Retrieval Hints

- "metadata schema"
- "chunk metadata"
- "RAGD fields"
- "document metadata"
- "frontmatter format"
