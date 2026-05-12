# Quickstart

Matin daily start:

```bash
cd ~/Dominion
dominion start
dominion status
warp matin
```

Dan daily start from Windows CMD:

```cmd
tailscale status
tailscale ping 100.95.35.80
ssh Martin@100.95.35.80
```

Then inside SSH:

```bash
warp dan
```

VS Code Remote SSH:

```cmd
code --remote ssh-remote+dominion /home/Martin/Dominion
```

Codex with RAGD:

```bash
codexstatus
codexprompt
codexrag "task-specific context"
warp codex
```

Research:

```bash
research init
research list-sources
research add-url https://docs.crawl4ai.com/ --source crawl4ai_docs
research run --limit 1
research ingest-ragd
```

Safety check:

```bash
domdata notice
domdata order-send || true
python ~/Dominion/domdata/check_no_trading.py
```
