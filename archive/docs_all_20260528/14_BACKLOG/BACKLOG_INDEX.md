---
doc_type: backlog
system: Dominion
ragd_priority: 5
audience:
  - owner
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - backlog
  - work-queue
  - planning
---

# Backlog Index

**Purpose:** Central catalog of pending work across all categories.

---

## Backlog Categories

| Category | File | Priority Range | Items (est.) |
|---|---|---|---|
| **Features** | [FEATURE_BACKLOG.md](FEATURE_BACKLOG.md) | P0-P4 | ~30 |
| **Bugs** | [BUG_BACKLOG.md](BUG_BACKLOG.md) | P0-P4 | ~15 |
| **Tech Debt** | [TECH_DEBT_BACKLOG.md](TECH_DEBT_BACKLOG.md) | P1-P4 | ~25 |
| **Documentation** | [DOCS_BACKLOG.md](DOCS_BACKLOG.md) | P2-P4 | ~20 |
| **RAGD** | [RAGD_BACKLOG.md](RAGD_BACKLOG.md) | P1-P4 | ~15 |
| **Obsidian** | [OBSIDIAN_BACKLOG.md](OBSIDIAN_BACKLOG.md) | P2-P4 | ~10 |
| **Research** | [RESEARCH_BACKLOG.md](RESEARCH_BACKLOG.md) | P3-P4 | ~12 |
| **Agent** | [AGENT_BACKLOG.md](AGENT_BACKLOG.md) | P1-P4 | ~18 |

---

## Priority Levels

| Priority | Meaning | Timeline |
|---|---|---|
| **P0** | Critical — blocks all work | Fix immediately |
| **P1** | High — blocks major features | Fix within 1 week |
| **P2** | Medium — important but not blocking | Fix within 1 month |
| **P3** | Low — nice to have | Fix within 3 months |
| **P4** | Icebox — future consideration | Someday/maybe |

---

## Current High-Priority Items (P0-P1)

### P0: Critical

*(None as of 2026-05-19 — Platform operational, see `dominion doctor` for status)*

### P1: High Priority

1. **Complexity Budget Violations** (Tech Debt)
   - dominion_loader: 53.6 vs 40 budget
   - 15 TEMP_ADAPTER labels to resolve
   - Status: Open
   - File: [TECH_DEBT_BACKLOG.md](TECH_DEBT_BACKLOG.md)

2. **Orphan RAGD Chunks** (RAGD)
   - ~1600 orphan chunks from deleted `/tmp/pytest-*` paths
   - Status: Open
   - File: [RAGD_BACKLOG.md](RAGD_BACKLOG.md)

3. **WebSocket Support** (RAGD)
   - Native WebSocket `/bus` not yet implemented
   - Status: Planned for Phase 2
   - File: [RAGD_BACKLOG.md](RAGD_BACKLOG.md)

4. **Embedding Key Configuration** (RAGD)
   - RAGD_EMBED_API_KEY not set (hybrid retrieval falls back to BM25 only)
   - Status: Owner action required
   - File: [RAGD_BACKLOG.md](RAGD_BACKLOG.md)

5. **Agent Performance Baseline** (Agent)
   - Need automated agent performance tracking
   - Status: Open
   - File: [AGENT_BACKLOG.md](AGENT_BACKLOG.md)

---

## Backlog Grooming

**Frequency:** Monthly (or after major phase completion)

**Process:**
1. Review all P0/P1 items — still relevant?
2. Promote urgent P2 items to P1
3. Demote/close irrelevant items
4. Update estimates and acceptance criteria
5. Link related items
6. Add new items discovered during work

**Next Grooming:** 2026-06-19

---

## Adding New Items

**Template:**

```markdown
## Item Title

Priority: P1  
Status: Open  
Area: RAGD | Docs | Agent | Architecture | Testing  
Assignee: TBD

### Problem

[What is broken or missing?]

### Proposed Fix

[How to solve it]

### Why It Matters

[Impact if not fixed]

### Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Tests pass
- [ ] Docs updated

### Related Files

- path/to/file.py:123
- docs/relevant_doc.md

### Dependencies

- Depends on: #123
- Blocks: #456
```

---

## Backlog Stats (2026-05-19)

| Category | Total Items | P0 | P1 | P2 | P3 | P4 |
|---|---:|---:|---:|---:|---:|---:|
| Features | ~30 | 0 | 2 | 8 | 12 | 8 |
| Bugs | ~15 | 0 | 1 | 4 | 6 | 4 |
| Tech Debt | ~25 | 0 | 2 | 8 | 10 | 5 |
| Docs | ~20 | 0 | 0 | 5 | 10 | 5 |
| RAGD | ~15 | 0 | 3 | 5 | 5 | 2 |
| Obsidian | ~10 | 0 | 0 | 3 | 5 | 2 |
| Research | ~12 | 0 | 0 | 2 | 6 | 4 |
| Agent | ~18 | 0 | 1 | 5 | 8 | 4 |
| **Total** | **~145** | **0** | **9** | **40** | **62** | **34** |

---

## Related Docs

- [06_ROADMAP/MASTER_ROADMAP.md](../06_ROADMAP/MASTER_ROADMAP.md) — Long-term roadmap
- [10_DECISION_LOGS/](../10_DECISION_LOGS/) — Architectural decisions
- [09_RISK_AND_SECURITY/RISK_REGISTER.md](../09_RISK_AND_SECURITY/RISK_REGISTER.md) — Known risks

---

## Retrieval Hints

- "backlog"
- "what needs to be done"
- "pending work"
- "TODO"
- "work queue"
