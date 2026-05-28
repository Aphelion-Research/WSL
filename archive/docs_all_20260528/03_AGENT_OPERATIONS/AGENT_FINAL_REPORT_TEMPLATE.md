---
doc_type: workflow
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - agent
  - report
  - template
---

# Agent Final Report Template

**Purpose:** Standard format for agent handoff reports.

---

## File Naming

```
reports/<phase-name>-<YYYYMMDD-HHMMSS>.md
```

**Examples:**
- `reports/doc-expansion-20260519-173000.md`
- `reports/feature-kalman-fusion-20260515-120000.md`
- `reports/bugfix-brownian-bridge-20260516-093000.md`

---

## Report Structure

```markdown
# <Phase Name> — Agent Report

**Agent:** <Model Name>  
**Date:** YYYY-MM-DD  
**Status:** COMPLETE | PARTIAL | BROKEN  
**Quality Score:** X/100

---

## Executive Summary

<2-3 sentence summary of what was accomplished>

---

## Mission

<What was the agent asked to do?>

---

## What Changed

### Files Modified

- path/to/file1.py:123 — <what changed>
- path/to/file2.py:456 — <what changed>
- docs/new_doc.md — <created>

### Files Created

- path/to/new_file.py — <purpose>
- tests/test_new_feature.py — <test coverage>

### Files Deleted

- path/to/old_file.py — <why removed>

---

## Why

<Explain the problem that motivated this work>

<Include context: user request, bug report, architectural decision, etc.>

---

## How

<Explain the approach taken>

<Key algorithms, design decisions, tradeoffs>

---

## Validation Results

### Tests

\`\`\`bash
python -m pytest -q
# Output:
# 426 passed

python domdata/check_no_trading.py
# Output:
# PASS

ctest --test-dir ragd/build --output-on-failure
# Output:
# 24/24 passed
\`\`\`

### Platform Health

\`\`\`bash
python scripts/dominion_cli.py doctor --offline --json
# Output:
# {"overall": "warn", ...}
\`\`\`

### Manual Validation

<Any manual testing performed>

---

## Known Limitations

- Limitation 1: description, impact, workaround
- Limitation 2: description, impact, workaround

---

## Open Questions

- Question 1: context, why unresolved, who can answer
- Question 2: context, investigation needed

---

## Next Recommended Task

<Specific, actionable suggestion for next agent>

**Why this task:** <Explain priority/impact>

**Estimated effort:** <hours/days>

**Prerequisites:** <What must be done first>

---

## Quality Score (Out of 100)

| Category | Score | Notes |
|---|---:|---|
| **Correctness** | XX/25 | Tests pass, behavior correct |
| **Completeness** | XX/20 | Feature fully implemented |
| **Code Quality** | XX/15 | Readable, maintainable, tested |
| **Documentation** | XX/15 | Docs updated, clear explanations |
| **Safety** | XX/15 | No trading, no secrets, no vulnerabilities |
| **Performance** | XX/10 | No regressions, reasonable speed |
| **Total** | XX/100 | |

**Grade:** A (90+) | B (80-89) | C (70-79) | D (60-69) | F (<60)

---

## Lessons Learned

### What Worked

- Approach 1: why it was effective
- Approach 2: why it was effective

### What Could Improve

- Challenge 1: what went wrong, how to avoid
- Challenge 2: what went wrong, how to avoid

---

## Continuation Commands

\`\`\`bash
# View changes
git diff

# View this report
cat reports/<this-report>.md

# Run validation
python -m pytest -q
python domdata/check_no_trading.py

# Continue work
python scripts/dominion_cli.py agent next --json
\`\`\`

---

## Related Work

- Report: reports/prior-phase-20260510-120000.md
- ADR: docs/10_DECISION_LOGS/ADR_0042_decision.md
- Issue: #123
- PR: #456

---

## Agent Signature

**Agent:** <Model Name>  
**Mode:** <Normal | Caveman>  
**Date:** YYYY-MM-DD HH:MM:SS  
**Mission:** <Short mission description>  
**Status:** COMPLETE | PARTIAL | BROKEN

---

**Co-Authored-By:** Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Section Guidelines

### Executive Summary

- 2-3 sentences
- What was done
- What's the outcome
- High-level impact

**Example:**
> Implemented Kalman fusion for multi-source data pipeline. 6-filter bank
> with dynamic trust scoring now combines 5 sources (Yahoo, FRED, AV, COT,
> MT5) with Byzantine fault tolerance. 16/16 tests passing, data quality
> dramatically improved.

---

### Mission

- What was the agent asked to do?
- Original user request or task description
- Scope boundaries

---

### What Changed

**Files Modified:**
- Use format: `path/to/file.py:123 — brief description`
- Include line numbers for significant changes
- Group by subsystem if many files

**Files Created:**
- List all new files
- Explain purpose of each

**Files Deleted:**
- List removed files
- Explain why removed (not just "deleted")

---

### Why

- Problem statement
- Context (user request, bug report, architectural need)
- Why this solution (vs alternatives)

**Don't just say:**
> "User asked for feature X."

**Instead:**
> "User asked for multi-source data fusion because single-source data
> is unreliable (API failures, stale data, conflicting prices). Current
> pipeline uses only Yahoo Finance, which had 3 outages last month."

---

### How

- High-level approach
- Key algorithms or design patterns
- Important implementation details
- Tradeoffs considered

**Include:**
- Architecture decisions
- Data structures chosen
- Algorithms implemented
- Libraries used (if new)

---

### Validation Results

**Always include:**
- `python -m pytest -q` output
- `python domdata/check_no_trading.py` output
- C++ tests if relevant
- Platform health check

**Show actual output, not just "passed":**
```
python -m pytest -q
426 passed in 12.34s
```

Not:
```
Tests passed
```

---

### Known Limitations

**Be specific:**

✓ Good:
> **Limitation:** Kalman fusion only handles 5 sources. Adding 6th source
> requires refactoring filter bank architecture.  
> **Impact:** Can't easily add new data sources.  
> **Workaround:** Use one of existing 5 slots or refactor filter bank.

✗ Bad:
> Some limitations exist.

---

### Open Questions

**Format:**

```markdown
## Open Questions

