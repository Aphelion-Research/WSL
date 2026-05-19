# Attack Surface Analysis

**Status:** LIVE_GREEN  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [THREAT_MODEL.md](THREAT_MODEL.md)

---

## Overview

Attack surface: entry points where adversary can interact with system.

**Scope:** Dominion (data pipeline, Agent OS, RAGD, trading systems)  
**Deployment:** Localhost-only (no internet-facing services)

---

## Entry Points

### E1: RAGD HTTP API (Port 7474)

**Binding:** `127.0.0.1:7474` (localhost-only)  
**Protocol:** HTTP (no TLS)  
**Authentication:** None  
**Endpoints:** `/health`, `/query`, `/index`, `/session/*`, `/memory/*`, `/todos/*`

**Attack Vectors:**
1. **Malicious query injection** — special chars in query string
2. **Path traversal** — `/index` accepts arbitrary file paths
3. **DoS** — flood with queries (no rate limiting)
4. **JSON injection** — malformed JSON crashes server

**Mitigations:**
- Localhost-only (not reachable from network)
- Exception handler catches crashes (returns 500)
- Input validation (JSON parsing validates structure)

**Residual Risks:**
- DoS (accepted, localhost-only)
- Path traversal (accepted, trusted local caller)

---

### E2: Filesystem

**Access:** Direct read/write via Python/C++ code

**Attack Vectors:**
1. **Secret file access** — read `secrets/mt5.env`
2. **Destructive commands** — `rm -rf data/`
3. **Symlink attacks** — create symlink to `/etc/passwd`, read via RAGD
4. **Race conditions** — TOCTOU (time-of-check-time-of-use)

**Mitigations:**
- Safety filters block secret paths (`is_secret_path()`)
- `--dangerous` flag required for destructive commands
- No symlink follow in RAGD (resolves absolute paths)
- WAL mode reduces TOCTOU window for SQLite

**Residual Risks:**
- Symlink attacks (accepted, trusted filesystem)
- Race conditions (low likelihood, SQLite WAL minimizes)

---

### E3: SQLite Databases

**Files:**
- `~/.dominion/agent_os.db` (Agent OS state)
- `~/.ragd/ragd.db` (RAGD index)
- `~/Dominion/data/dominion.duckdb` (market data)

**Attack Vectors:**
1. **SQL injection** — crafted input to SQL queries
2. **Database corruption** — write invalid data
3. **Lock denial** — hold lock indefinitely
4. **WAL checkpoint race** — concurrent write during checkpoint

**Mitigations:**
- Prepared statements (no string concatenation)
- Schema validation (foreign keys, NOT NULL constraints)
- WAL mode (concurrent reads, serialized writes)
- Timeout on lock acquisition (prevents indefinite holds)

**Residual Risks:**
- Database corruption (accepted, backups available)
- WAL checkpoint race (very low likelihood, WAL design minimizes)

---

### E4: Python Imports (Supply Chain)

**Attack Vectors:**
1. **Typosquatting** — install `panads` instead of `pandas`
2. **Compromised package** — legitimate package hijacked
3. **Dependency confusion** — private name clashes with malicious public
4. **Malicious import hook** — __import__ override steals credentials

**Mitigations:**
- Pin dependencies in `requirements.txt` (exact versions)
- Hash verification (`--hash=sha256:...`)
- Code review (manual inspection of new dependencies)
- Virtual environment (`.venv/`, isolated from system packages)

**Residual Risks:**
- Compromised package (low likelihood, monitor security advisories)
- Import hook (difficult to defend, accepted risk)

---

### E5: Git Repository

**Attack Vectors:**
1. **Commit secrets** — `git add secrets/`, push to public repo
2. **Rewrite history** — `git push --force` destroys commits
3. **Malicious hooks** — `.git/hooks/pre-commit` runs arbitrary code

**Mitigations:**
- `.gitignore` entry for `secrets/`
- Pre-commit hook scans for secrets
- Safety filters block secret paths in task scope
- Backups (weekly manual snapshots)

**Residual Risks:**
- Accidental force push (accepted, git reflog available)
- Malicious hooks (accepted, single-user repo)

---

### E6: Environment Variables

**Variables:**
- `DOMINION_ROOT` (repo root)
- `NOMIC_API_KEY` (embedding API key)
- `RAGD_URL` (RAGD endpoint)

**Attack Vectors:**
1. **Environment injection** — set `RAGD_URL=http://attacker.com:7474`
2. **Key leakage** — `echo $NOMIC_API_KEY` logged to shell history
3. **Command injection** — `DOMINION_ROOT="; rm -rf /"` passed to shell

**Mitigations:**
- No shell interpolation of env vars (Python `os.environ` direct access)
- API key not logged (safety filters redact API keys)
- Input validation (path sanitization)

**Residual Risks:**
- Key leakage to shell history (accepted, zsh history encrypted)
- Environment injection (accepted, single-user machine)

---

### E7: Network I/O (Outbound Only)

**Connections:**
- Nomic embedding API (HTTPS)
- Yahoo Finance API (HTTPS)
- FRED API (HTTPS)
- AlphaVantage API (HTTPS)

