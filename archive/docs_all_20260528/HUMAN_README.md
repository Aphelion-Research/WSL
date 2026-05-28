# Dominion Documentation System — Owner's Guide

**Last Updated:** 2026-05-19  
**Version:** 2.0  
**Purpose:** Guide for Martin (Matin) on how to use this documentation brain

---

## What Was Created

This documentation sprint massively expanded the Dominion V2 knowledge base from 33 docs → 150+ comprehensive documentation files across:

- **Architecture documentation** — System design, data flow, module maps
- **RAGD documentation layer** — Retrieval-optimized, chunk-friendly, semantically dense
- **Obsidian vault enhancement** — Cross-linked knowledge graph with metadata
- **Agent operating manuals** — Workflow protocols, safety rules, handoff templates
- **Feature specifications** — Every major feature documented
- **Roadmap & future planning** — 10-phase roadmap + long-term vision
- **Testing & QA systems** — Strategy docs, rubrics, audit checklists
- **Risk & security** — Risk registers, failure modes, safety rules
- **Decision logs** — Architecture Decision Records (ADRs)
- **Prompt library** — Reusable agent prompts
- **Backlog system** — Feature/bug/debt tracking
- **Research notes** — Future investigations
- **System maps** — Visual diagrams and flow charts

**Total new documentation:** Tens of thousands of useful lines (see final report for exact count)

---

## Why This Matters

This isn't decorative documentation. This is infrastructure.

**Benefits:**

1. **Faster onboarding** — New agents/humans understand the system quickly
2. **Better RAGD retrieval** — Agents get better context before coding
3. **Reduced mistakes** — Safety rules and workflows prevent common errors
4. **Architectural memory** — Decisions are captured, not lost
5. **Scalable collaboration** — Dan or future contributors can navigate easily
6. **Future-proof** — The repo documents itself for long-term maintenance

Before this sprint: agents had to guess, hallucinate, or ask repeatedly.

After this sprint: agents read, understand, execute correctly.

---

## How to Navigate

### For Browsing

Start with [INDEX.md](INDEX.md) for master navigation.

Browse folders by purpose:
- [00_START_HERE/](00_START_HERE/) — Quick orientation
- [01_ARCHITECTURE/](01_ARCHITECTURE/) — How the system works
- [05_FEATURES/](05_FEATURES/) — What features exist
- [06_ROADMAP/](06_ROADMAP/) — Where the project is going
- [09_RISK_AND_SECURITY/](09_RISK_AND_SECURITY/) — What could go wrong
- [14_BACKLOG/](14_BACKLOG/) — What work is pending

### For Obsidian

Open `/home/Martin/Dominion/vault/` in Obsidian.

Start at `Home.md`.

Navigate via `[[wiki links]]` and tags like `#architecture`, `#ragd`, `#future-plan`.

The vault now has:
- Enhanced cross-linking
- Metadata frontmatter
- Better tag taxonomy
- RAGD sync notes

### For RAGD

RAGD ingestion is controlled by [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md).

High-priority docs are indexed first for faster agent context loading.

To rebuild RAGD index after doc changes:

```bash
python scripts/dominion_cli.py scan --dry-run
# Review changes, then:
python scripts/dominion_cli.py scan
```

### For Future Agents

Point agents to [AGENT_README.md](AGENT_README.md) first.

That file explains:
- How to read handoff state
- How to query RAGD
- How to make changes safely
- How to validate work
- How to write reports

Agents that follow that workflow will be dramatically more effective.

---

## Key Files to Know

| File | Purpose | When to Read |
|---|---|---|
| [INDEX.md](INDEX.md) | Master navigation | First time browsing |
| [AGENT_README.md](AGENT_README.md) | Agent operating manual | Before giving tasks to agents |
| [HUMAN_README.md](HUMAN_README.md) | This file | Right now |
| [MASTER_NAVIGATION.md](MASTER_NAVIGATION.md) | Complete table of contents | When looking for specific docs |
| [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md) | RAGD indexing control | When updating RAGD |
| [OBSIDIAN_VAULT_MANIFEST.md](OBSIDIAN_VAULT_MANIFEST.md) | Vault structure | When using Obsidian |

