---
doc_type: workflow
system: Dominion
ragd_priority: 9
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - agent
  - handoff
  - protocol
---

# Agent Handoff Protocol

## Purpose

This protocol defines how agents hand off work to future agents.

## Handoff File

Primary handoff: `/AGENT_HANDOFF.md`

This file MUST be kept current.

## Handoff Format

```markdown
# Dominion Agent Handoff

## Current State — YYYY-MM-DD

Status: **LIVE_GREEN** | **BROKEN** | **PARTIAL** | **TESTING**

### Recent Changes (This Session)

[What changed in this agent run]

### What Works

- Feature X: operational, tests passing
- Feature Y: operational, validated
- Feature Z: operational, documented

### Known Issues

- Issue A: description, workaround, priority
- Issue B: description, impact, mitigation

### Validation Baseline

\`\`\`bash
python -m pytest -q                                    # X passed
python domdata/check_no_trading.py                     # PASS
ctest --test-dir ragd/build --output-on-failure        # Y/Y passed
bash scripts/verify_live.sh                            # Z/Z checks
\`\`\`

### Next Recommended Task

[Specific, actionable suggestion for next agent]

### Open Questions

- Question 1: context, why important, who can answer
- Question 2: context, investigation needed

---

## Historical Context

[Prior significant changes, organized by phase/date]
```

## Required Sections

Every handoff MUST include:

1. **Current State date** — Today's date
2. **Status** — LIVE_GREEN | BROKEN | PARTIAL | TESTING
3. **Recent Changes** — What this agent did
4. **What Works** — Operational features with evidence
5. **Known Issues** — Problems with workarounds
6. **Validation Baseline** — Exact commands + expected output
7. **Next Recommended Task** — Specific suggestion
8. **Open Questions** — Unresolved issues

## Status Levels

| Status | Meaning | Action |
|---|---|---|
| **LIVE_GREEN** | All systems operational, tests passing | Normal development |
| **PARTIAL** | Some features incomplete, tests pass | Continue work |
| **TESTING** | New code added, validation in progress | Complete validation |
| **BROKEN** | Critical systems failing, tests fail | Fix immediately |

## Handoff Quality Bar

Good handoff:
- ✓ Specific validation commands
- ✓ Exact test counts (426/426 not "all passing")
- ✓ Concrete next task ("add feature X" not "improve system")
- ✓ Evidence-backed claims (test output, health checks)
- ✓ Open questions clearly stated

Bad handoff:
- ✗ Vague status ("mostly working")
- ✗ No validation commands
- ✗ Generic next task ("continue development")
- ✗ No evidence
- ✗ Undocumented assumptions

## Update Frequency

Update handoff:
- **After every significant change** (feature add, bug fix, refactor)
- **Before agent terminates** (end of session)
- **When status changes** (LIVE_GREEN → BROKEN)
- **When validation baseline changes** (test count update)

## Handoff Validation

Before claiming handoff complete:

- [ ] Date is today
- [ ] Status is accurate
- [ ] Recent changes documented
- [ ] Validation commands work
- [ ] Next task is specific
- [ ] Open questions listed
- [ ] No false claims

## Example Handoff

See `/AGENT_HANDOFF.md` for current live example.

## Related Docs

- [AGENT_OPERATING_SYSTEM.md](AGENT_OPERATING_SYSTEM.md) — Full workflow
- [AGENT_README.md](../AGENT_README.md) — Agent manual

## Retrieval Hints

- "handoff protocol"
- "how to write handoff"
- "agent handoff format"
- "what to include in handoff"
