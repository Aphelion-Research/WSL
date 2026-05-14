# Dominion Platform Contract

Dominion is a shared WSL/Debian local-first research and engineering workstation. Preserve the working MT5/Wine read-only data bridge, RAGD memory spine, Codex workflow, Tailscale/SSH collaboration, and tmux sessions while improving the platform.

## RAGD-first workflow

Every future Codex run should:

- Call `ragd_handoff_read` before work.
- Call `ragd_query` with task-specific context before editing.
- Inspect the relevant files after RAGD context.
- Edit only after understanding the local contracts and current state.
- Validate the changed surface with focused tests or commands.
- Call `ragd_remember` for important decisions, architecture changes, and safety-relevant findings.
- Update `PROGRESS.md` and `AGENT_HANDOFF.md` for major tasks.
- Update the current report under `reports/` when a phase completes or fails.

## Safety boundaries

- Data only. Never add live trading, buy, sell, close, modify, or pending-order execution.
- Do not call MetaTrader5 `order_send`.
- Do not call MetaTrader5 `order_check` except inside explicitly blocked safety tests or the forbidden-token scanner.
- Forbidden trading tokens outside allowlisted safety/test files: `order_send`, `order_check`, `TRADE_ACTION_DEAL`, `TRADE_ACTION_PENDING`, `POSITION_CLOSE`.
- Never print, copy, commit, log, document, or index secrets from `secrets/`.
- Do not read `secrets/mt5.env` contents. Existence and permissions checks are allowed.
- Always mask account/password data in diagnostics.
- Do not delete data, backups, secrets, history, or user work unless explicitly requested.

## Validation policy

Run before claiming full platform success:

```bash
python ~/Dominion/domdata/check_no_trading.py
domdata notice
domdata order-send || true
domdata doctor
domdata xautick
domdata xaurates --count 5
domdata xauticks --start 2026-05-11T00:00:00Z --count 5
[ -z "$CODEX_SANDBOX" ] && dominion-health || echo "SKIP: health checks not available in sandbox"
```

For RAGD changes:

```bash
cmake -S ~/Dominion/ragd -B ~/Dominion/ragd/build -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build ~/Dominion/ragd/build -j$(nproc)
cd ~/Dominion/ragd/build && ctest --output-on-failure
```

For Research OS or local LLM changes, run the focused pytest suite under the changed package when available.

## Reporting policy

- Update `PROGRESS.md`, `AGENT_HANDOFF.md`, and the current report in `reports/` after major phases.
- Be explicit about failures, partial implementations, skipped validation, and deferred work.
- Keep reports useful for the next human or agent: include exact commands, status, and next best task.

## Research/crawler policy

- No uncontrolled internet crawling.
- Only crawl sources listed in `research/sources.yaml` or explicitly approved by command input.
- Respect per-source rate limits and bounded `--limit` execution.
- Store provenance for fetched documents: URL, source, fetch time, hash, status, and trust.
- Never crawl or ingest `secrets/`, private data dumps, raw MT5 data, Wine folders, backups, or model files.
- Fail closed with recorded errors instead of retrying forever.

## Data/domdata policy

- `domdata` remains read-only.
- Preserve investor/read-only MT5 behavior and blocked trading commands.
- Prefer normalized Parquet/DuckDB outputs under `data/normalized/`.
- Do not commit raw market data, DuckDB files, secrets, Wine prefixes, model files, logs, or backups.
- Run the forbidden-token scanner after changes near `domdata` or MT5 integration.

## Collaboration policy

- No auto-tmux from `.bashrc` or `.dominionrc`.
- No blocking startup commands.
- No SSH `RemoteCommand` for the `dominion` VS Code host.
- `openhere` must not launch Matin's Explorer for remote SSH users.
- Plain SSH users should use `tmux attach -t dan` or VS Code Remote SSH.
- Preserve stable tmux identities: `matin`, `dan`, `dominion`, `ragd`, and Codex sessions.
