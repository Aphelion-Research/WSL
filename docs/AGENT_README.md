# Agent Operating Manual

**Version:** 2.0  
**Last Updated:** 2026-05-19  
**Status:** LIVE_GREEN  
**Purpose:** First file every AI coding agent must read before touching Dominion repo

---

## Mission

You are operating inside **Dominion V2**, a local-first agent-native quantitative research workstation for systematic XAU/USD trading analysis.

Your job: improve the platform while preserving working systems.

This is not a greenfield project. This is a living, operational platform with:
- Working MT5/Wine data bridge (read-only, CRITICAL to preserve)
- Live RAGD daemon on 127.0.0.1:7474
- 426 passing Python tests + 24 passing C++ tests
- 878-note Obsidian vault with 0 broken links
- Active tmux sessions for collaboration
- Strict no-trading safety boundary

Break nothing. Improve incrementally. Document everything.

---

## Rules of Engagement

### 1. RAGD-First Workflow (MANDATORY)

Before any code change:

```bash
# Read handoff state
ragd_handoff_read
# or: cat /home/Martin/Dominion/AGENT_HANDOFF.md

# Query RAGD for task context
ragd_query "<your task description>" --top-k 5
# or: curl -X POST http://127.0.0.1:7474/query -d '{"q":"<query>","top_k":5}'

# Inspect relevant files after understanding context
# Make minimal diffs
# Validate changes
# Update documentation
```

After significant work:

```bash
# Remember important findings
ragd_remember "<your finding or decision>"
# or: python scripts/dominion_cli.py graph store --content "<content>"
```

### 2. Safety Boundaries (NON-NEGOTIABLE)

**Forbidden actions:**
- Never add live trading execution (order_send, order_check, TRADE_ACTION_*)
- Never print/copy/commit/log/document secrets from `secrets/`
- Never read `secrets/mt5.env` contents (existence checks OK)
- Never delete data/backups/secrets/history/user work unless explicitly requested
- Never break the MT5/Wine data bridge

**Required validation before claiming completion:**

```bash
python domdata/check_no_trading.py  # MUST PASS
python -m pytest -q                 # MUST PASS
ctest --test-dir ragd/build --output-on-failure  # MUST PASS (if C++ changed)
```

### 3. Minimal Diff Policy

- Prefer additive changes over rewrites
- Edit existing files, don't create duplicates
- One feature at a time
- Keep commits small and atomic
- Don't refactor code you're not changing

### 4. Documentation Protocol

After any significant change:

1. Update `/AGENT_HANDOFF.md` (current state section)
2. Update `docs/` if architecture changed
3. Update this file if agent workflow changed
4. Update RAGD manifest if docs changed
5. Write ADR if architectural decision made
6. Update backlog if work discovered
7. Write final report in `reports/`

---

## Repo Structure

```
/home/Martin/Dominion/
├── AGENT_HANDOFF.md          ← READ THIS FIRST (current state)
├── AGENTS.md                 ← Platform contract
├── README.md                 ← Repo overview
├── PROGRESS.md               ← Historical log
├── QUICKSTART.md             ← Fast start guide
├── docs/                     ← Documentation brain
│   ├── INDEX.md              ← Master navigation
│   ├── AGENT_README.md       ← THIS FILE
│   ├── 00_START_HERE/        ← Orientation
│   ├── 01_ARCHITECTURE/      ← System design
│   ├── 02_RAGD/              ← RAGD docs
│   ├── 03_AGENT_OPERATIONS/  ← Agent workflows
│   ├── 04_DEVELOPMENT/       ← Coding standards
│   ├── 05_FEATURES/          ← Feature specs
│   ├── 06_ROADMAP/           ← Future plans
│   ├── 09_RISK_AND_SECURITY/ ← Safety rules
│   ├── 10_DECISION_LOGS/     ← ADRs
│   └── 14_BACKLOG/           ← Work queue
├── vault/                    ← Obsidian knowledge graph (878 notes)
├── ragd/                     ← Native C++ RAGD core
├── domdata/                  ← MT5 data bridge (CRITICAL: read-only)
├── data_pipeline/            ← Multi-source fusion + 400+ features
├── dominion_agent/           ← Agent OS (lifecycle + safety)
├── dominion_ai/              ← RAG retrieval layer
├── dominion_loader/          ← Scan + manifest + cache
├── research_os/              ← Approved-source crawler
├── exec_sim/, lob/, tca/, toxicity/, exec_features/  ← Microstructure subsystems
├── scripts/                  ← CLI tools
├── tests/                    ← Test suite
└── reports/                  ← Historical reports
```

### Key Subsystems

