# RAGD Ingestion Manifest

**Version:** 2.0  
**Last Updated:** 2026-05-19  
**Purpose:** Control RAGD indexing priority and chunking strategy

---

## Overview

This manifest defines how RAGD should ingest Dominion documentation.

Priority levels:
- **10:** Critical — Must retrieve first (agent operating manuals, safety rules)
- **9:** Very High — Core architecture and workflows
- **8:** High — Feature specs and system design
- **7:** Medium-High — Development standards and testing
- **6:** Medium — Roadmap and planning
- **5:** Medium-Low — Research notes and investigations
- **4:** Low — Historical reports
- **3:** Very Low — Archive material
- **2:** Archive — Rarely needed
- **1:** Reference only — Don't index unless specifically needed

Chunking strategies:
- **heading-based:** Split by `##` headings (default for most docs)
- **semantic:** Use AST chunker with overlap
- **full-doc:** Index entire file as one chunk (small files only)
- **paragraph:** Split by blank lines
- **code-aware:** Preserve code blocks intact

---

## Metadata Schema

Every RAGD-indexed doc should have frontmatter:

```yaml
---
doc_type: architecture | feature | workflow | roadmap | research | backlog | adr
system: Dominion | RAGD | domdata | data_pipeline | agent_os | vault
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

This metadata enables:
- **Filtered retrieval** (e.g., "only current architecture docs")
- **Priority ranking** (high-priority docs boost relevance)
- **Audience targeting** (agent vs human docs)
- **Staleness detection** (last_reviewed date)

---

## High-Priority Documents (Priority 9-10)

These MUST be indexed first for agent context loading.

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `/AGENT_HANDOFF.md` | 10 | heading-based | ai_agent | Current state |
| `/AGENTS.md` | 10 | heading-based | ai_agent | Platform contract |
| `docs/AGENT_README.md` | 10 | heading-based | ai_agent | Agent operating manual |
| `docs/03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md` | 10 | heading-based | ai_agent | Workflow protocol |
| `docs/09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md` | 10 | heading-based | ai_agent | Safety boundaries |
| `docs/03_AGENT_OPERATIONS/AGENT_HANDOFF_PROTOCOL.md` | 9 | heading-based | ai_agent | Handoff format |
| `docs/01_ARCHITECTURE/SYSTEM_OVERVIEW.md` | 9 | heading-based | all | Architecture overview |
| `docs/01_ARCHITECTURE/DATA_FLOW.md` | 9 | heading-based | ai_agent, maintainer | Data flow diagrams |
| `docs/02_RAGD/RAGD_OVERVIEW.md` | 9 | heading-based | all | RAGD system doc |
| `docs/04_DEVELOPMENT/CODING_STANDARDS.md` | 9 | heading-based | ai_agent | Coding rules |

**Retrieval Hint:** Queries like "how to start", "agent workflow", "safety rules", "system overview" should return these.

---

## Core Architecture (Priority 8)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/01_ARCHITECTURE/REPO_STRUCTURE.md` | 8 | heading-based | all | Repo layout |
| `docs/01_ARCHITECTURE/MODULE_MAP.md` | 8 | heading-based | ai_agent, maintainer | Module dependencies |
| `docs/01_ARCHITECTURE/CONTROL_FLOW.md` | 8 | heading-based | ai_agent, maintainer | Control flow |
| `docs/01_ARCHITECTURE/DEPENDENCY_MAP.md` | 8 | heading-based | ai_agent, maintainer | Dependency graph |
| `docs/01_ARCHITECTURE/CONFIGURATION_MODEL.md` | 8 | heading-based | ai_agent, maintainer | Config structure |
| `docs/01_ARCHITECTURE/EXTENSION_POINTS.md` | 8 | heading-based | ai_agent, maintainer | Where to extend |
| `docs/01_ARCHITECTURE/KNOWN_LIMITATIONS.md` | 8 | heading-based | all | System limits |
| `docs/01_ARCHITECTURE/FUTURE_ARCHITECTURE.md` | 8 | heading-based | owner, maintainer | Architecture roadmap |

