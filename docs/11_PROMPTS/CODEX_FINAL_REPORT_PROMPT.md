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
  - report
  - handoff
---

# CODEX Final Report Prompt

**Use Case:** Write final handoff report  
**Complexity:** Low  
**Duration:** 15-30 minutes

---

## Context

Agent session ending. Write comprehensive handoff report.

Repository: `/home/Martin/Dominion`

---

## Mission

Document session for future agents/humans:
- What changed
- Why
- How
- Validation results
- Known issues
- Next steps

---

## Template

Use [[AGENT_FINAL_REPORT_TEMPLATE]] or inline:

```markdown
---
mission: [Brief mission statement]
agent: Claude Sonnet 4.5
date_started: 2026-05-19
date_completed: 2026-05-19
duration_hours: [X.X]
status: [COMPLETE | PARTIAL | BLOCKED]
validation: [PASS | FAIL | WARN]
---

# Agent Mission Report: [Title]

**Mission:** [1-2 sentence description]

**Status:** [COMPLETE | PARTIAL | BLOCKED]

**Quality Score:** [Optional: X/100]

---

## Executive Summary

[3-5 bullet points summarizing key deliverables]

---

## What Changed

### Files Created ([N] files)

1. **path/to/file.py** ([N] lines)
   - Purpose: [brief]
   - Key features: [list]

### Files Modified ([N] files)

1. **path/to/file.py** (lines [X]-[Y])
   - Change: [what changed]
   - Reason: [why]

### Files Deleted ([N] files)

[If any]

---

## Why

[Explain motivation and context]

**Problem:**
[What problem being solved]

**Approach:**
[Why this approach chosen]

**Alternatives:**
[What alternatives considered, why rejected]

---

## How

[Detailed implementation description]

**Key decisions:**
1. Decision A → Rationale
2. Decision B → Rationale

**Algorithms:**
[If complex algorithms, explain]

**Integration:**
[How changes integrate with existing code]

---

## Validation Results

### Core Validation ✓ | ✗

```bash
python domdata/check_no_trading.py
# Output: [PASS | FAIL]
```

### Tests ✓ | ✗

```bash
python -m pytest -q
# Output: [XXX/XXX passing]

ctest --test-dir ragd/build --output-on-failure
# Output: [XX/XX passing]
```

### Platform Health ✓ | ✗

```bash
python scripts/dominion_cli.py doctor --offline --json
# Output: overall: [ok | warn | error]
```

### Manual Testing ✓ | ✗

[Describe manual testing performed]

---

## Known Limitations

1. [Limitation 1]
2. [Limitation 2]

---

## Open Questions

1. [Question 1]
2. [Question 2]

---

## Next Recommended Task

**Option 1: [Task A]**
- Duration: [X hours]
- Value: [High | Medium | Low]
- Why: [rationale]

**Option 2: [Task B]**
- Duration: [X hours]
- Value: [High | Medium | Low]
- Why: [rationale]

**Recommendation:** [Which option and why]

---

## Quality Score: [Optional]

[If documenting quality improvements]

### [Category]: [XX]/100

**Improvements:**
- [What improved]

**Gaps:**
- [What remains]

---

## Lessons Learned

### What Worked Well

1. [Success 1]
2. [Success 2]

### What Could Improve

1. [Improvement 1]
2. [Improvement 2]

---

## Continuation Commands

```bash
# Validate
python domdata/check_no_trading.py
python scripts/dominion_cli.py doctor --offline --json

# Continue work
[Relevant commands for next agent]
```

---

## Related Work

[Link to related reports, features, issues]

---

## Agent Signature

**Agent:** Claude Sonnet 4.5  
**Session:** 2026-05-19  
**Token Budget Used:** ~XXK / 200K ([XX]%)  
**Validation:** [PASS | FAIL]  
**Handoff Status:** [Clean | Issues present]  
**Confidence:** [High | Medium | Low]

---

**Remember:** [Relevant closing note]
```

---

## Report Checklist

Before submitting report:
- [ ] Executive summary clear
- [ ] All changed files listed
- [ ] Validation results included
- [ ] Known limitations noted
- [ ] Next steps recommended
- [ ] Commands for continuation provided
- [ ] Lessons learned captured

---

## Report Quality

**Good report:**
- Scannable (headers, bullets)
- Concrete (specific files, line numbers)
- Validated (test results included)
- Honest (known issues disclosed)
- Actionable (next steps clear)

**Bad report:**
- Vague ("improved code quality")
- Incomplete (missing validation)
- Optimistic (hides issues)
- Dead-end (no next steps)

---

## Related Templates

- [[AGENT_FINAL_REPORT_TEMPLATE]] — Full template with guidelines
- [[AGENT_HANDOFF_PROTOCOL]] — Handoff requirements

---

## Retrieval Hints

- "final report"
- "handoff report"
- "session report"
- "agent report"