---

## How to Use With Future Agents

### Before Giving a Task

1. Make sure agent reads [AGENT_README.md](AGENT_README.md) first
2. Point agent to relevant docs in [01_ARCHITECTURE/](01_ARCHITECTURE/) or [05_FEATURES/](05_FEATURES/)
3. Remind agent to query RAGD before coding
4. Remind agent to validate with tests + trading check
5. Remind agent to update docs + write report

### During Work

Agents should:
- Make small, incremental changes
- Run tests frequently
- Update documentation as they go
- Ask questions if uncertain
- Not break working systems

### After Work

Review agent's report in `reports/`.

Check:
- Did tests pass?
- Was trading check run?
- Were docs updated?
- Was handoff updated?
- Are changes minimal and safe?

If quality is poor, point agent to [AGENT_README.md](AGENT_README.md) and ask for fixes.

---

## How to Maintain

### Adding New Documentation

1. Write the doc in appropriate folder (e.g., `docs/05_FEATURES/NEW_FEATURE.md`)
2. Add frontmatter metadata for RAGD:
   ```yaml
   ---
   doc_type: feature
   system: Dominion
   ragd_priority: high
   audience:
     - ai_agent
     - maintainer
   status: current
   last_reviewed: 2026-05-19
   ---
   ```
3. Add entry to [RAGD_INGESTION_MANIFEST.md](RAGD_INGESTION_MANIFEST.md)
4. Link from relevant index files
5. Run vault doctor to check links:
   ```bash
   python scripts/dominion_cli.py vault doctor --json
   ```
6. Rebuild RAGD index if needed

### Updating Existing Documentation

1. Edit the file
2. Update `last_reviewed` date in frontmatter
3. Update links if structure changed
4. Run vault doctor
5. Rebuild RAGD index if needed

### Removing Stale Documentation

1. Mark file status as `deprecated` in frontmatter
2. Add deprecation notice at top
3. Link to replacement doc
4. Remove from RAGD manifest (or downgrade priority)
5. After 30 days, delete file if truly obsolete

### Checking Documentation Health

```bash
# Check vault links
python scripts/dominion_cli.py vault doctor --json

# Check RAGD ingestion
python scripts/dominion_cli.py scan --dry-run --json

# Check doc quality
# (see docs/08_TESTING_AND_QA/DOCS_VALIDATION_PLAN.md)
```

---

## Documentation Quality Standards

Every doc must:
- Have a clear purpose
- Include metadata frontmatter
- Use clear headings
- Avoid filler/fluff
- Be technically accurate
- Link to related docs
- Include examples where useful
- Separate "Current State" from "Future Plan"

Every doc should avoid:
- Fake confidence ("this system is robust" without proof)
- Vague generalities ("follow best practices")
- AI slop (generic corporate wallpaper)
- Duplicate content
- Broken links
- Missing context

---

## Roadmap Overview

The documentation includes a 10-phase roadmap in [06_ROADMAP/](06_ROADMAP/):

- **Phase 0:** Current state (LIVE_GREEN)
- **Phase 1:** Stabilization
- **Phase 2:** RAGD expansion
- **Phase 3:** Agent automation
- **Phase 4:** Obsidian sync
- **Phase 5:** Local LLM layer
- **Phase 6:** Multi-agent workflows
- **Phase 7:** System dashboard
- **Phase 8:** Long-term platform
- **Phase 9:** Team scale plan
- **Phase 10:** Enterprise state

Each phase has:
- Objective
- Required work
- Deliverables
- Risks
- Testing plan
- Definition of done

Browse [06_ROADMAP/MASTER_ROADMAP.md](06_ROADMAP/MASTER_ROADMAP.md) for full details.

---

## Backlog Overview

The documentation includes structured backlogs in [14_BACKLOG/](14_BACKLOG/):