**Retrieval Hint:** "architecture", "system design", "module structure", "how does X work"

---

## RAGD System (Priority 8)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/02_RAGD/RAGD_INDEXING_STRATEGY.md` | 8 | heading-based | ai_agent | Indexing rules |
| `docs/02_RAGD/RAGD_CHUNKING_GUIDE.md` | 8 | heading-based | ai_agent | Chunking strategy |
| `docs/02_RAGD/RAGD_METADATA_SCHEMA.md` | 8 | heading-based | ai_agent | Metadata format |
| `docs/02_RAGD/RAGD_QUERY_PATTERNS.md` | 8 | heading-based | ai_agent | Query examples |
| `docs/02_RAGD/RAGD_AGENT_USAGE.md` | 8 | heading-based | ai_agent | How agents use RAGD |
| `docs/02_RAGD/RAGD_FAILURE_MODES.md` | 8 | heading-based | ai_agent, maintainer | What can go wrong |
| `docs/02_RAGD/RAGD_EVALUATION.md` | 8 | heading-based | maintainer | Eval metrics |
| `docs/02_RAGD/RAGD_FUTURE_PLAN.md` | 7 | heading-based | owner, maintainer | RAGD roadmap |

**Retrieval Hint:** "RAGD", "retrieval", "indexing", "query", "chunking"

---

## Feature Specifications (Priority 7-8)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/05_FEATURES/FEATURE_INDEX.md` | 8 | heading-based | all | Feature catalog |
| `docs/05_FEATURES/CURRENT_FEATURES.md` | 8 | heading-based | all | Implemented features |
| `docs/05_FEATURES/PLANNED_FEATURES.md` | 7 | heading-based | owner, maintainer | Future features |
| `docs/05_FEATURES/FEATURE_DEPENDENCY_MAP.md` | 7 | heading-based | ai_agent, maintainer | Feature dependencies |
| `docs/05_FEATURES/DATA_PIPELINE_FEATURE.md` | 8 | heading-based | all | Data pipeline spec |
| `docs/05_FEATURES/LOB_RECONSTRUCTION_FEATURE.md` | 8 | heading-based | all | LOB engine spec |
| `docs/05_FEATURES/EXEC_SIM_FEATURE.md` | 8 | heading-based | all | Execution simulator |
| `docs/05_FEATURES/TCA_FEATURE.md` | 7 | heading-based | all | TCA dashboard |
| `docs/05_FEATURES/TOXICITY_FEATURE.md` | 7 | heading-based | all | Toxicity monitor |
| `docs/05_FEATURES/EXEC_FEATURES_FEATURE.md` | 7 | heading-based | all | Exec alpha features |

**Retrieval Hint:** "feature", "what does X do", "how to use Y"

---

## Development Standards (Priority 7)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/04_DEVELOPMENT/DEVELOPMENT_GUIDE.md` | 7 | heading-based | ai_agent, maintainer | Dev workflow |
| `docs/04_DEVELOPMENT/TESTING_GUIDE.md` | 7 | heading-based | ai_agent, maintainer | Testing approach |
| `docs/04_DEVELOPMENT/COMMIT_GUIDE.md` | 7 | heading-based | ai_agent | Commit conventions |
| `docs/04_DEVELOPMENT/BRANCHING_GUIDE.md` | 7 | heading-based | ai_agent | Git workflow |
| `docs/04_DEVELOPMENT/LOGGING_GUIDE.md` | 7 | heading-based | ai_agent | Logging standards |
| `docs/04_DEVELOPMENT/ERROR_HANDLING_GUIDE.md` | 7 | heading-based | ai_agent | Error patterns |
| `docs/04_DEVELOPMENT/CONFIG_GUIDE.md` | 7 | heading-based | ai_agent | Config management |
| `docs/04_DEVELOPMENT/DEBUGGING_GUIDE.md` | 7 | heading-based | ai_agent, maintainer | Debug workflow |

