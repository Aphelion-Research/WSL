---
synced: 2026-05-21 22:42
---
# RAGD And Codex Workflow

Every substantial Codex session should use RAGD before editing.

```text
ragd_handoff_read
ragd_query(task-specific context)
inspect files
edit
validate
ragd_remember(important decisions)
update PROGRESS.md, AGENT_HANDOFF.md, and reports/
```

Helper commands:

```bash
codexstatus
codexprompt
codexrag "domdata read only safety"
codexstart
```

`codexrag` prints a context preamble and top RAGD chunks for a task. It is useful before starting Codex or while preparing a prompt for another agent.
