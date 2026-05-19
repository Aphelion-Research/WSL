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
  - workflow
---

# Agent Workflow

See [AGENT_OPERATING_SYSTEM.md](AGENT_OPERATING_SYSTEM.md) for complete workflow.

This doc provides quick workflow summaries for common tasks.

## Workflow: Add Feature

1. Read handoff
2. Query RAGD: "implement <feature name> feature"
3. Write feature spec in `docs/05_FEATURES/`
4. Write tests first (TDD)
5. Implement feature
6. Run tests: `python -m pytest -q`
7. Run trading check: `python domdata/check_no_trading.py`
8. Update docs
9. Update handoff
10. Write report
11. Commit

## Workflow: Fix Bug

1. Read handoff
2. Query RAGD: "fix <bug description> bug"
3. Write failing test
4. Fix bug
5. Verify test passes
6. Run full test suite
7. Run trading check
8. Update docs if behavior changed
9. Update handoff
10. Write report
11. Commit

## Workflow: Refactor

1. Read handoff
2. Query RAGD: "refactor <component> code"
3. Write ADR explaining why
4. Ensure tests exist for current behavior
5. Refactor incrementally
6. Run tests after each step
7. Run trading check
8. Update docs
9. Update handoff
10. Write report
11. Commit

## Workflow: Add Documentation

1. Read handoff
2. Check existing docs to avoid duplication
3. Write doc with frontmatter metadata
4. Add to `docs/RAGD_INGESTION_MANIFEST.md`
5. Link from relevant index files
6. Run vault doctor: `python scripts/dominion_cli.py vault doctor --json`
7. Update handoff
8. Commit

## Workflow: Debug Issue

1. Read handoff
2. Query RAGD: "debug <issue> problem"
3. Reproduce issue
4. Read relevant code
5. Add debug logging
6. Isolate root cause
7. Write test that reproduces bug
8. Fix bug
9. Verify test passes
10. Remove debug logging
11. Run trading check
12. Update handoff
13. Write report
14. Commit

## Workflow: Review Code

1. Read handoff
2. Check recent commits: `git log --oneline -10`
3. Review diffs: `git show <commit>`
4. Check tests pass: `python -m pytest -q`
5. Check trading check: `python domdata/check_no_trading.py`
6. Check platform health: `python scripts/dominion_cli.py doctor --offline --json`
7. Verify docs updated
8. Verify handoff updated
9. Note any issues in handoff or backlog

## Retrieval Hints

- "agent workflow"
- "how to add feature"
- "how to fix bug"
- "workflow for X"