**Retrieval Hint:** "how to develop", "testing", "commit format", "coding standards"

---

## Testing & QA (Priority 7)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/08_TESTING_AND_QA/TESTING_STRATEGY.md` | 7 | heading-based | ai_agent, maintainer | Test strategy |
| `docs/08_TESTING_AND_QA/QA_CHECKLIST.md` | 7 | heading-based | ai_agent, maintainer | Pre-release checks |
| `docs/08_TESTING_AND_QA/REGRESSION_PLAN.md` | 7 | heading-based | ai_agent, maintainer | Regression testing |
| `docs/08_TESTING_AND_QA/DOCS_VALIDATION_PLAN.md` | 7 | heading-based | ai_agent | Doc validation |
| `docs/08_TESTING_AND_QA/RAGD_RETRIEVAL_TESTS.md` | 7 | heading-based | ai_agent | RAGD eval tests |
| `docs/08_TESTING_AND_QA/QUALITY_SCORE_RUBRIC.md` | 7 | heading-based | maintainer | Quality scoring |

**Retrieval Hint:** "testing", "QA", "quality", "validation", "regression"

---

## Risk & Security (Priority 7-8)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/09_RISK_AND_SECURITY/RISK_REGISTER.md` | 8 | heading-based | all | Risk catalog |
| `docs/09_RISK_AND_SECURITY/FAILURE_MODES.md` | 8 | heading-based | ai_agent, maintainer | What can fail |
| `docs/09_RISK_AND_SECURITY/SECURITY_NOTES.md` | 7 | heading-based | auditor | Security concerns |
| `docs/09_RISK_AND_SECURITY/DATA_SAFETY.md` | 8 | heading-based | ai_agent | Data protection |
| `docs/09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md` | 10 | heading-based | ai_agent | Safety boundaries |
| `docs/09_RISK_AND_SECURITY/DOCUMENTATION_DRIFT_RISKS.md` | 6 | heading-based | maintainer | Doc staleness |
| `docs/09_RISK_AND_SECURITY/RAGD_STALENESS_RISKS.md` | 6 | heading-based | maintainer | RAGD staleness |

**Retrieval Hint:** "risk", "security", "safety", "what can go wrong", "failure modes"

---

## Roadmap & Planning (Priority 6)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/06_ROADMAP/MASTER_ROADMAP.md` | 6 | heading-based | owner, maintainer | Full roadmap |
| `docs/06_ROADMAP/PHASE_0_CURRENT_STATE.md` | 6 | heading-based | all | Current state |
| `docs/06_ROADMAP/PHASE_1_STABILIZATION.md` | 6 | heading-based | owner, maintainer | Phase 1 plan |
| `docs/06_ROADMAP/PHASE_2_RAGD_EXPANSION.md` | 6 | heading-based | owner, maintainer | Phase 2 plan |
| `docs/06_ROADMAP/PHASE_3_AGENT_AUTOMATION.md` | 6 | heading-based | owner, maintainer | Phase 3 plan |
| `docs/06_ROADMAP/PHASE_4_OBSIDIAN_SYNC.md` | 6 | heading-based | owner, maintainer | Phase 4 plan |
| `docs/06_ROADMAP/PHASE_5_LOCAL_LLM_LAYER.md` | 5 | heading-based | owner, maintainer | Phase 5 plan |
| `docs/06_ROADMAP/PHASE_6_MULTI_AGENT_WORKFLOWS.md` | 5 | heading-based | owner, maintainer | Phase 6 plan |

**Retrieval Hint:** "roadmap", "future plans", "what's next", "phase", "milestone"

---

