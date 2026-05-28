---
doc_type: prompt
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - prompt
  - documentation
---

# CODEX Documentation Update Prompt

**Use Case:** Update documentation  
**Complexity:** Medium  
**Duration:** 30-60 minutes

---

## Context

Documentation in Dominion V2 stale or incomplete.

Target docs: [SPECIFY DOCS OR "ALL"]

Repository: `/home/Martin/Dominion`

---

## Mission

Update documentation to match current code state:
1. Identify stale docs
2. Read current code
3. Update docs
4. Sync to vault
5. Rebuild RAGD index
6. Validate

---

## Workflow

### Step 1: Identify Stale Docs (5 min)

```bash
# Check last modified
find docs/ -name "*.md" -mtime +30 | head -20

# Check doc status in frontmatter
grep -r "status: draft\|status: outdated" docs/ | head -10

# Compare code vs doc update dates
ls -lt [module]/*.py | head -5
ls -lt docs/05_FEATURES/[MODULE]*.md | head -5
```

### Step 2: Read Current Code (10-15 min)

For each module being documented:

```bash
# List module files
ls [module]/

# Key classes/functions
grep -n "^class\|^def " [module]/*.py

# Check tests (indicate current behavior)
ls tests/[module]/
```

Read:
- Module `__init__.py` (public API)
- Main implementation files
- CLI (if exists)
- Tests (ground truth for behavior)

### Step 3: Update Doc Content (20-30 min)

**For feature specs** (`docs/05_FEATURES/`):

Required sections:
- Purpose
- Status (implementation, tests, docs)
- Key Components
- Usage Examples
- CLI Commands (if applicable)
- Configuration
- Data Schema (if applicable)
- Integration Points
- Tests (count, coverage)
- Known Limitations
- Future Enhancements

**For architecture docs** (`docs/01_ARCHITECTURE/`):

Required sections:
- Overview
- Components
- Dependencies
- Data Flow (diagrams helpful)
- Extension Points

**For development guides** (`docs/04_DEVELOPMENT/`):

Required sections:
- Purpose
- Prerequisites
- Step-by-Step Instructions
- Examples
- Troubleshooting
- Related Docs

### Step 4: Update Frontmatter (2 min)

```yaml
---
doc_type: [feature | architecture | guide | ...]
system: Dominion
ragd_priority: [1-10]
audience:
  - ai_agent
  - maintainer
  - owner
status: current
last_reviewed: 2026-05-19  # Update to today
tags:
  - [relevant tags]
---
```

### Step 5: Check Links (3 min)

```bash
# Find wiki links in doc
grep -o '\[\[.*\]\]' docs/[file].md

# Verify targets exist
python scripts/dominion_cli.py vault doctor --json | jq '.broken_links'
```

Fix broken links or create stub notes.

### Step 6: Sync to Vault (2 min)

```bash
python scripts/vault_sync.py
```

Verify sync:
```bash
ls vault/files/docs/[updated_doc].md
```

### Step 7: Rebuild RAGD Index (3 min)

```bash
python scripts/dominion_cli.py scan
```

Test retrieval:
```bash
python scripts/dominion_cli.py search "[doc topic]" --top-k 3
```

### Step 8: Validate (5 min)

```bash
# Vault integrity
python scripts/dominion_cli.py vault doctor --json

# Check RAGD indexing
curl http://127.0.0.1:7474/health | jq '.active_chunks'

# Verify doc renders (open in Obsidian or cat)
cat vault/files/docs/[updated_doc].md | head -50
```

---

## Validation

Docs updated when:
- [ ] Content matches current code
- [ ] Frontmatter updated (last_reviewed = today)
- [ ] Links valid (no broken wiki links)
- [ ] Synced to vault
- [ ] RAGD index rebuilt
- [ ] Test queries return updated content

---

## Output

1. **Updated docs:** Modified markdown files
2. **Validation:** vault doctor + RAGD health check results
3. **Brief summary:** What changed, why

---

## Common Pitfalls

**Don't:**
- Copy code into docs (link instead)
- Leave TODOs in docs (finish or note as "Future")
- Forget to update last_reviewed date
- Skip vault sync (breaks Obsidian navigation)
- Assume docs accurate without checking code

**Do:**
- Verify behavior by reading tests
- Use concrete examples (not placeholders)
- Cross-reference related docs with [[wiki links]]
- Keep docs concise (2000 words max per file)
- Update RAGD index (makes docs discoverable)

---

## Bulk Update Strategy

If updating many docs:

1. **Group by category** (features, architecture, guides)
2. **Update category at a time**
3. **Sync + index after each category**
4. **Validate incrementally** (don't wait until end)

---

## Related Prompts

- [[CODEX_OBSIDIAN_UPDATE_PROMPT]] — Vault-specific operations
- [[CODEX_RAGD_UPDATE_PROMPT]] — Just rebuild index

---

## Retrieval Hints

- "update docs"
- "documentation update"
- "doc refresh"
- "stale docs"
