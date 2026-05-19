---
synced: 2026-05-19 18:24
---
# Runbook

## Daily Start

```bash
cd ~/Dominion
dominion start
dominion status
dominion-ui --once
```

## MT5 And domdata

```bash
mt5start
domdata notice
domdata collect-status
domdata xautick
```

Trading commands are intentionally blocked:

```bash
domdata order-send || true
python ~/Dominion/domdata/check_no_trading.py
```

## RAGD

```bash
dominion ragd
curl -sf http://127.0.0.1:7474/health
codexrag "current task"
```

If RAGD is down, run `dominion start` and then check the `ragd` tmux session.

## Research OS

```bash
research status
research doctor
research list-sources
research add-url URL --source SOURCE_NAME
research run --limit 1
research ingest-ragd
```

Fetch only approved sources. Do not run unbounded crawlers.

## Retrieval Context

```bash
dominion embed stats
dominion vault status
dominion search "query"
```

External embedding runs require explicit `RAGD_EMBED_API_KEY`. Without it, `dominion embed run` fails closed and does not send code externally.

## Collaboration

```bash
warp list
warp matin
warp dan
warp dominion
```

Remote file editing should use VS Code Remote SSH.

## Common Fixes

- If MT5 data commands fail, run `mt5start`, wait five seconds, and retry once.
- If shell startup is broken, restore `.bashrc` and `.dominionrc` from the latest `backups/<RUN_ID>/`.
- If Dan cannot connect, Matin should check `tailscale status`, `service ssh status`, and `connectinfo` inside WSL/Dominion.
- If Research OS fetch fails, inspect `research status`, `research list-sources`, and the crawl job error.
- If Codex lacks RAGD tools, run `codexstatus` and then `/mcp` inside Codex.