## Decision Logs (Priority 6-7)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/10_DECISION_LOGS/DECISION_LOG_INDEX.md` | 7 | heading-based | all | ADR catalog |
| `docs/10_DECISION_LOGS/ADR_TEMPLATE.md` | 6 | full-doc | ai_agent | ADR format |
| `docs/10_DECISION_LOGS/ADR_0001_DOCUMENTATION_SYSTEM.md` | 7 | heading-based | all | Doc system ADR |
| `docs/10_DECISION_LOGS/ADR_0002_RAGD_DOC_STRUCTURE.md` | 7 | heading-based | all | RAGD structure ADR |
| `docs/10_DECISION_LOGS/ADR_0003_OBSIDIAN_VAULT_STRUCTURE.md` | 6 | heading-based | all | Vault structure ADR |
| `docs/10_DECISION_LOGS/ADR_0004_AGENT_HANDOFF_PROTOCOL.md` | 7 | heading-based | ai_agent | Handoff protocol ADR |

**Retrieval Hint:** "decision", "why did we choose", "ADR", "architecture decision"

---

## Prompts (Priority 6)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/11_PROMPTS/PROMPT_INDEX.md` | 6 | heading-based | ai_agent | Prompt catalog |
| `docs/11_PROMPTS/CODEX_REPO_AUDIT_PROMPT.md` | 6 | full-doc | ai_agent | Audit prompt |
| `docs/11_PROMPTS/CODEX_FEATURE_IMPLEMENTATION_PROMPT.md` | 6 | full-doc | ai_agent | Feature prompt |
| `docs/11_PROMPTS/CODEX_DOC_UPDATE_PROMPT.md` | 6 | full-doc | ai_agent | Doc update prompt |
| `docs/11_PROMPTS/CODEX_RAGD_UPDATE_PROMPT.md` | 6 | full-doc | ai_agent | RAGD update prompt |
| `docs/11_PROMPTS/CODEX_TESTING_PROMPT.md` | 6 | full-doc | ai_agent | Testing prompt |
| `docs/11_PROMPTS/CODEX_FINAL_REPORT_PROMPT.md` | 7 | full-doc | ai_agent | Report template |

**Retrieval Hint:** "prompt", "how to ask agent to", "agent template"

---

## Backlog (Priority 5)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/14_BACKLOG/BACKLOG_INDEX.md` | 5 | heading-based | owner, maintainer | Backlog catalog |
| `docs/14_BACKLOG/FEATURE_BACKLOG.md` | 5 | heading-based | owner, maintainer | Feature queue |
| `docs/14_BACKLOG/BUG_BACKLOG.md` | 5 | heading-based | maintainer | Bug queue |
| `docs/14_BACKLOG/TECH_DEBT_BACKLOG.md` | 5 | heading-based | maintainer | Debt queue |
| `docs/14_BACKLOG/DOCS_BACKLOG.md` | 5 | heading-based | maintainer | Doc gaps |
| `docs/14_BACKLOG/RAGD_BACKLOG.md` | 5 | heading-based | maintainer | RAGD improvements |

**Retrieval Hint:** "backlog", "what needs to be done", "pending work", "TODO"

---

## Research Notes (Priority 4-5)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/07_RESEARCH/LOCAL_LLM_RESEARCH.md` | 5 | heading-based | owner, maintainer | Local LLM notes |
| `docs/07_RESEARCH/RAG_SYSTEM_DESIGN_RESEARCH.md` | 5 | heading-based | owner, maintainer | RAG design |
| `docs/07_RESEARCH/MULTI_AGENT_SYSTEMS_RESEARCH.md` | 5 | heading-based | owner, maintainer | Multi-agent notes |
| `docs/07_RESEARCH/OBSIDIAN_AS_KNOWLEDGE_GRAPH.md` | 4 | heading-based | owner | Obsidian research |

**Retrieval Hint:** "research", "investigation", "future idea", "experiment"

---

## Future State (Priority 4-5)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/15_FUTURE_STATE/FUTURE_STATE_VISION.md` | 5 | heading-based | owner, maintainer | Long-term vision |
| `docs/15_FUTURE_STATE/LOCAL_LLM_RESEARCH_LAYER.md` | 4 | heading-based | owner | Local LLM plan |
| `docs/15_FUTURE_STATE/RAGD_SUPERINDEX_PLAN.md` | 4 | heading-based | owner | RAGD scaling |
| `docs/15_FUTURE_STATE/MULTI_AGENT_ORCHESTRATION_PLAN.md` | 4 | heading-based | owner | Multi-agent plan |

