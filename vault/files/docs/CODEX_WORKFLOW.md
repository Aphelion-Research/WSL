---
synced: 2026-05-21 22:42
---
# Codex Workflow

Start substantial work with RAGD:

```text
ragd_handoff_read
ragd_query(task-specific context)
inspect files
edit
validate
ragd_remember(important decisions)
update PROGRESS.md, AGENT_HANDOFF.md, and reports/
```

Helpers:

```bash
codexstatus
codexprompt
codexrag "task-specific context"
codexstart
codexmatin
codexdan
codexls
codexsend SESSION MESSAGE...
codexkill SESSION
codexnew SESSION PATH
```

Review before handoff:

```bash
git status --short
git diff --stat
python ~/Dominion/domdata/check_no_trading.py
```

Stop a bad Codex session:

```bash
codexls
codexkill codex-matin
```
