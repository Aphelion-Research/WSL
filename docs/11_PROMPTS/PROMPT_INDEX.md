---
doc_type: index
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - prompts
  - agent
  - workflow
---

# Agent Prompt Library

**Purpose:** Reusable prompts for common agent workflows.

---

## Prompt Catalog

| Prompt | Use Case | Complexity | Duration |
|---|---|---|---|
| [[CODEX_REPO_AUDIT_PROMPT]] | Initial repository audit | High | 30-60 min |
| [[CODEX_FEATURE_IMPLEMENTATION_PROMPT]] | Implement new feature | High | 2-4 hours |
| [[CODEX_DOC_UPDATE_PROMPT]] | Update documentation | Medium | 30-60 min |
| [[CODEX_RAGD_UPDATE_PROMPT]] | Rebuild RAGD index | Low | 5-10 min |
| [[CODEX_TESTING_PROMPT]] | Add/fix tests | Medium | 1-2 hours |
| [[CODEX_REFACTOR_PROMPT]] | Refactor code | High | 2-4 hours |
| [[CODEX_BUGFIX_PROMPT]] | Debug + fix bug | Medium | 30-90 min |
| [[CODEX_FINAL_REPORT_PROMPT]] | Write final report | Low | 15-30 min |
| [[MULTI_AGENT_COORDINATION_PROMPT]] | Coordinate multiple agents | High | Variable |
| [[CODEX_OBSIDIAN_UPDATE_PROMPT]] | Sync vault + update notes | Low | 10-20 min |
| [[CODEX_HEALTH_CHECK_PROMPT]] | Platform health validation | Low | 5-10 min |

---

## Prompt Structure

All prompts follow standard structure:

```markdown
# [Prompt Name]

## Context
[What is the current state]

## Mission
[What needs to be accomplished]

## Constraints
[Safety rules, architectural boundaries, performance requirements]

## Workflow
[Step-by-step process]

## Validation
[Success criteria, tests to run]

## Output
[Expected deliverables]
```

---

## Usage

**Option 1: Copy-paste full prompt**
```bash
cat docs/11_PROMPTS/CODEX_FEATURE_IMPLEMENTATION_PROMPT.md
# Copy content, paste to agent
```

**Option 2: Reference in conversation**
```
"Follow CODEX_FEATURE_IMPLEMENTATION_PROMPT to add XYZ feature"
```

**Option 3: Chain prompts**
```
"Use CODEX_REPO_AUDIT_PROMPT first, then CODEX_FEATURE_IMPLEMENTATION_PROMPT"
```

---

## When to Use Each Prompt

### CODEX_REPO_AUDIT_PROMPT
**Trigger:** First time working in repo, or after long gap (>1 week)
**Purpose:** Build mental model of codebase
**Output:** Audit report with module map, dependencies, health assessment

### CODEX_FEATURE_IMPLEMENTATION_PROMPT
**Trigger:** User requests new feature
**Purpose:** Plan → implement → test → document → report
**Output:** Feature implementation + tests + docs + report

### CODEX_DOC_UPDATE_PROMPT
**Trigger:** Documentation stale or incomplete
**Purpose:** Update docs to match current code state
**Output:** Updated markdown files + vault sync

### CODEX_RAGD_UPDATE_PROMPT
**Trigger:** New docs added, or after major code changes
**Purpose:** Rebuild RAGD index for fresh retrieval
**Output:** Updated RAGD index + validation

### CODEX_TESTING_PROMPT
**Trigger:** Tests failing, or coverage gaps
**Purpose:** Write/fix tests for specific module
**Output:** Passing tests + coverage report

### CODEX_REFACTOR_PROMPT
**Trigger:** Code smells, technical debt, performance issues
**Purpose:** Refactor without changing behavior
**Output:** Cleaner code + passing tests + performance comparison

### CODEX_BUGFIX_PROMPT
**Trigger:** Bug reported (failing test, user report, health check)
**Purpose:** Debug → root cause → fix → validate
**Output:** Bug fix + regression test + report

### CODEX_FINAL_REPORT_PROMPT
**Trigger:** End of agent session
**Purpose:** Write comprehensive handoff report
**Output:** Final report following template

### MULTI_AGENT_COORDINATION_PROMPT
**Trigger:** Multiple agents working in parallel
**Purpose:** Coordinate work, avoid conflicts, merge results
**Output:** Coordination plan + merge strategy

### CODEX_OBSIDIAN_UPDATE_PROMPT
**Trigger:** After doc changes
**Purpose:** Sync docs to vault, update links, validate
**Output:** Synced vault + validation report

### CODEX_HEALTH_CHECK_PROMPT
**Trigger:** Before/after major changes
**Purpose:** Validate platform health
**Output:** Health report (tests, trading check, platform status)

---

## Prompt Chaining Patterns

### Pattern 1: New Feature (Full Cycle)
1. CODEX_REPO_AUDIT_PROMPT (if needed)
2. CODEX_FEATURE_IMPLEMENTATION_PROMPT
3. CODEX_TESTING_PROMPT (if coverage gaps)
4. CODEX_DOC_UPDATE_PROMPT
5. CODEX_RAGD_UPDATE_PROMPT
6. CODEX_FINAL_REPORT_PROMPT

### Pattern 2: Bug Fix (Quick)
1. CODEX_BUGFIX_PROMPT
2. CODEX_HEALTH_CHECK_PROMPT
3. CODEX_FINAL_REPORT_PROMPT

### Pattern 3: Documentation Sprint
1. CODEX_DOC_UPDATE_PROMPT (multiple docs)
2. CODEX_OBSIDIAN_UPDATE_PROMPT
3. CODEX_RAGD_UPDATE_PROMPT
4. CODEX_FINAL_REPORT_PROMPT

### Pattern 4: Parallel Agents
1. MULTI_AGENT_COORDINATION_PROMPT (both agents)
2. Agent 1: [Task-specific prompt]
3. Agent 2: [Task-specific prompt]
4. MULTI_AGENT_COORDINATION_PROMPT (merge)

---

## Customizing Prompts

All prompts are templates. Customize:

**Replace placeholders:**
- `[MODULE_NAME]` → actual module
- `[FEATURE_NAME]` → specific feature
- `[BUG_DESCRIPTION]` → bug details

**Adjust scope:**
- Remove steps if not needed
- Add domain-specific constraints
- Modify validation criteria

**Combine prompts:**
- Extract sections from multiple prompts
- Merge into custom workflow

---

## Prompt Maintenance

**Update prompts when:**
- Workflow changes (new validation gates)
- Tools change (new CLI commands)
- Best practices evolve
- Failure patterns emerge

**Review schedule:**
- Quarterly: Review all prompts for accuracy
- After incidents: Update prompts to prevent recurrence
- When onboarding: Test prompts with new agent

---

## Related Docs

- [[AGENT_README]] — Agent operating manual
- [[AGENT_OPERATING_SYSTEM]] — 13-step workflow
- [[AGENT_FINAL_REPORT_TEMPLATE]] — Report structure
- [[AGENT_SAFETY_RULES]] — Safety boundaries

---

## Retrieval Hints

- "agent prompts"
- "prompt library"
- "codex prompts"
- "workflow prompts"
- "how to prompt agent"
