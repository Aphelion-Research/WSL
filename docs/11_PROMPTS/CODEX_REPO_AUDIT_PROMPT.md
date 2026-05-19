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
  - audit
  - onboarding
---

# CODEX Repository Audit Prompt

**Use Case:** Initial repository audit  
**Complexity:** High  
**Duration:** 30-60 minutes

---

## Context

You are a Claude Code agent auditing the Dominion V2 repository for the first time (or after long gap >1 week).

Dominion is local-first quantitative research workstation for XAU/USD trading analysis. Core layers: RAGD (memory), domdata (MT5 bridge), data pipeline (5 sources + 400 features), microstructure (LOB/Exec/TCA/Toxicity/Features), Agent OS (safety + lifecycle), Vault (878 Obsidian notes).

Repository: `/home/Martin/Dominion`

---

## Mission

Build comprehensive mental model of codebase:
1. Module structure + dependencies
2. Current health (tests, platform status)
3. Recent changes (git log)
4. Architecture patterns
5. Known issues + risks
6. Documentation quality

Output: Audit report for future reference.

---

## Constraints

**Safety (CRITICAL):**
- Never run trading code (`order_send`, `order_check`, `TRADE_ACTION_*` forbidden)
- Never read secrets/ contents (existence checks OK)
- Never destructive operations (no `rm`, no `git reset --hard`)

**Scope:**
- Read-only operations only
- Focus on understanding, not fixing
- Note issues, don't fix yet (unless blocking audit)

**Time:**
- Target 30-60 minutes
- Prioritize breadth over depth

---

## Workflow

### Step 1: Platform Health (5 min)

```bash
# Quick validation
python domdata/check_no_trading.py
python scripts/dominion_cli.py doctor --offline --json
python scripts/dominion_cli.py status

# Test suite
python -m pytest -q
ctest --test-dir ragd/build --output-on-failure
```

**Record:**
- Test results (pass/fail counts)
- Platform status (LIVE_GREEN vs BROKEN)
- Known warnings

### Step 2: Repository Structure (10 min)

```bash
# Top-level layout
ls -la

# Module count
find . -maxdepth 1 -type d | wc -l

# Python packages
find . -name "__init__.py" | head -20

# C++ modules
find ragd/ -name "*.cpp" | wc -l

# Documentation
find docs/ -name "*.md" | wc -l
```

**Record:**
- Module list (dominion_*, data_pipeline/, lob/, exec_sim/, tca/, toxicity/, exec_features/)
- Doc count
- Native code presence (ragd/)

### Step 3: Recent Changes (5 min)

```bash
# Last 10 commits
git log --oneline -10

# Recent activity
git log --since="1 week ago" --oneline

# Current branch
git status
```

**Record:**
- Recent work themes
- Active branches
- Uncommitted changes

### Step 4: Module Dependencies (15 min)

Read key files:
- `/AGENT_HANDOFF.md` — Current state
- `docs/00_START_HERE/OVERVIEW.md` — System overview
- `docs/01_ARCHITECTURE/MODULE_MAP.md` — Module dependencies
- `docs/01_ARCHITECTURE/DATA_FLOW.md` — Data flow

**Query RAGD:**
```bash
python scripts/dominion_cli.py search "module dependencies" --top-k 3
python scripts/dominion_cli.py search "architecture overview" --top-k 3
```

**Record:**
- Critical modules (domdata, RAGD, data_pipeline, Agent OS)
- Dependency graph (who depends on whom)
- Circular dependencies (if any)

### Step 5: Code Quality Scan (10 min)

```bash
# Python file count + classification
python scripts/dominion_cli.py scan --dry-run --json | jq '.files_scanned'

# Test coverage (if available)
python -m pytest --cov=. --cov-report=term-missing -q 2>/dev/null | tail -20

# Known issues
grep -r "TODO\|FIXME\|HACK" --include="*.py" | head -20
```

**Record:**
- File count
- Test coverage (if available)
- TODO/FIXME count

### Step 6: Documentation Assessment (10 min)

```bash
# Doc structure
ls docs/

# Vault status
python scripts/dominion_cli.py vault doctor --json | jq '.total_notes, .broken_links | length'

# RAGD index
curl -s http://127.0.0.1:7474/health | jq '.active_chunks'
```

**Record:**
- Doc folder count (should be 15)
- Vault notes count (~900+)
- Broken links count
- RAGD chunk count (~7K+)

### Step 7: Risk Assessment (5 min)

Read:
- `docs/09_RISK_AND_SECURITY/RISK_REGISTER.md`
- `docs/09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md`

**Record:**
- Critical risks (R001 Trading Code, R002 Secret Leakage)
- Current mitigations
- Open risks

---

## Validation

Audit complete when you can answer:

1. **Health:** What is platform status? (LIVE_GREEN, LIVE_WARN, BROKEN)
2. **Tests:** How many tests pass/fail? (Python + C++)
3. **Structure:** What are top 10 modules?
4. **Dependencies:** What depends on RAGD? What depends on domdata?
5. **Recent work:** What was last major feature added?
6. **Issues:** What are top 3 known issues?
7. **Docs:** How many docs exist? Any broken links?
8. **Safety:** Are trading tokens present? (Should be NO)

---

## Output

Write audit report: `AGENT_REPO_AUDIT_[DATE].md`

**Template:**

```markdown
---
audit_date: YYYY-MM-DD
agent: Claude Sonnet 4.5
duration_minutes: XX
---

# Repository Audit Report

## Platform Health

- Status: [LIVE_GREEN | LIVE_WARN | BROKEN]
- Python tests: XX/XX passing
- C++ tests: XX/XX passing
- Trading check: [PASS | FAIL]
- RAGD daemon: [Running | Down]

## Repository Structure

- Total modules: XX
- Python packages: [list top 10]
- Native code: XX C++ files
- Documentation: XX markdown files
- Vault notes: XX notes, XX broken links
- RAGD chunks: XX active

## Module Dependencies

[List critical modules + dependencies]

## Recent Changes

[Last 5 commits summary]

## Code Quality

- File count: XX
- TODO/FIXME: XX
- Test coverage: XX% (if available)

## Known Issues

1. [Issue 1]
2. [Issue 2]
3. [Issue 3]

## Risk Assessment

- Critical risks: [R001, R002, ...]
- Mitigations in place: [describe]

## Documentation Quality

- Doc coverage: [Good | Gaps | Missing]
- Broken links: XX
- Stale docs: [list if any]

## Recommendations

1. [Rec 1]
2. [Rec 2]
3. [Rec 3]

## Next Steps

[Suggested next task based on audit findings]
```

---

## Common Pitfalls

**Don't:**
- Run code without understanding (no blind execution)
- Fix issues during audit (note them, fix later)
- Read secrets/ contents (forbidden)
- Spend >60 min (breadth over depth)

**Do:**
- Query RAGD for context before deep-dives
- Note questions for future investigation
- Prioritize critical modules (domdata, RAGD, data_pipeline)
- Validate trading safety first

---

## Follow-Up

After audit, likely next prompt:
- If issues found: CODEX_BUGFIX_PROMPT
- If new feature needed: CODEX_FEATURE_IMPLEMENTATION_PROMPT
- If docs stale: CODEX_DOC_UPDATE_PROMPT
- If tests failing: CODEX_TESTING_PROMPT

---

## Related Prompts

- [[CODEX_HEALTH_CHECK_PROMPT]] — Quick health validation
- [[CODEX_DOC_UPDATE_PROMPT]] — Update docs after audit

---

## Retrieval Hints

- "repo audit"
- "codebase audit"
- "initial assessment"
- "repository overview"