### Question 1: Should we use multiprocessing for feature computation?

**Context:** Feature computation takes ~10 seconds (single-threaded).
Could parallelize by feature group.

**Tradeoffs:**
- Pro: Faster (estimate 3-5x speedup)
- Con: More complex, harder to debug
- Con: Needs shared memory for large arrays

**Who can answer:** Owner (Matin) — depends on latency requirements.

**Next steps:** Profile to confirm bottleneck, prototype multiprocessing,
measure speedup.
```

---

### Next Recommended Task

**Be specific:**

✓ Good:
> **Task:** Add automated scheduling for data pipeline.
>
> **Why:** Pipeline currently runs manually. Automated scheduling (cron or
> systemd timer) would ensure data stays fresh.
>
> **Approach:**
> 1. Create systemd timer unit
> 2. Add error notification (email or Slack)
> 3. Add job status dashboard
>
> **Estimated effort:** 2-3 hours
>
> **Prerequisites:** None

✗ Bad:
> Add more features.

---

### Quality Score

**Be honest:**
- Don't inflate scores
- Explain deductions
- Show path to 100

**Example:**

| Category | Score | Notes |
|---|---:|---|
| Correctness | 25/25 | All tests pass, behavior verified |
| Completeness | 18/20 | Feature works, but multiprocessing not added |
| Code Quality | 13/15 | Good structure, but some functions >100 lines |
| Documentation | 14/15 | Docs updated, could add more diagrams |
| Safety | 15/15 | Trading check pass, no vulnerabilities |
| Performance | 8/10 | Works, but feature computation slow |
| **Total** | **93/100** | Grade: A |

**Path to 100:**
- Add multiprocessing (+2)
- Split large functions (+2)
- Add Mermaid diagrams (+1)
- Profile and optimize features (+2)

---

### Lessons Learned

**What Worked:**
- TDD approach (write tests first) caught 3 bugs early
- RAGD query before coding prevented duplicate work
- Incremental commits (5 small commits) easier to review

**What Could Improve:**
- Spent 30 mins debugging type hint error (should have read docs first)
- Initial implementation was too complex (over-engineered)
- Didn't check performance until end (discovered slowness late)

---

## Anti-Patterns

**Don't write:**

✗ "Everything works great, no issues."  
✓ List specific achievements and known limitations.

✗ "Added some code and fixed stuff."  
✓ Explain what changed and why.

✗ "Tests probably pass."  
✓ Show actual test output.

✗ "Next agent should improve things."  
✓ Give specific, actionable next task.

---

## When to Write Report

**Timing:**
- After significant work (>1 hour)
- Before agent terminates
- After each phase completion
- When handing off to another agent
- When blocked on user decision

**Don't write report:**
- For tiny changes (<5 minutes, <10 lines)
- For mid-work snapshots (use git commits instead)

---

## Report Quality Checklist

- [ ] Executive summary is 2-3 sentences
- [ ] Mission clearly stated
- [ ] All changed files listed
- [ ] WHY explained (problem + context)
- [ ] HOW explained (approach + decisions)
- [ ] Validation commands shown with actual output
- [ ] Known limitations listed with impact
- [ ] Open questions explained with context
- [ ] Next task is specific and actionable
- [ ] Quality score is honest (not inflated)
- [ ] Lessons learned are concrete
- [ ] Continuation commands provided
- [ ] Agent signature present

---

## Related Docs

- [AGENT_OPERATING_SYSTEM.md](AGENT_OPERATING_SYSTEM.md)
- [AGENT_HANDOFF_PROTOCOL.md](AGENT_HANDOFF_PROTOCOL.md)
- [AGENT_README.md](../AGENT_README.md)

---

## Retrieval Hints

- "report template"
- "final report"
- "agent report format"
- "how to write report"
- "handoff report"
