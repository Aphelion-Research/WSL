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
  - retrieval
  - query
---

# RAGD Query Patterns

**Purpose:** Effective query patterns for RAGD retrieval.

---

## Query Principles

### 1. Be Task-Specific
**Bad:** "code"
**Good:** "data pipeline feature implementation"

**Why:** Generic queries return too many irrelevant results.

---

### 2. Include Context
**Bad:** "testing"
**Good:** "testing strategy for data pipeline features"

**Why:** Context narrows results to relevant subsystem.

---

### 3. Use Domain Language
**Bad:** "how to do X"
**Good:** "agent workflow for adding LOB feature"

**Why:** Docs are written in domain language (agent, LOB, pipeline, etc.).

---

### 4. Check Top 5-10 Results
**Bad:** Read only top 1 result
**Good:** Scan top 5-10, pick most relevant

**Why:** Top 1 may be close but not perfect. Top 5 give you options.

---

## Query Patterns by Task

### Pattern: Start New Feature
**Goal:** Understand similar features, architecture, testing requirements

**Queries:**
```bash
# Find similar features
python scripts/dominion_cli.py search "LOB reconstruction feature implementation" --top-k 5

# Find architecture context
python scripts/dominion_cli.py search "microstructure system architecture data flow" --top-k 3

# Find testing requirements
python scripts/dominion_cli.py search "testing strategy microstructure features" --top-k 3
```

**Expected results:**
- Feature specs (FEATURE_INDEX.md, LOB_RECONSTRUCTION_FEATURE.md)
- Architecture docs (SYSTEM_OVERVIEW.md, DATA_FLOW.md)
- Testing guide (TESTING_GUIDE.md)

---

### Pattern: Debug Existing Code
**Goal:** Understand subsystem, find known issues, locate debugging workflow

**Queries:**
```bash
# Find subsystem docs
python scripts/dominion_cli.py search "domdata MT5 integration read-only" --top-k 5

# Find known issues
python scripts/dominion_cli.py search "domdata failure modes known issues" --top-k 3

# Find debugging approach
python scripts/dominion_cli.py search "debugging workflow validation commands" --top-k 3
```

**Expected results:**
- Subsystem docs (DOMDATA.md, DATA_PIPELINE.md)
- Risk docs (FAILURE_MODES.md)
- Development guide (DEBUGGING_GUIDE.md)

---

### Pattern: Understand Safety Boundaries
**Goal:** Find trading restrictions, validation commands, safety rules

**Queries:**
```bash
# Safety rules
python scripts/dominion_cli.py search "agent safety rules trading forbidden" --top-k 5

# Validation commands
python scripts/dominion_cli.py search "validation commands check_no_trading domdata" --top-k 3

# What's allowed
python scripts/dominion_cli.py search "read-only data access MT5" --top-k 3
```

**Expected results:**
- Safety docs (AGENT_SAFETY_RULES.md, AGENTS.md)
- Validation scripts (check_no_trading.py)
- Platform contract (AGENTS.md)

---

### Pattern: Update Documentation
**Goal:** Find doc structure, related docs to link, metadata format

**Queries:**
```bash
# Doc structure guidelines
python scripts/dominion_cli.py search "documentation system RAGD metadata" --top-k 5

# Related docs for linking
python scripts/dominion_cli.py search "data pipeline architecture" \
  --filter-doc-type architecture \
  --top-k 3

# Metadata format
python scripts/dominion_cli.py search "frontmatter metadata schema" --top-k 3
```

**Expected results:**
- Doc standards (ADR_0001_DOCUMENTATION_SYSTEM.md)
- Related docs in target subsystem
- Metadata schema (RAGD_METADATA_SCHEMA.md)

---

### Pattern: Understand Agent Workflow
**Goal:** Learn agent operating system, handoff protocol, RAGD usage

**Queries:**
```bash
# Agent workflow
python scripts/dominion_cli.py search "agent operating system workflow" \
  --filter-audience ai_agent \
  --top-k 5

# Handoff protocol
python scripts/dominion_cli.py search "agent handoff protocol current state" --top-k 3

# RAGD usage
python scripts/dominion_cli.py search "how to use RAGD agent context loading" --top-k 3
```

**Expected results:**
- Workflow docs (AGENT_OPERATING_SYSTEM.md, AGENT_README.md)
- Handoff protocol (AGENT_HANDOFF_PROTOCOL.md)
- RAGD usage (RAGD_AGENT_USAGE.md)

---

## Filtering Strategies

### Filter by Document Type
```bash
# Only architecture docs
python scripts/dominion_cli.py search "data flow" --filter-doc-type architecture

# Only workflows
python scripts/dominion_cli.py search "agent process" --filter-doc-type workflow

# Only safety docs
python scripts/dominion_cli.py search "trading restrictions" --filter-doc-type safety
```

**Available doc_types:**
- `architecture`
- `feature`
- `workflow`
- `roadmap`
- `research`
- `backlog`
- `adr`
- `testing`
- `safety`
- `ragd`
- `development`

---

### Filter by Audience
```bash
# Agent-specific docs
python scripts/dominion_cli.py search "coding standards" \
  --filter-audience ai_agent

# Maintainer docs
python scripts/dominion_cli.py search "deployment runbook" \
  --filter-audience maintainer
```