| Subsystem | Purpose | Critical? | Tests |
|---|---|---|---|
| **RAGD** | Persistent memory + retrieval | YES | 24 C++ tests |
| **domdata** | MT5 data bridge (Wine) | YES | In check_no_trading.py |
| **data_pipeline** | 5-source fusion + features | YES | 16 tests |
| **dominion_agent** | Agent OS (safety + lifecycle) | YES | Included in 426 |
| **dominion_ai** | RAG retrieval layer | YES | Included in 426 |
| **dominion_loader** | Scan + manifest | YES | Included in 426 |
| **research_os** | Approved-source crawler | NO | 7 tests |
| **vault** | Obsidian knowledge graph | NO | Vault doctor |
| **exec_sim** | Execution simulator | NO | 8 tests |
| **lob** | LOB reconstruction | NO | 8 tests |
| **tca** | Transaction cost analysis | NO | 4 tests |
| **toxicity** | VPIN + toxicity monitoring | NO | 4 tests |
| **exec_features** | Execution alpha features | NO | 6 tests |

---

## Before You Start

### Step 1: Read Current State

```bash
cat /home/Martin/Dominion/AGENT_HANDOFF.md
```

This tells you:
- Current platform status
- Recent changes
- Known issues
- Validation baseline
- Next recommended task

### Step 2: Understand Your Task

Ask yourself:
- What am I trying to accomplish?
- Which subsystems does this touch?
- What could break?
- How will I validate?
- What docs need updating?

If unclear, ask the human for clarification.

### Step 3: Load Context

```bash
# Query RAGD for relevant docs
curl -X POST http://127.0.0.1:7474/query \
  -H 'Content-Type: application/json' \
  -d '{"q":"<your task>","top_k":5}'

# Or use dominion CLI
python scripts/dominion_cli.py search "<your task>" --top-k 5 --json
```

### Step 4: Inspect Code

Read the actual code in the relevant subsystems.

Do NOT assume. Do NOT hallucinate. Read the real files.

### Step 5: Make a Plan

Write down:
- Files you'll touch
- Changes you'll make
- Tests you'll add/update
- Docs you'll update
- Validation commands

If the plan is large, create tasks:

```bash
python scripts/dominion_cli.py agent task create \
  --name "<task name>" \
  --description "<task description>" \
  --priority high
```

---

## During Work

### Making Code Changes

1. **Make minimal diffs**
   - Change only what's necessary
   - Don't refactor unrelated code
   - Don't "clean up" things you're not fixing

2. **Follow existing patterns**
   - Match the style of surrounding code
   - Use existing abstractions
   - Don't introduce new patterns without justification

3. **Add tests**
   - New code needs tests
   - Changed behavior needs tests
   - Run tests after changes

4. **Handle errors gracefully**
   - Fail closed, not open
   - Log errors clearly
   - Don't swallow exceptions

5. **Avoid security vulnerabilities**
   - No command injection
   - No SQL injection
   - No XSS
   - No OWASP Top 10 violations

### Running Tests

```bash
# All Python tests
python -m pytest -q

# Specific subsystem
python -m pytest -q data_pipeline/tests/

# All C++ tests
ctest --test-dir ragd/build --output-on-failure

# Specific C++ test
ctest --test-dir ragd/build -R test_query -V

# Trading safety check
python domdata/check_no_trading.py
```

### Checking Platform Health

```bash
# Overall doctor check
python scripts/dominion_cli.py doctor --offline --json

# RAGD health
curl http://127.0.0.1:7474/health

# Vault integrity
python scripts/dominion_cli.py vault doctor --json

# Embedding stats
python scripts/dominion_cli.py embed stats --json

# Agent OS stats
python scripts/dominion_cli.py agent dashboard --json
```

---

## After Work

### Step 1: Validate Changes

Run ALL validation commands:

```bash
# Core validation (MANDATORY)
python domdata/check_no_trading.py  # MUST PASS
python -m pytest -q                 # MUST PASS
ctest --test-dir ragd/build --output-on-failure  # MUST PASS (if C++ changed)

# Platform validation (RECOMMENDED)
bash scripts/verify_live.sh         # Should show LIVE_GREEN
python scripts/dominion_cli.py doctor --offline --json  # Should be warn or ok
```

### Step 2: Update Documentation

Update these files as relevant:

1. `/AGENT_HANDOFF.md` — Current state section
2. `docs/01_ARCHITECTURE/` — If architecture changed
3. `docs/05_FEATURES/` — If feature added/changed
4. `docs/09_RISK_AND_SECURITY/RISK_REGISTER.md` — If new risks
5. `docs/10_DECISION_LOGS/` — If architectural decision
6. `docs/14_BACKLOG/` — If work discovered
7. `docs/RAGD_INGESTION_MANIFEST.md` — If docs added

### Step 3: Write Report

Create a report in `reports/`:

```bash
# Template
reports/<phase-name>-<YYYYMMDD-HHMMSS>.md
```

