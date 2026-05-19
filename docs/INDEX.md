# Dominion Documentation Index

**Last Updated:** 2026-05-19  
**Purpose:** Master navigation for Dominion V2 documentation system

---

## What Is Dominion?

Dominion V2 is a local-first, agent-native quantitative research and engineering workstation running on WSL/Debian.

Core mission: sovereign quant research infrastructure for XAU/USD systematic trading analysis.

Core layers:
- **RAGD:** Persistent project memory, retrieval, handoffs, TODOs, MCP context
- **Codex:** Engineering workflow orchestration
- **Research OS:** Approved-source evidence collection + RAGD ingestion
- **domdata:** Read-only MT5/XAUUSD data bridge (Wine/MetaTrader5)
- **Data Pipeline:** Institutional-grade multi-source fusion + 400+ alpha features
- **Agent OS:** SQLite-backed agent lifecycle + safety rules + complexity budgets
- **Vault:** Obsidian-compatible knowledge graph (878+ notes, 0 broken links)
- **Native Core:** C++ spine for scan/manifest/doctor/vault operations (24/24 tests passing)

---

## What Is This Documentation System?

This documentation brain serves:
- **AI coding agents** (Codex/Claude Code) → agent operating manuals, handoff protocols, safety rules
- **Human maintainers** → architecture docs, runbooks, decision logs
- **RAGD retrieval system** → chunk-friendly, semantically dense, searchable docs
- **Obsidian vault** → cross-linked knowledge graph
- **Future scaling** → roadmaps, backlog, research notes, risk registers

This is not decorative. This is the repo's intelligence layer.

---

## Navigation for Humans

**Start here:**
- [HUMAN_README.md](HUMAN_README.md) — Owner's guide to the documentation system
- [00_START_HERE/OVERVIEW.md](00_START_HERE/OVERVIEW.md) — System overview
- [00_START_HERE/QUICKSTART.md](00_START_HERE/QUICKSTART.md) — Fast orientation

**Architecture:**
- [01_ARCHITECTURE/](01_ARCHITECTURE/) — System design, data flow, module map
- [13_SYSTEM_MAPS/](13_SYSTEM_MAPS/) — Diagrams and visual maps

**Development:**
- [04_DEVELOPMENT/](04_DEVELOPMENT/) — Coding standards, testing, debugging
- [05_FEATURES/](05_FEATURES/) — Feature specs and documentation
- [08_TESTING_AND_QA/](08_TESTING_AND_QA/) — Testing strategy and QA rubrics

**Operations:**
- [03_AGENT_OPERATIONS/](03_AGENT_OPERATIONS/) — AI agent workflows
- [02_RAGD/](02_RAGD/) — RAGD retrieval system docs
- [09_RISK_AND_SECURITY/](09_RISK_AND_SECURITY/) — Risk register, security, safety

**Planning:**
- [06_ROADMAP/](06_ROADMAP/) — Phased roadmap + future state
- [15_FUTURE_STATE/](15_FUTURE_STATE/) — Long-term vision
- [14_BACKLOG/](14_BACKLOG/) — Feature/bug/debt backlog
- [10_DECISION_LOGS/](10_DECISION_LOGS/) — Architecture Decision Records (ADRs)

**Research:**
- [07_RESEARCH/](07_RESEARCH/) — Research notes and investigations
- [11_PROMPTS/](11_PROMPTS/) — Agent prompt library

---

## Navigation for AI Agents

**Read first:**
1. [AGENT_README.md](AGENT_README.md) — Agent operating system contract
2. [03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md](03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md) — Workflow protocol
3. [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md) — Priority doc list

**Before editing code:**
1. Call `ragd_handoff_read` (or read [/AGENT_HANDOFF.md](/AGENT_HANDOFF.md))
2. Call `ragd_query` with task context
3. Read relevant architecture docs from [01_ARCHITECTURE/](01_ARCHITECTURE/)
4. Inspect files after understanding contracts
5. Make minimal diffs
6. Update docs after changes
7. Write handoff report

**Safety rules:**
- Read [09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md](09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md) before any code change
- Run `python domdata/check_no_trading.py` before claiming completion
- Never touch `secrets/` folder

---

## Navigation for RAGD

See [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md) for:
- Priority ordering
- Chunking strategy
- Metadata schema
- Retrieval hints

---

## Navigation for Obsidian

See [OBSIDIAN_VAULT_MANIFEST.md](OBSIDIAN_VAULT_MANIFEST.md) for vault structure and linking conventions.

Vault location: `/home/Martin/Dominion/vault/`

---

## Documentation Quality Standards

