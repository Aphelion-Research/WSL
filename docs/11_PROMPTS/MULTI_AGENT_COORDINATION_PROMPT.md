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
  - coordination
  - parallel
---

# Multi-Agent Coordination Prompt

**Use Case:** Coordinate multiple agents  
**Complexity:** High  
**Duration:** Variable

---

## Context

Multiple agents working in parallel on separate tasks.

**Agent 1:** [Task description]  
**Agent 2:** [Task description]

Repository: `/home/Martin/Dominion`

---

## Mission

Coordinate work to avoid conflicts and merge cleanly.

---

## Coordination Protocol

### Phase 1: Pre-Work (Before starting)

**Both agents:**

1. **Create branches**
```bash
# Agent 1
git checkout -b agent1-[task]

# Agent 2
git checkout -b agent2-[task]
```

2. **Define file ownership**

Document which agent owns which files:
```markdown
## File Ownership

### Agent 1 Territory
- docs/11_PROMPTS/
- docs/05_FEATURES/ (content only, no diagrams)
- docs/06_ROADMAP/
- docs/07_RESEARCH/
- docs/14_BACKLOG/
- docs/15_FUTURE_STATE/

### Agent 2 Territory
- docs/01_ARCHITECTURE/ (diagrams)
- vault/symbols/
- docs/09_RISK_AND_SECURITY/
- docs/08_TESTING_AND_QA/ (technical)

### Shared (Coordinate)
- docs/INDEX.md
- docs/MASTER_NAVIGATION.md
- docs/RAGD_INGESTION_MANIFEST.md
```

3. **Sync baseline**
```bash
# Both agents confirm same starting point
git log -1 --oneline
# Should show same commit
```

### Phase 2: Parallel Work

**Communication channels:**
- Shared doc: `AGENT_COORDINATION_STATUS.md`
- Format:
  ```markdown
  ## Agent 1 Status (Updated: 2026-05-19 15:30)
  - Task: Writing prompt library
  - Progress: 8/11 files complete
  - ETA: 30 minutes
  - Blockers: None
  
  ## Agent 2 Status (Updated: 2026-05-19 15:32)
  - Task: Creating architecture diagrams
  - Progress: 3/5 diagrams complete
  - ETA: 1 hour
  - Blockers: Waiting for Agent 1 to finish FEATURE_TEMPLATE.md
  ```

**Update frequency:**
- Every 30 minutes
- When completing major milestone
- When blocked
- When discovering conflict

### Phase 3: Pre-Merge Validation

**Each agent independently:**

```bash
# On own branch
python domdata/check_no_trading.py  # MUST PASS
python -m pytest -q                  # MUST PASS
python scripts/dominion_cli.py doctor --offline --json
```

**If validation fails:**
- Fix on own branch
- Re-validate
- Don't merge until passing

### Phase 4: Merge Strategy

**Option A: Sequential merge (Recommended)**

1. **Agent 2 merges first** (infrastructure changes)
```bash
# Agent 2
git checkout main
git pull
git merge agent2-[task]
git push
```

2. **Agent 1 rebases + merges** (content depends on infrastructure)
```bash
# Agent 1
git checkout agent1-[task]
git fetch origin
git rebase origin/main
# Resolve conflicts if any
python -m pytest -q  # Validate after rebase
git checkout main
git merge agent1-[task]
git push
```

**Option B: Parallel merge (If truly independent)**

1. Both merge to main simultaneously
2. Resolve conflicts in last merge
3. Validate merged state together

### Phase 5: Post-Merge Validation

**After all merges:**

```bash
# On main branch
python domdata/check_no_trading.py
python -m pytest -q
ctest --test-dir ragd/build --output-on-failure
python scripts/dominion_cli.py doctor --offline --json

# Rebuild RAGD index
python scripts/dominion_cli.py scan

# Sync to vault
python scripts/vault_sync.py
```

### Phase 6: Combined Report

**Create joint report:**

```markdown
---
mission: [Combined mission]
agents: Claude Sonnet 4.5 (Agent 1 + Agent 2)
date_completed: 2026-05-19
status: COMPLETE
validation: PASS
---

# Multi-Agent Mission Report

## Agent 1 Deliverables
[Agent 1's work summary]

## Agent 2 Deliverables
[Agent 2's work summary]

## Integration
[How work combined]

## Combined Validation
[Test results after merge]

## Quality Score
[If applicable]

## Next Steps
[Recommended follow-ups]
```

---

## Conflict Resolution

**If file conflicts:**

1. **Identify conflict area**
```bash
git status  # Shows conflicted files
```

2. **Understand both changes**
```bash
git diff --ours [file]    # Your version
git diff --theirs [file]  # Their version
```

3. **Resolve manually**
- Keep both if independent changes
- Merge if complementary
- Choose one if contradictory (discuss)

4. **Validate after resolution**
```bash
python -m pytest tests/[affected]/
```

**If logic conflicts (no git conflict but incompatible):**
- Agent call: Discuss approach
- Prioritize: Infrastructure before content
- Compromise: Find middle ground

---

## Common Patterns

### Pattern 1: Content + Infrastructure Split

**Agent 1:** Write specs, guides, docs (content)  
**Agent 2:** Diagrams, APIs, symbols (infrastructure)

**Merge order:** Agent 2 first (content depends on infrastructure)

### Pattern 2: Module Split

**Agent 1:** Module A  
**Agent 2:** Module B

**Merge order:** Alphabetical or either (independent)

### Pattern 3: Front-End + Back-End

**Agent 1:** CLI, user-facing (front-end)  
**Agent 2:** Core logic, APIs (back-end)

**Merge order:** Agent 2 first (front-end depends on back-end)

---

## Communication Template

```markdown
## [Agent Name] Update

**Time:** HH:MM
**Task:** [Current task]
**Status:** [On track | Ahead | Behind | Blocked]
**Progress:** [X/Y complete]
**ETA:** [Time remaining]
**Blockers:** [None | Description]
**Notes:** [Relevant info for other agent]
```

---

## Validation Checklist

Before declaring success:
- [ ] Both agents' branches merged
- [ ] All tests pass on main
- [ ] No merge conflicts remain
- [ ] Trading check passes
- [ ] Platform health OK
- [ ] RAGD index rebuilt
- [ ] Vault synced
- [ ] Combined report written

---

## Related Prompts

- [[CODEX_FINAL_REPORT_PROMPT]] — Individual reports
- Individual task prompts — Specific workflows

---

## Retrieval Hints

- "multi agent"
- "agent coordination"
- "parallel agents"
- "merge strategy"
