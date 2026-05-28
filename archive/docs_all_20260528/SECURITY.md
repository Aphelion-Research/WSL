# Security

- `secrets/` is excluded from git and has mode `700`.
- `secrets/mt5.env` should have mode `600`.
- Do not print, copy, index, or document secret values.
- `domdata` is read-only and blocks trade-like commands.
- Run `python ~/Dominion/domdata/check_no_trading.py` before releases.
- Research OS may only fetch approved sources from `research/sources.yaml`.
- Do not index `secrets/`, raw data, Wine folders, backups, model files, or logs with sensitive content.
- Mask account, password, token, cookie, and API key values in diagnostics.
- Do not add MetaTrader5 `order_send` or live trading behavior.

If a secret may have leaked, stop work, report the exact path/output channel, and rotate credentials outside this repo.