**Retrieval Hint:** "future", "vision", "long-term", "ambitious"

---

## System Maps (Priority 6)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `docs/13_SYSTEM_MAPS/SYSTEM_MAP_INDEX.md` | 6 | heading-based | all | Map catalog |
| `docs/13_SYSTEM_MAPS/REPO_MAP.md` | 6 | semantic | all | Repo structure diagram |
| `docs/13_SYSTEM_MAPS/RAGD_MAP.md` | 6 | semantic | all | RAGD diagram |
| `docs/13_SYSTEM_MAPS/DATA_FLOW_MAP.md` | 7 | semantic | ai_agent, maintainer | Data flow diagram |
| `docs/13_SYSTEM_MAPS/AGENT_MAP.md` | 6 | semantic | ai_agent | Agent workflow diagram |

**Retrieval Hint:** "diagram", "map", "visual", "flow chart"

---

## Historical Reports (Priority 3-4)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `/reports/*.md` | 3 | heading-based | owner, maintainer | Historical context |
| `/PROGRESS.md` | 4 | heading-based | owner, maintainer | Change log |

**Retrieval Hint:** "history", "what changed", "past work"

---

## Existing Docs (Priority varies)

| File | Priority | Chunking | Audience | Notes |
|---|---:|---|---|---|
| `/README.md` | 9 | heading-based | all | Repo overview |
| `/QUICKSTART.md` | 8 | heading-based | all | Quick start |
| `docs/DOMINION_V2.md` | 8 | heading-based | all | V2 overview |
| `docs/DOMDATA.md` | 8 | heading-based | ai_agent | domdata docs |
| `docs/DATA_PIPELINE.md` | 8 | heading-based | all | Pipeline docs |
| `docs/NATIVE_CORE.md` | 7 | heading-based | ai_agent, maintainer | C++ core docs |
| `docs/PLATFORM_LAYOUT.md` | 7 | heading-based | all | Platform structure |
| `docs/ENGINEERING_STANDARDS.md` | 7 | heading-based | ai_agent | Standards |
| `docs/RAGD_CODEX_WORKFLOW.md` | 8 | heading-based | ai_agent | RAGD+Codex workflow |
| `docs/CODEX_WORKFLOW.md` | 7 | heading-based | ai_agent | Codex workflow |
| `docs/COMMAND_CENTER.md` | 6 | heading-based | all | Command reference |
| `docs/RUNBOOK.md` | 7 | heading-based | maintainer | Ops runbook |
| `docs/COLLABORATION.md` | 6 | heading-based | owner | Collab workflow |
| `docs/TMUX_WORKFLOW.md` | 5 | heading-based | owner | tmux guide |
| `docs/SECURITY.md` | 8 | heading-based | auditor | Security notes |
| `docs/agents/*.md` | 7-8 | heading-based | ai_agent, maintainer | Agent OS docs |

**Retrieval Hint:** Various (system-specific)

---

## Ingestion Strategy

### Priority Tiers

**Tier 1 (Priority 9-10):** Index immediately, high boost
- Agent operating manuals
- Safety rules
- Current state docs
- Platform contract

**Tier 2 (Priority 7-8):** Index early, medium boost
- Architecture docs
- Feature specs
- Development standards
- RAGD system docs
- Risk & security

**Tier 3 (Priority 5-6):** Index normally, no boost
- Roadmap
- Decision logs
- Prompts
- Backlog
- System maps

**Tier 4 (Priority 3-4):** Index late, low priority
- Research notes
- Future vision
- Historical reports

**Tier 5 (Priority 1-2):** Index only if space allows
- Archive material
- Deprecated docs

### Chunking Defaults

- **Markdown docs:** heading-based (split on `##` headers)
- **Code files:** semantic (AST-aware)
- **Diagrams:** full-doc (preserve context)
- **Short files (<500 words):** full-doc
- **Long files (>5000 words):** heading-based with 200-char overlap

