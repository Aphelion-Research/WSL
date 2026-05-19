---
synced: 2026-05-19 18:24
---
# Matin Setup

```bash
domshare start
domshare status
matin
shared
tailscale status
service ssh status
```

Reset tmux sessions only when no one is using them:

```bash
tmux kill-session -t dominion
tmux new -d -s dominion
```

`codehere` opens local VS Code on Matin's local WSL. From plain SSH it prints the Dan-side Remote SSH command. `openhere` never opens Matin's Explorer for remote SSH users.
