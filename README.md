# Dominion

Dominion V2 is a local-first, agent-native research and engineering workstation running on WSL/Debian.

Core layers:

- Codex for engineering work.
- RAGD for persistent project memory, retrieval, handoffs, TODOs, and MCP context.
- Research OS for approved-source evidence collection and RAGD research ingestion.
- RAGD embedding/HNSW/vault infrastructure for frontier-agent retrieval context.
- `domdata` for read-only MT5/XAUUSD data access.
- tmux, SSH, and Tailscale for Matin/Dan collaboration.

Daily commands:

```bash
dominion status
dominion doctor
dominion-ui --once
research status
dominion embed stats
dominion vault status
domdata notice
domdata xautick
```

Trading is intentionally blocked. Secrets live under `secrets/` and must never be printed, indexed, documented, or committed.