### Metadata Extraction

RAGD should extract from frontmatter:
- `doc_type` → filter by type
- `system` → filter by subsystem
- `ragd_priority` → boost factor
- `audience` → filter by intended reader
- `status` → exclude deprecated unless explicitly requested
- `last_reviewed` → staleness detection
- `tags` → additional filtering

### Refresh Strategy

- **Priority 9-10:** Re-index on every change
- **Priority 7-8:** Re-index daily
- **Priority 5-6:** Re-index weekly
- **Priority 3-4:** Re-index monthly
- **Priority 1-2:** Re-index manually

---

## Retrieval Hints

Common queries that should work well:

| Query | Expected Result | Priority Docs |
|---|---|---|
| "how to start as agent" | AGENT_README.md | P10 |
| "agent workflow" | AGENT_OPERATING_SYSTEM.md | P10 |
| "safety rules" | AGENT_SAFETY_RULES.md | P10 |
| "system architecture" | SYSTEM_OVERVIEW.md | P9 |
| "data flow" | DATA_FLOW.md | P9 |
| "how RAGD works" | RAGD_OVERVIEW.md | P9 |
| "coding standards" | CODING_STANDARDS.md | P9 |
| "how to test" | TESTING_GUIDE.md | P7 |
| "what features exist" | FEATURE_INDEX.md | P8 |
| "data pipeline design" | DATA_PIPELINE_FEATURE.md | P8 |
| "what can go wrong" | FAILURE_MODES.md, RISK_REGISTER.md | P8 |
| "future plans" | MASTER_ROADMAP.md | P6 |
| "why did we decide X" | DECISION_LOG_INDEX.md | P7 |
| "prompt for feature" | CODEX_FEATURE_IMPLEMENTATION_PROMPT.md | P6 |

---

## Quality Control

### Before Indexing

- [ ] Doc has frontmatter metadata
- [ ] Priority level is appropriate
- [ ] Chunking strategy matches doc structure
- [ ] Audience is clearly defined
- [ ] Status is current (not deprecated)
- [ ] Last_reviewed date is recent

### After Indexing

- [ ] Run test queries
- [ ] Verify priority docs appear first
- [ ] Check chunk sizes (target 500-2000 chars)
- [ ] Verify metadata is extractable
- [ ] Check for duplicate chunks
- [ ] Validate cross-references work

### Maintenance

- [ ] Re-index changed files
- [ ] Purge deprecated docs
- [ ] Update priorities quarterly
- [ ] Audit staleness (last_reviewed > 90 days)
- [ ] Check chunk quality (run sample retrieval tests)

---

## Tools

### Rebuild RAGD Index

```bash
# Dry run (see what would change)
python scripts/dominion_cli.py scan --dry-run --json

# Full rebuild
python scripts/dominion_cli.py scan
```

### Check Embedding Coverage

```bash
python scripts/dominion_cli.py embed stats --json
```

### Run Retrieval Tests

```bash
python scripts/dominion_cli.py search "agent workflow" --top-k 5 --json
python -m pytest -q dominion_ai/tests/test_eval.py
```

### Audit Doc Staleness

```bash
# Find docs not reviewed in 90 days
find docs/ -name "*.md" -exec grep -L "last_reviewed: 202[6-9]" {} \;
```

---

## Future Enhancements

- **Auto-priority inference:** ML model predicts priority from doc content
- **Semantic clustering:** Group related docs for context-aware chunking
- **Query rewriting:** Expand user queries with synonyms/related terms
- **Chunk quality scoring:** Flag low-quality chunks for rewrite
- **Auto-tagging:** Extract tags from doc content
- **Duplicate detection:** Find semantically duplicate chunks
- **Cross-reference validation:** Check all `[[links]]` are indexed
- **Version tracking:** Store multiple versions of same doc

---

**Last Audit:** 2026-05-19  
**Next Audit:** 2026-06-19  
**Maintained By:** Agent + Owner

---

**Remember:** High-quality RAGD ingestion = high-quality agent context = fewer mistakes.