Report must include:
- **What changed** (files, features, tests)
- **Why it changed** (problem statement)
- **How to use it** (commands, examples)
- **Validation results** (test output, health checks)
- **Known limitations** (what's incomplete)
- **Next recommended task** (what should happen next)

### Step 4: Commit Changes

Use conventional commit format:

```bash
git add <files>
git commit -m "feat|fix|docs|refactor|test: <description>

<body explaining why>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

Do NOT:
- Commit secrets
- Commit large binaries
- Commit generated files (logs, caches, __pycache__, .venv)
- Commit test databases
- Force push to main
- Skip commit hooks

---

## Common Workflows

### Workflow 1: Adding a Feature

1. Read handoff + query RAGD
2. Write feature spec in `docs/05_FEATURES/`
3. Add tests first (TDD)
4. Implement feature
5. Update docs
6. Run validation
7. Write report
8. Commit

### Workflow 2: Fixing a Bug

1. Read handoff + query RAGD
2. Write failing test that reproduces bug
3. Fix bug
4. Verify test passes
5. Run full test suite
6. Update docs if behavior changed
7. Write report
8. Commit

### Workflow 3: Refactoring

1. Read handoff + query RAGD
2. Write ADR explaining why refactor is needed
3. Ensure tests exist for current behavior
4. Refactor incrementally
5. Run tests after each step
6. Update docs
7. Write report
8. Commit

### Workflow 4: Adding Documentation

1. Read existing docs to avoid duplication
2. Write new doc with frontmatter metadata
3. Add to RAGD_INGESTION_MANIFEST.md
4. Link from relevant index files
5. Run vault doctor to check links
6. Commit

---

## Failure Recovery

### If Tests Fail

1. **Don't skip or disable tests**
2. Read the test failure output carefully
3. Understand what the test is checking
4. Fix the underlying issue
5. If test is wrong, fix the test (with justification)

### If Trading Check Fails

1. **STOP IMMEDIATELY**
2. Do NOT commit
3. Find and remove trading-related code
4. Run check again
5. If false positive, update allowlist in `config/forbidden_tokens.json`

### If Platform Health Degrades

1. Run `python scripts/dominion_cli.py doctor --offline --json`
2. Read the errors carefully
3. Fix issues one by one
4. Re-run doctor after each fix
5. Don't proceed until doctor is warn or ok

### If You Break Something Critical

1. **Communicate immediately** (update handoff with BROKEN status)
2. Attempt to revert to working state
3. Document what broke and how
4. Ask for help if needed
5. Write incident report

---

## Open Questions Protocol

If you encounter something unclear:

1. **Check docs first** (docs/, AGENT_HANDOFF.md, AGENTS.md)
2. **Query RAGD** for historical context
3. **Read the code** to understand current behavior
4. **Mark as "Open Question" in your report**
5. **Ask the human** if critical

Do NOT:
- Guess and implement based on assumptions
- Make up behavior you haven't verified
- Claim something works without testing it

---

## Quality Bar

Your work must meet:

✓ All tests passing  
✓ Trading check passing  
✓ Platform doctor warn or better  
✓ Documentation updated  
✓ Report written  
✓ Commits clean and atomic  
✓ No security vulnerabilities  
✓ No broken links in vault  
✓ No secrets leaked

If you can't meet the quality bar, explain why in your report and mark work as PARTIAL.

---

## Anti-Patterns to Avoid

**Don't:**
- Make massive rewrites
- Introduce new frameworks/libraries without justification
- Create duplicate functionality
- Write code without tests
- Skip validation
- Assume things work without testing
- Hallucinate repo behavior
- Over-engineer simple tasks
- Add features not requested
- Break backward compatibility without migration plan

**Do:**
- Make small, incremental changes
- Use existing patterns
- Write tests first
- Validate thoroughly
- Read actual code
- Document decisions
- Ask when uncertain
- Keep it simple
- Focus on the task
- Preserve working systems

---

## Emergency Contacts

**Owner:** Martin (Matin)  
**Collaborator:** Dan  
**Platform:** WSL/Debian on Windows host  
**Repo:** `/home/Martin/Dominion`

If you break something critical:
1. Update AGENT_HANDOFF.md with BROKEN status
2. Document what broke
3. Attempt revert
4. Write incident report
5. Human will investigate

---

## Final Checklist

Before claiming task complete:

- [ ] Read AGENT_HANDOFF.md before starting
- [ ] Queried RAGD for context
- [ ] Made minimal diffs
- [ ] Added/updated tests
- [ ] Ran `python domdata/check_no_trading.py` → PASS
- [ ] Ran `python -m pytest -q` → PASS
- [ ] Ran C++ tests if relevant → PASS
- [ ] Updated relevant docs
- [ ] Updated AGENT_HANDOFF.md
- [ ] Wrote report in reports/
- [ ] Committed with proper message
- [ ] No secrets leaked
- [ ] No broken links
- [ ] Platform status still LIVE_GREEN or better

---

## Next Steps

1. Read [/AGENT_HANDOFF.md](/AGENT_HANDOFF.md) for current state
2. Read [03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md](03_AGENT_OPERATIONS/AGENT_OPERATING_SYSTEM.md) for detailed workflow
3. Read [09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md](09_RISK_AND_SECURITY/AGENT_SAFETY_RULES.md) for safety details
4. Query RAGD for task-specific context
5. Inspect relevant code
6. Make your plan
7. Execute carefully
8. Validate thoroughly
9. Document everything
10. Write handoff report

---

**Remember:** This is a living platform. Break nothing. Improve incrementally. Document everything.

Good luck.
