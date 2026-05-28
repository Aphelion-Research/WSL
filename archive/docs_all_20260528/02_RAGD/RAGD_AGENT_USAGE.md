---
doc_type: ragd
system: RAGD
ragd_priority: 10
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - ragd
  - agent
  - workflow
---

# RAGD Agent Usage

**Purpose:** How AI agents should use RAGD for context-aware development.

---

## Mandatory Workflow

**EVERY Codex run MUST:**

1. **Read handoff state** before work
2. **Query RAGD** with task-specific context before editing
3. **Inspect files** after understanding context
4. **Edit** with minimal diff
5. **Validate** changes
6. **Update docs** if substantial changes made

This is not optional. This is the contract per `/AGENTS.md`.

---

## Step 1: Read Handoff State

**Purpose:** Understand current platform state and recent work.

### Option A: Direct File Read
```bash
cat /home/Martin/Dominion/AGENT_HANDOFF.md
```

### Option B: MCP Tool (when available)
```python
# MCP tool ragd_handoff_read (not currently connected)
# When MCP server is connected:
ragd_handoff_read()
```

**What to extract:**
- Current overall status (SOURCE_GREEN, LIVE_WARN, etc.)
- Recent changes
- Known issues
- Active experiments
- Next recommended tasks

---

## Step 2: Query RAGD for Task Context

**Purpose:** Retrieve relevant docs/code before making changes.

### CLI Method (Always Available)
```bash
# Query for specific task context
python scripts/dominion_cli.py search "data pipeline feature implementation" \
  --top-k 5 \
  --json

# Filter by doc type
python scripts/dominion_cli.py search "testing strategy" \
  --filter-doc-type testing \
  --top-k 3

# Filter by audience
python scripts/dominion_cli.py search "agent workflow" \
  --filter-audience ai_agent \
  --top-k 5
```

### REST API Method
```bash
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{
    "q": "agent workflow",
    "top_k": 5,
    "filters": {
      "doc_type": "workflow",
      "audience": {"$in": ["ai_agent"]},
      "status": "current"
    }
  }'
```

### MCP Tool (when available)
```python
# When MCP server is connected:
result = ragd_query("data pipeline feature", top_k=5)
```

**Query Writing Tips:**
- Be specific: "data pipeline error handling" not "errors"
- Include context: "agent safety rules for trading" not "safety"
- Use task language: "how to add feature" not "code patterns"
- Check top 5-10 results (not just top 1)

---

## Step 3: Inspect Retrieved Context

**What to check:**
- **Metadata:** `doc_type`, `status`, `last_reviewed`
- **Priority:** High-priority docs (9-10) are authoritative
- **Audience:** Prefer docs tagged `ai_agent`
- **Freshness:** Prefer `last_reviewed` within 30 days

**Example Result:**
```json
{
  "results": [
    {
      "chunk_id": "abc123",
      "document_id": "docs/AGENT_README.md",
      "heading": "## Safety Boundaries",
      "content": "...",
      "ragd_priority": 10,
      "audience": ["ai_agent"],
      "status": "current",
      "last_reviewed": "2026-05-19",
      "score": 0.92
    }
  ]
}
```

**Decision tree:**
- `status: deprecated` → Ignore, find current version
- `ragd_priority: 1-4` → Low confidence, verify independently
- `ragd_priority: 9-10` → Authoritative, trust content
- `last_reviewed > 90 days ago` → May be stale, verify

---

## Step 4: Use Context to Guide Edits

**Before editing:**
- [ ] Understand the local contract (from retrieved docs)
- [ ] Check existing patterns (from code search)
- [ ] Verify safety boundaries (AGENT_SAFETY_RULES.md)
- [ ] Confirm testing requirements (TESTING_GUIDE.md)

**During editing:**
- Make minimal diffs
- Preserve existing patterns
- Don't refactor unrelated code
- Add tests if changing behavior

---

## Step 5: Remember Important Findings

**After significant work, record findings for future agents.**

### Option A: Update AGENT_HANDOFF.md Directly
```bash
# Edit the handoff file to record current state
# Include: what changed, why, what's next
```

### Option B: MCP Tool (when available)
```python
# When MCP server is connected:
ragd_remember(
    kind="decision",
    content="Switched data pipeline to use DuckDB for aggregations instead of pandas groupby. 10x faster on 1M+ rows. Tested with domdata xauticks pipeline."
)
```

