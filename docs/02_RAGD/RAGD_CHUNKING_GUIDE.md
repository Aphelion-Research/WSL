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
  - chunking
---

# RAGD Chunking Guide

**Purpose:** How RAGD splits documents into retrievable chunks.

---

## Chunking Strategies

### 1. Heading-Based (Default for Markdown)

Split by `##` heading boundaries.

**Example:**
```markdown
# Title
## Section 1
Content A
## Section 2
Content B
```

**Chunks:**
- Chunk 1: "# Title"
- Chunk 2: "## Section 1\nContent A"
- Chunk 3: "## Section 2\nContent B"

**Pros:**
- Preserves semantic boundaries
- Chunks have clear context (heading)
- Natural size (sections are usually 200-2000 chars)

**Cons:**
- Very small sections become tiny chunks
- Very large sections need manual splitting

**Configuration:**
```python
chunker = MarkdownChunker(
    heading_level=2,  # Split on ##
    max_chunk_size=2000,
    overlap=200
)
```

---

### 2. Semantic (AST-Aware for Code)

Split by language constructs (functions, classes, methods).

**Example:**
```python
def func_a():
    pass

def func_b():
    pass

class MyClass:
    def method_a(self):
        pass
```

**Chunks:**
- Chunk 1: `def func_a(): pass`
- Chunk 2: `def func_b(): pass`
- Chunk 3: `class MyClass: def method_a(self): pass`

**Pros:**
- Code chunks are complete units
- Preserves syntax
- Natural for code retrieval

**Cons:**
- Requires AST parsing (slower)
- Large functions become large chunks

**Configuration:**
```python
chunker = ASTChunker(
    language="python",
    max_chunk_size=1500,
    overlap=100
)
```

---

### 3. Paragraph-Based

Split by blank lines.

**Pros:**
- Simple
- Fast
- Works for plain text

**Cons:**
- Loses structure
- Paragraph size varies widely

**Use:** Plain text files without clear structure.

---

### 4. Full-Document

Index entire file as one chunk.

**Pros:**
- Complete context
- No boundary issues

**Cons:**
- Large files become huge chunks
- Poor retrieval granularity

**Use:** Small files (<500 words), diagrams, templates.

---

## Chunk Size Guidelines

| Content Type | Target Size | Max Size | Overlap |
|---|---:|---:|---:|
| Markdown docs | 500-2000 chars | 3000 chars | 200 chars |
| Python code | 300-1500 chars | 2000 chars | 100 chars |
| C++ code | 300-1500 chars | 2000 chars | 100 chars |
| JSON/YAML | 200-1000 chars | 1500 chars | 50 chars |
| Plain text | 500-2000 chars | 3000 chars | 200 chars |

**Why these sizes?**
- Embedding models work best with 500-2000 chars
- Too small: loses context
- Too large: too much irrelevant content
- Overlap: preserves boundary context

---

## Overlap Strategy

**Purpose:** Preserve context across chunk boundaries.

**Example:**
```
Chunk 1: "... end of section 1."
Chunk 2: "... end of section 1.\n## Section 2\nStart of section 2 ..."
```

Overlap = last 200 chars of Chunk 1 repeated at start of Chunk 2.

**Pros:**
- Queries near boundaries find both chunks
- Context preserved

**Cons:**
- Duplicate content in index
- Slightly larger storage

**Recommendation:** 10-15% overlap (e.g., 200 chars for 2000-char chunks).

---

## Metadata Extraction

Every chunk includes:

```python
{
    "chunk_id": "abc123",
    "document_id": "docs/AGENT_README.md",
    "chunk_index": 2,
    "chunk_type": "markdown_section",
    "heading": "## Step 2: Query RAGD",
    "content": "...",
    "start_line": 45,
    "end_line": 67,
    "char_count": 1234,
    "word_count": 234,
    "doc_type": "workflow",
    "system": "Dominion",
    "ragd_priority": 10,
    "audience": ["ai_agent"],
    "status": "current",
    "last_reviewed": "2026-05-19",
    "tags": ["agent", "workflow"]
}
```

See [RAGD_METADATA_SCHEMA.md](RAGD_METADATA_SCHEMA.md) for full schema.

---

## Special Cases

### Long Code Functions

**Problem:** Single function >2000 chars.

**Solution:**
- Split by logical sections (if comments mark sections)
- Or: keep as one chunk (acceptable for complex functions)

### Short Sections

**Problem:** Many sections <200 chars.

**Solution:**
- Merge consecutive short sections
- Or: keep as-is if semantically distinct

### Tables

**Problem:** Tables split mid-row look broken.

**Solution:**
- Treat entire table as one chunk
- Or: split by row boundaries (preserve header)

### Code with Comments

**Problem:** Large docstring + small function.

**Solution:**
- Keep together (docstring provides context)

---

## Implementation

**Python:**
```python
from ragd_chunker import ChunkerFactory

# Auto-detect strategy
chunker = ChunkerFactory.create(file_path)
chunks = chunker.chunk(content)

# Manual strategy
from ragd_chunker import MarkdownChunker
chunker = MarkdownChunker(heading_level=2, max_chunk_size=2000)
chunks = chunker.chunk(markdown_content)
```

**CLI:**
```bash
# Chunk a file
python -m ragd_chunker.cli chunk --file docs/AGENT_README.md --strategy heading

# Chunk directory
python -m ragd_chunker.cli chunk-dir --dir docs/ --output chunks.json
```

---

## Quality Checks

Good chunk:
- ✓ 500-2000 chars (ideal)
- ✓ Complete semantic unit (section, function, paragraph)
- ✓ Has heading or context
- ✓ Metadata complete

Bad chunk:
- ✗ <100 chars (too small, no context)
- ✗ >5000 chars (too large, too much noise)
- ✗ Mid-sentence boundary
- ✗ Missing metadata

---

## Debugging

**Problem:** Retrieval misses relevant docs.

**Check:**
```bash
# Inspect chunks for a file
python -m ragd_chunker.cli inspect --file docs/AGENT_README.md

# Check chunk sizes
python -m ragd_chunker.cli stats --dir docs/
```

**Problem:** Chunks too large.

**Fix:**
- Reduce `max_chunk_size`
- Use finer-grained splitting (e.g., `heading_level=3`)

**Problem:** Chunks too small.

**Fix:**
- Increase `max_chunk_size`
- Merge short sections

---

## Related Docs

- [RAGD_OVERVIEW.md](RAGD_OVERVIEW.md)
- [RAGD_INDEXING_STRATEGY.md](RAGD_INDEXING_STRATEGY.md)
- [RAGD_METADATA_SCHEMA.md](RAGD_METADATA_SCHEMA.md)

---

## Retrieval Hints

- "chunking"
- "how to split documents"
- "chunk size"
- "RAGD chunking strategy"
