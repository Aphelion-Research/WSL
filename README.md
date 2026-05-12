# Dominion

Dominion is a WSL/Debian workstation for read-only MT5 XAUUSD data engineering, local research, agent-assisted development, and shared Matin/Dan collaboration.

Core commands:

```bash
dominion-health
domdata notice
domdata xautick
domdata xaurates --count 20
domdata collect-status
connectinfo
```

Trading is intentionally blocked. Secrets live under `secrets/` and must never be printed or committed.
