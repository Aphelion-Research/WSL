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
  - indexing
  - strategy
---

# RAGD Indexing Strategy

**Purpose:** What gets indexed, when, and how.

---

## Indexing Goals

1. **High-priority docs indexed first** (agent operating manuals, safety rules)
2. **Current docs only** (exclude deprecated/archived)
3. **Metadata-enriched** (priority, audience, status)
4. **Optimal chunk sizes** (500-2000 chars)
5. **Fast retrieval** (<50ms query latency)

---

## Priority Tiers

### Tier 1: Priority 9-10 (CRITICAL)
**Index immediately, high boost, re-index on every change**

- Agent operating manuals (AGENT_README.md, AGENT_OPERATING_SYSTEM.md)
- Safety rules (AGENT_SAFETY_RULES.md)
- Platform contract (AGENTS.md)
- Current state (AGENT_HANDOFF.md)
- Core architecture (SYSTEM_OVERVIEW.md, DATA_FLOW.md)

**Retrieval boost:** 2.0x (P10), 1.5x (P9)

**Why:** Agents query these most frequently. Incorrect retrieval causes safety/contract violations.

---

### Tier 2: Priority 7-8 (HIGH)
**Index early, medium boost, re-index daily**

- Feature specs (LOB, TCA, exec_sim)
- Development standards (CODING_STANDARDS.md, TESTING_GUIDE.md)
- RAGD system docs (this doc, RAGD_OVERVIEW.md)
- Risk & security (FAILURE_MODES.md, RISK_REGISTER.md)

**Retrieval boost:** 1.2x (P8), 1.0x (P7)

**Why:** Frequently referenced during development. Errors here cause bugs but not safety violations.

---

### Tier 3: Priority 5-6 (MEDIUM)
**Index normally, no boost, re-index weekly**

- Roadmap (MASTER_ROADMAP.md, phase plans)
- Decision logs (ADRs)
- Prompts (agent templates)
- Backlog (feature queue, tech debt)
- System maps (diagrams)

**Retrieval boost:** 1.0x

**Why:** Context for planning but not execution-critical.

---

### Tier 4: Priority 3-4 (LOW)
**Index late, low priority, re-index monthly**

- Research notes (future investigations)
- Future vision (long-term plans)
- Historical reports (past work)

**Retrieval boost:** 0.8x

**Why:** Historical context only. Rarely queried by agents.

---

### Tier 5: Priority 1-2 (ARCHIVE)
**Index only if space allows**

- Deprecated docs
- Archive material
- Old drafts

**Retrieval boost:** 0.5x

**Why:** Kept for historical record but should not appear in normal queries.

---

## What Gets Indexed

### Always Index
- ✓ Documentation (`.md` files) in `docs/`
- ✓ Top-level docs (README.md, AGENTS.md, AGENT_HANDOFF.md)
- ✓ Obsidian vault notes (`vault/**/*.md`)
- ✓ Python source files with docstrings
- ✓ C++ header files with documentation comments

### Conditionally Index
- Code files: Only if they have significant documentation
- Configuration files: Only if they define behavior
- Test files: Only integration test docs, not unit test code

### Never Index
- ✗ `secrets/` directory (safety boundary)
- ✗ `.git/` directory
- ✗ Binary files (`.db`, `.bin`, `.parquet`)
- ✗ Generated files (`build/`, `__pycache__/`)
- ✗ Temporary files (`.tmp`, `.bak`)
- ✗ Raw data dumps (MT5 data, logs)

---

## Chunking Strategy by File Type

### Markdown Docs
**Strategy:** Heading-based (split on `##` headers)

**Target size:** 500-2000 chars

**Overlap:** 200 chars

**Example:**
```markdown
# Doc Title
## Section 1
Content A...
## Section 2
Content B...
```
→ Chunk 1: "## Section 1\nContent A..."
→ Chunk 2: "## Section 2\nContent B..."

---

### Python Code
**Strategy:** AST-aware (split by function/class)

**Target size:** 300-1500 chars

**Overlap:** 100 chars

**Example:**
```python
def func_a():
    """Does A"""
    pass

class MyClass:
    def method_a(self):
        """Does M"""
        pass
```
→ Chunk 1: `def func_a(): ...`
→ Chunk 2: `class MyClass: def method_a(self): ...`

---

### C++ Code
**Strategy:** AST-aware (split by function/class)

**Target size:** 300-1500 chars

**Overlap:** 100 chars

