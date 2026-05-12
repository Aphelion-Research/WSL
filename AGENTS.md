# Dominion Agent Rules

Dominion is a shared WSL/Debian quant data workstation. Preserve the working MT5/Wine read-only data bridge, Tailscale/SSH collaboration, tmux sessions, and Codex workflow.

## Safety

- Data only. Never add live trading, buy, sell, close, modify, or pending-order execution.
- Do not call MetaTrader5 `order_send`.
- Do not call MetaTrader5 `order_check` except inside explicitly blocked safety tests or the forbidden-token scanner.
- Forbidden trading tokens outside allowlisted safety/test files: `order_send`, `order_check`, `TRADE_ACTION_DEAL`, `TRADE_ACTION_PENDING`, `POSITION_CLOSE`.
- Never print, copy, commit, log, document, or index secrets from `secrets/`.
- Do not read `secrets/mt5.env` contents. Existence and permissions checks are allowed.
- Always mask account/password data in diagnostics.

## Shell And Collaboration

- No auto-tmux from `.bashrc` or `.dominionrc`.
- No blocking startup commands.
- No SSH `RemoteCommand` for the `dominion` VS Code host.
- `openhere` must not launch Matin's Explorer for remote SSH users.
- Plain SSH users should use `tmux attach -t dan` or VS Code Remote SSH.

## Validation

Run before claiming success:

```bash
python ~/Dominion/domdata/check_no_trading.py
domdata notice
domdata order-send || true
domdata doctor
domdata xautick
domdata xaurates --count 5
domdata xauticks --start 2026-05-11T00:00:00Z --count 5
dominion-health
```

For RAGD changes:

```bash
cmake -S ~/Dominion/ragd -B ~/Dominion/ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ~/Dominion/ragd/build -j$(nproc)
cd ~/Dominion/ragd/build && ctest --output-on-failure
```

## Reporting

Update `PROGRESS.md`, `AGENT_HANDOFF.md`, and the current report in `reports/` after major phases. Be explicit about failures and deferred work.