### Fallback: Update PROGRESS.md
```bash
# For historical record
echo "## 2026-05-19 - Data Pipeline Performance" >> PROGRESS.md
echo "" >> PROGRESS.md
echo "- Switched to DuckDB aggregations (10x faster)" >> PROGRESS.md
```

**What to remember:**
- Architectural decisions (why X over Y)
- Safety-relevant findings (new attack surface)
- Performance discoveries (10x speedup)
- Failure modes (what breaks when X)
- Deferred work (TODO for next agent)

---

## Common Retrieval Patterns

### Pattern 1: Start New Feature
```bash
# Query for similar features
python scripts/dominion_cli.py search "feature implementation" --top-k 5

# Query for architecture context
python scripts/dominion_cli.py search "system architecture data pipeline" --top-k 3

# Query for testing requirements
python scripts/dominion_cli.py search "testing strategy" --top-k 3
```

### Pattern 2: Debug Existing Code
```bash
# Find the subsystem docs
python scripts/dominion_cli.py search "domdata MT5 integration" --top-k 5

# Find related issues
python scripts/dominion_cli.py search "known issues domdata" --top-k 3

# Find testing approach
python scripts/dominion_cli.py search "debugging workflow" --top-k 3
```

### Pattern 3: Update Documentation
```bash
# Find doc structure guidelines
python scripts/dominion_cli.py search "documentation system" --top-k 5

# Find related docs to link
python scripts/dominion_cli.py search "data pipeline" --filter-doc-type architecture --top-k 3
```

### Pattern 4: Understand Safety Boundaries
```bash
# Query safety rules
python scripts/dominion_cli.py search "safety rules trading" --top-k 5

# Query validation commands
python scripts/dominion_cli.py search "validation testing" --top-k 3
```

---

## Failure Recovery

### Problem: Query Returns Nothing
**Cause:** Stale index or overly specific query

**Fix:**
```bash
# Rebuild index
python scripts/dominion_cli.py scan

# Try broader query
python scripts/dominion_cli.py search "agent" --top-k 10
```

### Problem: Query Returns Wrong Docs
**Cause:** Query too generic or missing filters

**Fix:**
```bash
# Add filters
python scripts/dominion_cli.py search "workflow" \
  --filter-doc-type workflow \
  --filter-audience ai_agent

# Be more specific
python scripts/dominion_cli.py search "agent operating system workflow protocol"
```

### Problem: RAGD Daemon Unreachable
**Cause:** Daemon not running or wrong port

**Fix:**
```bash
# Check health
curl http://127.0.0.1:7474/health

# Check if running
pgrep -f ragd

# Restart if needed (check RUNBOOK.md for procedure)
```

---

## Best Practices

### DO:
- ✓ Query RAGD **before** reading code
- ✓ Use **task-specific queries** ("how to add LOB feature")
- ✓ Check **metadata** (priority, status, freshness)
- ✓ Read **top 5-10 results**, not just top 1
- ✓ Verify **high-risk changes** with safety docs
- ✓ **Update handoff** after significant work

### DON'T:
- ✗ Skip RAGD query and guess
- ✗ Use generic queries ("code", "feature", "test")
- ✗ Trust deprecated/low-priority docs
- ✗ Read only top 1 result
- ✗ Make safety-critical changes without checking AGENT_SAFETY_RULES.md
- ✗ Leave state undocumented

---

## Validation Checklist

Before claiming task complete:

- [ ] Queried RAGD with task context
- [ ] Read retrieved docs (not just titles)
- [ ] Followed local contracts from docs
- [ ] Ran `python domdata/check_no_trading.py` (MUST PASS)
- [ ] Ran relevant test suite
- [ ] Updated docs if substantial change
- [ ] Updated AGENT_HANDOFF.md with current state

---

## Related Docs

- [RAGD_OVERVIEW.md](RAGD_OVERVIEW.md) — System architecture
- [RAGD_QUERY_PATTERNS.md](RAGD_QUERY_PATTERNS.md) — Effective query patterns
- [RAGD_INDEXING_STRATEGY.md](RAGD_INDEXING_STRATEGY.md) — What's indexed
- [AGENT_OPERATING_SYSTEM.md](../03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md) — Full agent workflow
- [AGENT_SAFETY_RULES.md](../09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md) — Safety boundaries

---

## Retrieval Hints

Queries that should find this doc:
- "how to use RAGD"
- "agent workflow RAGD"
- "RAGD agent usage"
- "how to query RAGD"
- "agent context loading"
