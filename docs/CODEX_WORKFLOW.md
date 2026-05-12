# Codex Workflow

Helpers:

```bash
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