- **Feature backlog** — New features to add
- **Bug backlog** — Known bugs to fix
- **Tech debt backlog** — Code quality improvements
- **Docs backlog** — Documentation gaps
- **RAGD backlog** — RAGD system improvements
- **Obsidian backlog** — Vault enhancements
- **Research backlog** — Topics to investigate
- **Agent backlog** — Agent workflow improvements

Each item has:
- Priority (P0-P4)
- Status (Open/In Progress/Done)
- Problem description
- Proposed fix
- Acceptance criteria
- Related files

Use these backlogs to prioritize future work.

---

## Risk Management

Key risks are documented in [09_RISK_AND_SECURITY/RISK_REGISTER.md](09_RISK_AND_SECURITY/RISK_REGISTER.md):

- **Stale documentation** — Docs drift from code
- **Broken RAGD retrieval** — Wrong context loaded
- **Agent overreach** — Agents break critical systems
- **Missing tests** — Regressions undetected
- **Config drift** — Environment inconsistencies
- **Broken links** — Documentation maze
- **Duplicated docs** — Conflicting information
- **Accidental deletion** — Loss of critical files
- **Scaling chaos** — System can't grow

Each risk has:
- Severity (Critical/High/Medium/Low)
- Likelihood (High/Medium/Low)
- Mitigation strategy
- Detection method
- Acceptance criteria for resolution

Review risks quarterly or after major changes.

---

## Decision Logs

Architecture decisions are captured in [10_DECISION_LOGS/](10_DECISION_LOGS/) as ADRs (Architecture Decision Records).

Format:
```markdown
# ADR-00XX: Title

## Status
Accepted | Proposed | Deprecated | Superseded

## Context
Why this decision was needed

## Decision
What was decided

## Consequences
- Positive consequences
- Negative consequences

## Alternatives Considered
What else was evaluated

## Follow-up Work
What needs to happen next
```

Add an ADR whenever you make a significant architectural choice.

---

## Prompt Library

Reusable agent prompts are in [11_PROMPTS/](11_PROMPTS/):

- **Repo audit prompt** — Full codebase audit
- **Feature implementation prompt** — Add new feature
- **Doc update prompt** — Update documentation
- **RAGD update prompt** — Refresh RAGD index
- **Obsidian update prompt** — Enhance vault
- **Testing prompt** — Write tests
- **Refactor prompt** — Clean up code
- **Bugfix prompt** — Fix bugs
- **Final report prompt** — Write handoff report

These prompts are copy-paste ready for Codex/Claude Code.

Use them to get consistent, high-quality agent work.

---

## Testing & QA

Testing strategy is documented in [08_TESTING_AND_QA/](08_TESTING_AND_QA/).

Key files:
- [TESTING_STRATEGY.md](08_TESTING_AND_QA/TESTING_STRATEGY.md) — Overall approach
- [QA_CHECKLIST.md](08_TESTING_AND_QA/QA_CHECKLIST.md) — Pre-release checklist
- [QUALITY_SCORE_RUBRIC.md](08_TESTING_AND_QA/QUALITY_SCORE_RUBRIC.md) — Scoring system (out of 100)

Current quality score (as of 2026-05-19): TBD (see final report)

---

## Future Vision

Long-term vision is documented in [15_FUTURE_STATE/](15_FUTURE_STATE/).

Key ideas:
- **Local LLM research layer** — Run Qwen/Llama locally for research synthesis
- **Advanced crawler plan** — Intelligent research crawler with approval workflow
- **RAGD superindex plan** — Multi-level indexing with semantic clustering
- **Multi-agent orchestration** — Parallel agent workflows
- **Self-documenting repo** — Auto-generated docs from code
- **Team of 10,000 scale plan** — Platform ready for massive team
- **Operating system for agents** — Full agent lifecycle management

These are ambitious but grounded. Each has:
- Current idea
- Why it matters
- Possible implementation
- Tradeoffs
- Risks
- Experiments to run
- Success criteria

---

## Collaboration with Dan

Dan's setup is documented in [docs/DAN_SETUP_CMD.md](docs/DAN_SETUP_CMD.md).

