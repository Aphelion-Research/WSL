---
created: 2026-05-19 18:15
modified: 2026-05-19 18:15
tags:
  - vault
  - navigation
  - entry-point
status: active
---

# Dominion Vault Home

**Purpose:** Entry point for Dominion Obsidian vault knowledge graph

**Status:** 930 notes, 26 broken template links (expected)

**Last Updated:** 2026-05-19

---

## Quick Navigation

### Start Here

- [[OVERVIEW]] — System overview (P9)
- [[QUICKSTART]] — 60-second orientation (P8)
- [[AGENT_README]] — Agent operating manual (P10)
- [[HUMAN_README]] — Owner's guide (P9)

### Core Documentation

#### Architecture
- [[SYSTEM_OVERVIEW]] — System architecture (P9)
- [[DATA_FLOW]] — Data flow maps with diagrams (P9)
- [[MODULE_MAP]] — Module dependencies (P8)
- [[REPO_STRUCTURE]] — Repository layout (P8)

#### RAGD System
- [[RAGD_OVERVIEW]] — RAGD system docs (P9)
- [[RAGD_CHUNKING_GUIDE]] — Chunking strategies (P8)
- [[RAGD_METADATA_SCHEMA]] — Metadata schema (P8)
- [[RAGD_QUERY_PATTERNS]] — Query patterns (P8)
- [[RAGD_AGENT_USAGE]] — Agent usage guide (P8)
- [[RAGD_INDEXING_STRATEGY]] — Indexing strategy (P8)

#### Agent Operations
- [[AGENT_OPERATING_SYSTEM]] — 13-step golden workflow (P10)
- [[AGENT_HANDOFF_PROTOCOL]] — Handoff format (P9)
- [[AGENT_WORKFLOW]] — Common workflows (P8)
- [[AGENT_CONTEXT_LOADING]] — Context loading (P8)
- [[AGENT_FINAL_REPORT_TEMPLATE]] — Report template (P7)

#### Development
- [[CODING_STANDARDS]] — Python/C++ style guide (P9)
- [[TESTING_GUIDE]] — Testing guide (P8)
- [[COMMIT_GUIDE]] — Conventional commits (P7)
- [[LOCAL_SETUP_GUIDE]] — First-time setup (P7)
- [[DEVELOPMENT_GUIDE]] — Dev workflow (P7)

#### Features
- [[FEATURE_INDEX]] — Feature catalog (P8)
- [[DATA_PIPELINE_FEATURE]] — Data pipeline spec (P8)

#### Roadmap & Planning
- [[MASTER_ROADMAP]] — 10-phase roadmap (P8)
- [[BACKLOG_INDEX]] — Backlog catalog (P7)

#### Testing & QA
- [[TESTING_STRATEGY]] — Testing strategy (P9)
- [[QA_CHECKLIST]] — Pre-release validation (P7)
- [[VERIFICATION]] — Verification procedures (P7)

#### Risk & Security
- [[AGENT_SAFETY_RULES]] — 10 safety rules (P10)
- [[RISK_REGISTER]] — Risk catalog (P7)

#### Decision Logs
- [[DECISION_LOG_INDEX]] — ADR catalog (P7)
- [[ADR_TEMPLATE]] — ADR template (P7)

---

## Navigation by Tag

### System Tags
- `#system` — System-level notes
- `#architecture` — Architecture docs
- `#ragd` — RAGD-related
- `#agent` — Agent operations
- `#feature` — Feature specs
- `#roadmap` — Planning docs
- `#decision` — ADRs
- `#risk` — Risk/security

### Priority Tags
- `#p0` — Critical (do not break)
- `#p1` — High priority
- `#p2` — Medium priority

### Subsystem Tags
- `#domdata` — MT5 data bridge
- `#data-pipeline` — Multi-source fusion
- `#microstructure` — LOB/Exec/TCA/Toxicity
- `#vault` — Obsidian vault

---

## Vault Structure

```
vault/
├── Home.md                    # This file (entry point)
├── _index/                    # Auto-generated indexes
│   ├── files-index.md
│   ├── symbols-index.md
│   └── daily-index.md
├── _daily/                    # Daily notes (YYYY-MM-DD.md)
├── _templates/                # Note templates
│   ├── Daily Changelog.md
│   ├── File Note.md
│   └── Symbol Note.md
├── files/                     # File snapshots (mirrored repo structure)
│   ├── docs/                  # Documentation brain
│   │   ├── 00_START_HERE/
│   │   ├── 01_ARCHITECTURE/
│   │   ├── 02_RAGD/
│   │   ├── 03_AGENT_OPERATIONS/
│   │   ├── 04_DEVELOPMENT/
│   │   ├── 05_FEATURES/
│   │   ├── 06_ROADMAP/
│   │   ├── 08_TESTING_AND_QA/
│   │   ├── 09_RISK_AND_SECURITY/
│   │   ├── 10_DECISION_LOGS/
│   │   ├── 14_BACKLOG/
│   │   └── agents/
│   ├── domdata/
│   ├── data_pipeline/
│   └── ...
├── symbols/                   # Code symbol notes
└── .obsidian/                 # Obsidian config
```

---

## Vault Maintenance

**Daily:**
- Create daily note
- Update work log
- Link related notes

**Weekly:**
- Review open notes
- Archive completed work
- Check for broken links: `dominion vault doctor --json`

**Monthly:**
- Audit tag usage
- Clean up duplicates
- Update templates
- Sync file snapshots: `python scripts/vault_sync.py`

---

## Related Docs

**Master indexes:**
- [[INDEX]] — Master navigation
- [[MASTER_NAVIGATION]] — Complete TOC
- [[RAGD_INGESTION_MANIFEST]] — RAGD indexing manifest (P9)
- [[OBSIDIAN_VAULT_MANIFEST]] — Vault structure manifest (P7)

**Technical:**
- [[DOMDATA]] — MT5 bridge
- [[DATA_PIPELINE]] — Data pipeline
- [[NATIVE_CORE]] — C++ spine
- [[COMMAND_CENTER]] — CLI tools

**Collaboration:**
- [[COLLABORATION]] — Collaboration guide
- [[TMUX_WORKFLOW]] — tmux sessions

---

## Retrieval Hints

- "vault home"
- "obsidian navigation"
- "where to start"
- "vault structure"
- "documentation index"