**Attack Vectors:**
1. **Man-in-the-middle** — HTTPS downgrade, capture API keys
2. **DNS poisoning** — redirect to malicious server
3. **API response injection** — malicious JSON crashes parser

**Mitigations:**
- TLS certificate validation (default Python `requests`)
- DNS over HTTPS (systemd-resolved, optional)
- JSON parsing with error handling (try/except)

**Residual Risks:**
- MITM (very low likelihood, TLS certificates validated)
- DNS poisoning (low likelihood, local DNS resolver)

---

## Attack Surface Reduction

### Reduction 1: Localhost-Only Binding

**Before:** RAGD binds to `0.0.0.0:7474` (all interfaces)  
**After:** RAGD binds to `127.0.0.1:7474` (localhost-only)

**Impact:** Eliminates network attacker threat (T3)

---

### Reduction 2: No Order Placement Functions

**Before:** MT5 order functions (`order_send`, `Position_Open`) in codebase  
**After:** No trading functions, safety filters block forbidden terms

**Impact:** Eliminates accidental/malicious order placement (T1.3)

---

### Reduction 3: Secret Path Blocking

**Before:** Agent OS allowed any file in task scope  
**After:** Safety filters block `secrets/`, `mt5.env`, `.env`, `.key`

**Impact:** Prevents accidental secret commit to git (T1.1)

---

### Reduction 4: Dependency Pinning

**Before:** `pip install pandas` (installs latest version)  
**After:** `pip install pandas==2.1.0 --hash=sha256:...`

**Impact:** Reduces supply chain risk (T2.1, T2.2)

---

## Entry Point Risk Assessment

| Entry Point | Exposure | Authentication | Encryption | Risk |
|-------------|----------|----------------|------------|------|
| RAGD HTTP API | Localhost | None | None | **Low** |
| Filesystem | Local process | OS permissions | None (disk encrypted) | **Medium** |
| SQLite databases | Local process | None | None (disk encrypted) | **Low** |
| Python imports | Local process | None | N/A | **Medium** |
| Git repository | Local + remote | SSH key | TLS (remote) | **Medium** |
| Environment vars | Local process | None | N/A | **Low** |
| Network I/O | Outbound | API keys | TLS | **Low** |

---

## Defense in Depth

### Layer 1: Network

- **Localhost-only binding** — RAGD, Research OS bind to `127.0.0.1`
- **No inbound connections** — firewall blocks external traffic

---

### Layer 2: Application

- **Safety filters** — block secrets, forbidden trading, dangerous commands
- **domdata scanner** — pre-commit hook scans for trading tokens
- **Input validation** — JSON parsing, path sanitization
- **Exception handling** — crashes return 500, don't expose stack traces

---

### Layer 3: Filesystem

- **Permissions** — `secrets/` = 700, `mt5.env` = 600
- **`.gitignore`** — excludes secrets from version control
- **Backups** — weekly snapshots to `backups/`

---

### Layer 4: Operating System

- **Disk encryption** — LUKS full-disk encryption
- **Screen lock** — 5-minute timeout
- **User isolation** — single user (no other accounts)

---

### Layer 5: Physical

- **Home office** — locked door, no unauthorized visitors
- **Dev machine** — laptop with TPM, secure boot

---

## Monitoring & Detection

### M1: RAGD Query Log

**Location:** `~/.ragd/ragd.log`  
**Rotation:** Daily (7-day retention)  
**Detection:** Unusual query patterns (e.g., 1000 queries/sec)

---

### M2: Agent OS Audit Log

**Location:** `~/.dominion/agent_os.db` (tables: `agent_file_touches`, `agent_sessions_v2`)  
**Retention:** Indefinite (append-only)  
**Detection:** Unauthorized file access, task creation by unknown agent

---

### M3: Git History

**Location:** `.git/` (commit history, reflog)  
**Retention:** Indefinite (unless history rewritten)  
**Detection:** Secrets in commit diff (`git log -p | grep -E "password|key"`)

---

## Incident Response

### I1: Secret Leaked to Git

**Detection:** Pre-commit hook blocks commit, or manual inspection

**Response:**
1. **Stop:** Do NOT push to remote
2. **Remove:** `git reset --hard HEAD~1` (if not pushed) or `git filter-repo --path secrets/ --invert-paths` (if pushed)
3. **Rotate:** Change MT5 password, Nomic API key
4. **Verify:** Scan commit history for other secrets

---

### I2: Unauthorized Trading

**Detection:** MT5 broker alert, unexpected order in account

**Response:**
1. **Stop:** Close all positions immediately (via MT5 terminal)
2. **Investigate:** Check `domdata/check_no_trading.py` scan results
3. **Remediate:** Remove trading code, rotate credentials
4. **Verify:** Re-run scanner, review git diff

---

### I3: Data Corruption

**Detection:** DuckDB integrity check fails, Agent OS queries return errors

**Response:**
1. **Stop:** Stop data pipeline, Agent OS operations
2. **Restore:** Copy from weekly backup
3. **Verify:** Re-run integrity checks
4. **Root cause:** Review logs, identify corruption source

---

## Related

- [THREAT_MODEL.md](THREAT_MODEL.md) — Threat actors, attack trees, risk matrix
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) — Security configuration checklist

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All entry points mapped + mitigations validated