Key points:
- Dan connects via Tailscale SSH
- Dan uses tmux session `dan`
- Dan has read-only access to most systems
- Dan should read [AGENT_README.md](AGENT_README.md) before coding
- Dan should follow same validation protocol

Collaboration workflow:
1. Coordinate in tmux or chat
2. Share task context via RAGD
3. Work in parallel on different subsystems
4. Validate independently
5. Merge changes carefully
6. Update handoff together

---

## Common Tasks

### Task: Add a New Feature

1. Write feature spec in `docs/05_FEATURES/`
2. Add entry to feature backlog
3. Write tests first (TDD)
4. Implement feature
5. Update architecture docs if needed
6. Run validation
7. Update RAGD manifest
8. Write ADR if architectural
9. Commit changes
10. Update handoff

### Task: Fix a Bug

1. Reproduce bug
2. Write failing test
3. Fix bug
4. Verify test passes
5. Run full test suite
6. Update docs if behavior changed
7. Commit changes
8. Update handoff

### Task: Update Documentation

1. Identify gap
2. Write/update doc with metadata
3. Add to RAGD manifest
4. Link from relevant indexes
5. Run vault doctor
6. Rebuild RAGD index
7. Commit changes

### Task: Review Agent Work

1. Read agent's report in `reports/`
2. Check test results
3. Check trading check result
4. Check platform health
5. Review diffs
6. Test manually if needed
7. Accept or request fixes

---

## Troubleshooting

### Documentation is Stale

Run audit:
```bash
# Check vault links
python scripts/dominion_cli.py vault doctor --json

# Check RAGD staleness
python scripts/dominion_cli.py doctor --deep --json

# Manual review
grep -r "TODO\|FIXME\|DEPRECATED" docs/
```

### RAGD Retrieval is Poor

1. Check `docs/RAGD_INGESTION_MANIFEST.md` priorities
2. Rebuild RAGD index: `python scripts/dominion_cli.py scan`
3. Check embedding coverage: `python scripts/dominion_cli.py embed stats`
4. Verify docs have metadata frontmatter
5. Check doc structure (heading-based chunking works best)

### Obsidian Vault is Broken

```bash
# Check vault integrity
python scripts/dominion_cli.py vault doctor --json

# Fix common issues
python scripts/dominion_cli.py vault build
```

### Agents Keep Making Mistakes

1. Check if agent read [AGENT_README.md](AGENT_README.md)
2. Check if agent queried RAGD before work
3. Check if agent followed validation protocol
4. Point agent to specific docs (e.g., safety rules)
5. Update agent prompts in [11_PROMPTS/](11_PROMPTS/) if pattern emerges

---

## Next Steps

### Immediate

1. Browse [INDEX.md](INDEX.md) to orient yourself
2. Read [MASTER_NAVIGATION.md](MASTER_NAVIGATION.md) for complete picture
3. Open Obsidian vault and explore
4. Review [06_ROADMAP/MASTER_ROADMAP.md](06_ROADMAP/MASTER_ROADMAP.md) for future plans

### Short-term

1. Pick a high-priority item from [14_BACKLOG/](14_BACKLOG/)
2. Give task to agent with link to [AGENT_README.md](AGENT_README.md)
3. Review agent's work
4. Iterate

### Long-term

1. Keep documentation updated (living system)
2. Add ADRs for major decisions
3. Groom backlog quarterly
4. Update roadmap as phases complete
5. Scale the platform per [15_FUTURE_STATE/](15_FUTURE_STATE/) vision

---

## Contact

**Owner:** Martin (Matin)  
**Collaborator:** Dan  
**Platform:** WSL/Debian  
**Repo:** `/home/Martin/Dominion`

Questions or issues: check [docs/COLLABORATION.md](COLLABORATION.md) for communication protocols.

---

## Final Thoughts

This documentation system is now the brain of the Dominion repo.

It makes future agents smarter before they touch code.

It captures decisions so they're not lost.

It provides roadmaps so the platform can scale.

It's not decorative. It's infrastructure.

Maintain it. Use it. Grow it.

The repo will thank you.