Every doc must serve one of:
- Explain current system
- Guide future implementation
- Improve RAGD retrieval
- Improve Obsidian navigation
- Help agents operate safely
- Reduce technical debt
- Capture decisions
- Define next steps

No filler. No AI slop. No fake confidence. No hype.

Use:
- Clear headings
- Tables where useful
- Mermaid diagrams when useful
- Checklists for operations
- Frontmatter metadata for RAGD/Obsidian
- "Current Known State" vs "Future Plan" separation

---

## Folder Overview

| Folder | Purpose | Primary Audience |
|---|---|---|
| [00_START_HERE/](00_START_HERE/) | Orientation + quick start | Human, Agent |
| [01_ARCHITECTURE/](01_ARCHITECTURE/) | System design + data flow | Agent, Maintainer |
| [02_RAGD/](02_RAGD/) | RAGD system documentation | Agent, RAGD |
| [03_AGENT_OPERATIONS/](03_AGENT_OPERATIONS/) | Agent workflows + handoff protocol | Agent |
| [04_DEVELOPMENT/](04_DEVELOPMENT/) | Coding standards + testing | Agent, Maintainer |
| [05_FEATURES/](05_FEATURES/) | Feature specs + documentation | All |
| [06_ROADMAP/](06_ROADMAP/) | Phased roadmap + milestones | Owner, Maintainer |
| [07_RESEARCH/](07_RESEARCH/) | Research notes + investigations | Owner, Maintainer |
| [08_TESTING_AND_QA/](08_TESTING_AND_QA/) | Testing strategy + QA rubrics | Agent, Maintainer |
| [09_RISK_AND_SECURITY/](09_RISK_AND_SECURITY/) | Risk + security + safety | Agent, Auditor |
| [10_DECISION_LOGS/](10_DECISION_LOGS/) | Architecture Decision Records | All |
| [11_PROMPTS/](11_PROMPTS/) | Agent prompt library | Agent |
| [13_SYSTEM_MAPS/](13_SYSTEM_MAPS/) | Diagrams + visual maps | All |
| [14_BACKLOG/](14_BACKLOG/) | Feature/bug/debt backlog | Owner, Maintainer |
| [15_FUTURE_STATE/](15_FUTURE_STATE/) | Long-term vision + research | Owner, Maintainer |

---

## Key Files

| File | Purpose |
|---|---|
| [/README.md](/README.md) | Top-level repo README |
| [/AGENT_HANDOFF.md](/AGENT_HANDOFF.md) | Current agent handoff state |
| [/AGENTS.md](/AGENTS.md) | Platform contract for agents |
| [/PROGRESS.md](/PROGRESS.md) | Historical progress log |
| [/QUICKSTART.md](/QUICKSTART.md) | Fast start guide |
| [AGENT_README.md](AGENT_README.md) | Agent operating manual |
| [HUMAN_README.md](HUMAN_README.md) | Human owner's guide |
| [MASTER_NAVIGATION.md](MASTER_NAVIGATION.md) | Complete table of contents |
| [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md) | RAGD indexing manifest |
| [OBSIDIAN_VAULT_MANIFEST.md](OBSIDIAN_VAULT_MANIFEST.md) | Vault structure manifest |

---

## Documentation Stats

Current state (as of 2026-05-19):
- Documentation files: expanding from 33 → 150+ target
- Vault notes: 878 files, 0 broken links
- RAGD active chunks: 7159
- Tests passing: 426/426 Python, 24/24 C++
- Repository status: LIVE_GREEN

---

## How to Use This System

**For humans:**
1. Start with [HUMAN_README.md](HUMAN_README.md)
2. Browse [MASTER_NAVIGATION.md](MASTER_NAVIGATION.md) for complete index
3. Use Obsidian vault for knowledge graph navigation

**For AI agents:**
1. Start with [AGENT_README.md](AGENT_README.md)
2. Read [03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md](03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md)
3. Consult [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md) for context loading

**For RAGD:**
1. Ingest docs per [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md)
2. Use metadata for filtering
3. Chunk by heading structure

**For Obsidian:**
1. Open vault at `/home/Martin/Dominion/vault/`
2. Start at Home.md
3. Navigate via `[[wiki links]]` and tags

---

## Maintenance

This documentation system requires:
- Updates after major features
- Link validation (run vault doctor)
- RAGD manifest updates when adding docs
- ADR creation for architectural changes
- Backlog grooming
- Roadmap phase updates

Documentation is a first-class deliverable, not an afterthought.

---

## Contact

Owner: Martin (Matin)  
Collaborator: Dan  
Platform: WSL/Debian  
Repo: `/home/Martin/Dominion`

---

**Remember:** This documentation exists to make future agents and humans dramatically smarter before they touch code.