**Available audiences:**
- `ai_agent` — AI coding agents
- `maintainer` — Human maintainers
- `owner` — Project owner
- `auditor` — Security auditors

---

### Filter by Status
```bash
# Current docs only (default)
python scripts/dominion_cli.py search "feature spec" --filter-status current

# Include planned features
python scripts/dominion_cli.py search "future features" --filter-status planned
```

**Available statuses:**
- `current` — Active docs (default)
- `planned` — Future work
- `deprecated` — Old versions (use with caution)
- `archived` — Historical only

---

### Filter by Priority
```bash
# High-priority docs only
python scripts/dominion_cli.py search "agent workflow" --min-priority 9

# Critical docs (P10)
python scripts/dominion_cli.py search "safety rules" --min-priority 10
```

---

## REST API Query Examples

### Basic Query
```bash
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{
    "q": "agent workflow",
    "top_k": 5
  }'
```

### Query with Filters
```bash
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{
    "q": "data pipeline feature",
    "top_k": 5,
    "filters": {
      "doc_type": "feature",
      "status": "current",
      "ragd_priority": {"$gte": 7}
    }
  }'
```

### Query with Audience Filter
```bash
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{
    "q": "testing strategy",
    "top_k": 3,
    "filters": {
      "audience": {"$in": ["ai_agent", "maintainer"]},
      "status": "current"
    }
  }'
```

---

## Common Queries & Expected Results

| Query | Expected Top Result | Priority |
|---|---|---|
| "agent workflow" | AGENT_OPERATING_SYSTEM.md | P10 |
| "safety rules" | AGENT_SAFETY_RULES.md | P10 |
| "platform contract" | AGENTS.md | P10 |
| "current state" | AGENT_HANDOFF.md | P10 |
| "system architecture" | SYSTEM_OVERVIEW.md | P9 |
| "data flow" | DATA_FLOW.md | P9 |
| "how RAGD works" | RAGD_OVERVIEW.md | P9 |
| "coding standards" | CODING_STANDARDS.md | P9 |
| "testing strategy" | TESTING_GUIDE.md | P7 |
| "feature list" | FEATURE_INDEX.md | P8 |
| "data pipeline design" | DATA_PIPELINE_FEATURE.md | P8 |
| "what can go wrong" | FAILURE_MODES.md | P8 |
| "future plans" | MASTER_ROADMAP.md | P6 |
| "why did we decide X" | DECISION_LOG_INDEX.md | P7 |

---

## Debugging Bad Queries

### Symptom: 0 Results
**Cause:** Query too specific or index stale

**Fix:**
```bash
# Try broader query
python scripts/dominion_cli.py search "agent" --top-k 10

# Rebuild index
python scripts/dominion_cli.py scan

# Check if doc exists
find docs -name "*agent*"
```

---

### Symptom: Too Many Irrelevant Results
**Cause:** Query too generic

**Fix:**
```bash
# Add context
python scripts/dominion_cli.py search "agent workflow RAGD context loading"

# Add filters
python scripts/dominion_cli.py search "workflow" \
  --filter-doc-type workflow \
  --filter-audience ai_agent
```

---

### Symptom: Wrong Doc Appears First
**Cause:** Priority mismatch or deprecated doc

**Fix:**
```bash
# Filter by status
python scripts/dominion_cli.py search "feature spec" --filter-status current

# Check metadata
python scripts/dominion_cli.py search "X" --top-k 5 --json | jq '.results[].ragd_priority'
```

---

### Symptom: Stale Content Returned
**Cause:** Doc updated but not re-indexed

**Fix:**
```bash
# Re-index specific file
python scripts/dominion_cli.py scan --file docs/changed_doc.md

# Full re-index
python scripts/dominion_cli.py scan
```

---

## Best Practices

### DO:
- ✓ Use task-specific queries ("implement LOB feature")
- ✓ Include subsystem context ("data pipeline error handling")
- ✓ Check top 5-10 results
- ✓ Use filters for doc_type, audience, status
- ✓ Verify metadata (priority, freshness, status)

### DON'T:
- ✗ Use single-word queries ("code", "test")
- ✗ Read only top 1 result
- ✗ Trust deprecated docs (check `status` field)
- ✗ Ignore low-priority results when high-priority missing
- ✗ Query without context ("how to")

---

## Performance Tips

- **Query latency:** <50ms (HNSW search)
- **Optimal top_k:** 5 (good balance of relevance/noise)
- **Max useful top_k:** 10 (beyond this, quality drops)
- **Filter overhead:** Minimal (<5ms)

---

## Related Docs

- [RAGD_OVERVIEW.md](RAGD_OVERVIEW.md) — System architecture
- [RAGD_AGENT_USAGE.md](RAGD_AGENT_USAGE.md) — Agent workflow with RAGD
- [RAGD_INDEXING_STRATEGY.md](RAGD_INDEXING_STRATEGY.md) — What's indexed
- [RAGD_METADATA_SCHEMA.md](RAGD_METADATA_SCHEMA.md) — Metadata format
- [AGENT_OPERATING_SYSTEM.md](../03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md) — Full agent workflow

---

## Retrieval Hints

Queries that should find this doc:
- "query patterns"
- "how to query RAGD"
- "effective RAGD queries"
- "retrieval best practices"
- "RAGD search examples"
