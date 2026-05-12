# Dominion Overnight Superbuild Report

RUN_ID: `20260511-221153`

Started: `2026-05-11T22:11:53-04:00`

## Phase 0: Baseline Audit

Start: `2026-05-11T22:11:53-04:00`


### Audit Summary

- Workspace: `/home/Martin/Dominion`
- OS: Debian 13 on WSL2 kernel 6.6.87.2
- CPU/RAM: 20 threads, 29GiB RAM, 16GiB swap
- Disk: /dev/sdd about 936G free
- GPU: NVIDIA GeForce RTX 3050 Laptop GPU detected
- Python: `.venv` Python 3.13.5 active on current PATH
- Node/npm/Codex: node v20.19.2, npm 9.2.0, codex-cli 0.130.0
- tmux: 3.5a; sessions `matin`, `dan`, `dominion` present
- SSH: active on port 22; Tailscale IP `100.95.35.80`
- Wine/MT5: Wine 11.8, `/home/Martin/.mt5`, terminal64.exe and Wine Python present; MT5 process running
- domdata: command exists and doctor imports MetaTrader5 with masked password status
- Secrets: `secrets/` mode 700, `secrets/mt5.env` mode 600; contents not read
- Git: `.git` directory exists but is not initialized; writable after interrupted prior init

Commands run: baseline audit commands for system, toolchain, SSH/Tailscale, Wine/MT5, domdata doctor, directory sizes, git state.

Validation results: Phase 0 PASS. No secrets printed.

Failures: none blocking. Git needs initialization in Phase 1.

Next actions: initialize git safely, update `.gitignore`, create baseline checkpoint if safe.

End: `2026-05-11T22:12:44-04:00`
