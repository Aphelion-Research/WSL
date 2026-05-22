---
synced: 2026-05-21 22:42
---
# Dan Setup From Windows CMD

1. Install Tailscale if needed.
2. Accept Matin's Tailnet invite.
3. In CMD:

```cmd
tailscale status
tailscale ip -4
tailscale ping <tailscale-ip>
ssh Martin@<tailscale-ip>
```

Note: `connectinfo` is run by Matin inside WSL/Dominion (Linux shell), not by Dan in Windows CMD.

4. After SSH:

```bash
tmux attach -t dan
```

5. VS Code Remote SSH config at `%USERPROFILE%\.ssh\config`:

```text
Host dominion
  HostName <tailscale-ip>
  User Martin
  ServerAliveInterval 30
  ServerAliveCountMax 3
```

Open:

```cmd
code --remote ssh-remote+dominion /home/Martin/Dominion
```

Fallback:

```cmd
"%LocalAppData%\Programs\Microsoft VS Code\bin\code.cmd" --remote ssh-remote+dominion /home/Martin/Dominion
```
