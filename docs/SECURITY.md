# Security

- `secrets/` is excluded from git and has mode `700`.
- `secrets/mt5.env` should have mode `600`.
- Do not print, copy, index, or document secret values.
- `domdata` is read-only and blocks trade-like commands.
- Run `python ~/Dominion/domdata/check_no_trading.py` before releases.

If a secret may have leaked, stop work, report the exact path/output channel, and rotate credentials outside this repo.