---

### Small Files (<500 words)
**Strategy:** Full-document

**Why:** Splitting loses context for short files

---

## Metadata Extraction

Every indexed chunk includes:

```yaml
chunk_id: unique-hash
document_id: relative/path/to/file.md
chunk_index: 0
chunk_type: markdown_section | python_function | cpp_function | full_doc
content: "actual chunk text"

# From frontmatter
doc_type: workflow
system: RAGD
ragd_priority: 10
audience: [ai_agent, maintainer]
status: current
last_reviewed: 2026-05-19
tags: [ragd, agent]

# Generated
indexed_at: 2026-05-19T17:30:00Z
content_hash: sha256:...
char_count: 1234
word_count: 234
```

See [RAGD_METADATA_SCHEMA.md](RAGD_METADATA_SCHEMA.md) for full schema.

---

## Indexing Commands

### Full Rebuild
```bash
# Scan entire repo, index everything
python scripts/dominion_cli.py scan

# Output
Scanning: 878 files
Indexed: 7159 chunks
Skipped: 42 files (secrets, binary, generated)
Errors: 0
Duration: 23.4s
```

### Incremental Update
```bash
# Index only changed files
python scripts/dominion_cli.py scan --incremental

# Output
Changed: 5 files
Indexed: 32 chunks
Duration: 1.2s
```

### Single File
```bash
# Index specific file
python scripts/dominion_cli.py scan --file docs/AGENT_README.md

# Output
Indexed: 12 chunks from docs/AGENT_README.md
```

### Dry Run
```bash
# See what would be indexed without doing it
python scripts/dominion_cli.py scan --dry-run --json

# Output
{"files_to_index": [...], "files_to_skip": [...]}
```

---

## Re-Indexing Schedule

| Priority | Trigger | Frequency |
|---|---|---|
| **P10** | On every change | Immediate |
| **P9** | On every change | Immediate |
| **P8** | File modified | Daily |
| **P7** | File modified | Daily |
| **P6** | File modified | Weekly |
| **P5** | File modified | Weekly |
| **P1-4** | Manual | Monthly |

**Implementation:** Watch for file changes, trigger re-index per schedule.

---

## Quality Control

### Before Indexing
- [ ] Doc has valid frontmatter metadata
- [ ] Priority level is appropriate (9-10 for agent-critical docs)
- [ ] Status is `current` (not deprecated)
- [ ] Last_reviewed is recent (<90 days)
- [ ] Audience is clearly defined

### After Indexing
- [ ] Run test queries
- [ ] Verify priority docs appear first
- [ ] Check chunk sizes (target 500-2000 chars)
- [ ] Verify metadata is extractable
- [ ] Check for duplicate chunks

### Maintenance
- [ ] Re-index changed files
- [ ] Purge deprecated docs
- [ ] Update priorities quarterly
- [ ] Audit staleness (last_reviewed > 90 days)

---

## Failure Modes

### Symptom: Retrieval Misses Relevant Docs
**Cause:** Doc not indexed or stale

**Fix:**
```bash
# Check if indexed
python scripts/dominion_cli.py search "exact phrase from doc" --top-k 1

# If not found, re-index
python scripts/dominion_cli.py scan
```

---

### Symptom: Too Many Results
**Cause:** Chunks too small or query too generic

**Fix:**
- Increase chunk size (edit chunker config)
- Use more specific queries
- Add metadata filters

---

### Symptom: Wrong Docs Appear First
**Cause:** Priority misconfigured or query too broad

**Fix:**
- Check doc frontmatter `ragd_priority`
- Add filters: `--filter-doc-type`, `--filter-audience`
- Make query more specific

---

## Related Docs

- [RAGD_OVERVIEW.md](RAGD_OVERVIEW.md) — System architecture
- [RAGD_CHUNKING_GUIDE.md](RAGD_CHUNKING_GUIDE.md) — Chunking strategies
- [RAGD_METADATA_SCHEMA.md](RAGD_METADATA_SCHEMA.md) — Metadata format
- [RAGD_AGENT_USAGE.md](RAGD_AGENT_USAGE.md) — How agents use RAGD
- [RAGD_INGESTION_MANIFEST.md](../RAGD_INGESTION_MANIFEST.md) — Full indexing manifest

---

## Retrieval Hints

Queries that should find this doc:
- "indexing strategy"
- "what gets indexed"
- "RAGD indexing"
- "how to reindex"
- "chunk priorities"
