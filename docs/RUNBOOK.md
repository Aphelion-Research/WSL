# Runbook

MT5:

```bash
mt5start
mt5kill
mt5start
```

Health:

```bash
dominion-health
dominion-health --json
domshare status
```

Common fixes:

- If MT5 data commands fail, run `mt5start`, wait five seconds, and retry once.
- If shell startup is broken, restore `.bashrc` and `.dominionrc` from the latest `backups/<RUN_ID>/`.
- If Dan cannot connect, check `tailscale status`, `service ssh status`, and `connectinfo`.
