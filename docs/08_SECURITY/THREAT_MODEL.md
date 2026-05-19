# Threat Model

**Status:** LIVE_GREEN (Security analysis for local-first system)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Scope:** Dominion (data pipeline, Agent OS, RAGD, trading systems)

---

## System Profile

**Deployment:** Local workstation (Ubuntu 22.04 WSL2)  
**Network Exposure:** Localhost only (`127.0.0.1`)  
**Users:** Single developer (MatinDeevv)  
**Threat Actor:** Insider threat (accidental), supply chain (dependencies)  
**CIA Priority:** Confidentiality > Integrity > Availability

---

## Assets

### High-Value Assets

**1. Trading Credentials (`secrets/mt5.env`)**
- MT5 account ID, password, server
- **Impact if compromised:** Unauthorized trading, account drain
- **Protection:** Git-ignored, filesystem permissions (`600`), blocked by safety filters

**2. Embedding API Keys (`NOMIC_API_KEY`)**
- Nomic embedding API key
- **Impact if compromised:** API quota theft, $100-500/month loss
- **Protection:** Environment variable (not persisted), no logging

**3. Market Data (DuckDB `dominion.duckdb`)**
- 1256 days of OHLCV data, 400 features
- **Impact if compromised:** Data theft (low commercial value, public data)
- **Protection:** Filesystem permissions (`644`), no encryption

**4. Agent OS State (SQLite `agent_os.db`)**
- Session history, task details, file touches
- **Impact if compromised:** Reverse-engineer development process, leak IP
- **Protection:** Filesystem permissions (`644`), no encryption

**5. RAGD Index (`ragd.db`, `ragd.hnsw`)**
- Indexed codebase (10k chunks, source code)
- **Impact if compromised:** Source code leak
- **Protection:** Filesystem permissions (`644`), localhost-only API

---

## Threat Actors

### T1: Accidental Insider (High Likelihood, Moderate Impact)

**Profile:** Developer (self) accidentally exposes secrets or destroys data

**Motivations:**
- Convenience (commit secrets to git for backup)
- Ignorance (don't know file contains secret)
- Fatigue (run destructive command without thinking)

**Capabilities:**
- Full filesystem access
- Git push access
- Root privileges (sudo)

**Attack Scenarios:**
1. **Accidental git commit of secrets** (`git add secrets/`, push to public repo)
2. **Copy-paste credentials into code** (API key in source file)
3. **Destructive command** (`rm -rf data/`, `git reset --hard` without backup)
4. **Order placement** (accidentally call `order_send` in test code)

---

### T2: Supply Chain Attack (Low Likelihood, High Impact)

**Profile:** Compromised Python package in dependencies

**Motivations:**
- Credential theft (steal API keys, MT5 passwords)
- Backdoor (persistent access to dev machine)
- Ransomware (encrypt data, demand payment)

**Capabilities:**
- Code execution (Python import hook)
- Filesystem access (read secrets)
- Network access (exfiltrate data)

**Attack Scenarios:**
1. **Typosquatting** (install `panads` instead of `pandas`)
2. **Compromised maintainer** (legitimate package hijacked)
3. **Dependency confusion** (private package name clashes with malicious public package)

---

### T3: Network Attacker (Very Low Likelihood, Low Impact)

**Profile:** Attacker on local network (LAN)

**Motivations:**
- Reconnaissance (scan for open ports)
- Data theft (capture RAGD queries)
- Denial of service (flood RAGD port)

**Capabilities:**
- Network access (same LAN)
- Port scanning (nmap)
- Packet sniffing (Wireshark)

**Attack Scenarios:**
1. **Port scan** (discover RAGD on `7474`)
2. **Man-in-the-middle** (ARP spoofing, capture traffic)
3. **Denial of service** (flood RAGD with queries)

**Mitigation:** All services bind to `127.0.0.1` (not `0.0.0.0`) → **network attacker cannot reach services**

---

### T4: Physical Attacker (Very Low Likelihood, High Impact)

**Profile:** Physical access to dev machine

**Motivations:**
- Data theft (copy secrets, source code)
- Sabotage (delete data, install malware)

**Capabilities:**
- Full disk access (boot from USB)
- Memory dump (cold boot attack)
- Keylogging (hardware keylogger)

**Attack Scenarios:**
1. **Unattended machine** (screen unlocked, attacker copies secrets)
2. **Boot from USB** (bypass OS, mount disk, copy files)
3. **Evil maid** (install keylogger, return later for credentials)

**Mitigation:** Disk encryption (LUKS), screen lock timeout, physical security

---

## Attack Trees

### AT1: Exfiltrate MT5 Credentials

```
                [Steal MT5 credentials]
                        |
        +---------------+---------------+
        |                               |
   [Read secrets/mt5.env]        [Keylog password]
        |                               |
   +----+----+                     [Physical access]
   |         |                          |
[Git leak][Supply chain]         [Hardware keylogger]
```

**Mitigations:**
- Git leak: `.gitignore` entry, pre-commit hook, safety filters
- Supply chain: Pin dependencies (`requirements.txt` with hashes)
- Keylog: Disk encryption, screen lock

---

### AT2: Unauthorized Trading

```
                [Place unauthorized order]
                        |
        +---------------+---------------+
        |                               |
   [Call order_send()]            [Compromise MT5 server]
        |                               |
   +----+----+                     [Network attack]
   |         |                          |
[Accidental][Malicious code]      [Not in scope]
```

**Mitigations:**
- Accidental: `domdata/check_no_trading.py` scanner, safety filters, no order functions in repo
- Malicious code: Code review, no trading commands in codebase

---

### AT3: Data Exfiltration (Source Code)

```
                [Steal source code]
                        |
        +---------------+---------------+
        |                               |
   [Query RAGD]                  [Copy filesystem]
        |                               |
   +----+----+                     [Physical access]
   |         |                          |
[LAN attacker][Supply chain]      [Boot from USB]
```

**Mitigations:**
- LAN attacker: RAGD binds to `127.0.0.1` (not reachable from LAN)
- Supply chain: Pin dependencies, code review
- Physical: Disk encryption (LUKS)

---

## Risk Matrix

| Threat | Likelihood | Impact | Risk | Mitigations |
|--------|------------|--------|------|-------------|
| **T1.1: Git leak secrets** | High | High | **CRITICAL** | `.gitignore`, pre-commit hook, safety filters |
| **T1.2: Destructive command** | Medium | High | **HIGH** | Backups, `--dangerous` flag, confirmation prompts |
| **T1.3: Accidental order placement** | Low | Critical | **HIGH** | `check_no_trading.py`, safety filters, no order functions |
| **T2.1: Supply chain (typosquatting)** | Low | High | **MEDIUM** | Pin dependencies, code review |
| **T2.2: Supply chain (compromised pkg)** | Very Low | High | **LOW** | Pin dependencies with hashes |
| **T3.1: Network attacker (LAN)** | Very Low | Low | **NEGLIGIBLE** | Bind to `127.0.0.1` |
| **T4.1: Physical attacker (evil maid)** | Very Low | High | **LOW** | Disk encryption, screen lock |

---

## Security Controls

### Preventive Controls

**C1: Git Ignore Secrets (T1.1)**
```gitignore
secrets/
*.env
*.key
*.pem
```

**C2: Safety Filters (T1.1, T1.3)**  
`dominion_agent/safety.py`:
- `is_secret_path()` — block `secrets/`, `mt5.env`, `.env`, `.key`
- `is_forbidden_trading_task()` — block `order_send`, `Position_Open`, `enable live trading`
- `validate_task_payload()` — run on task creation, block unsafe tasks

**C3: domdata Scanner (T1.3)**  
`domdata/check_no_trading.py`:
- Scans codebase for forbidden trading tokens
- Blocks: `order_send`, `Order_Send`, `Position_Open`, `execute_trade`
- Runs in CI (pre-commit hook)

**C4: Localhost-Only Binding (T3.1)**  
RAGD, Research OS bind to `127.0.0.1` (not `0.0.0.0`) → no network exposure

**C5: Dependency Pinning (T2.1, T2.2)**  
`requirements.txt` with exact versions + hashes:
```
pandas==2.1.0 --hash=sha256:abc123...
numpy==1.25.2 --hash=sha256:def456...
```

**C6: Filesystem Permissions (T1.1, T4.1)**
```bash
chmod 700 secrets/
chmod 600 secrets/mt5.env
```

---

### Detective Controls

**D1: Git History Scan (T1.1)**  
Pre-commit hook scans staged files for secrets:
```bash
git diff --cached --name-only | grep -E "secrets/|\.env$" && exit 1
```

**D2: RAGD Query Logging (T3.1)**  
RAGD logs all queries to `~/.ragd/ragd.log` (rotate daily)

**D3: Agent OS Audit Log (T1.2)**  
Agent OS records all file touches, tasks, sessions in SQLite (immutable append-only log)

---

### Corrective Controls

**R1: Backups (T1.2)**  
Weekly manual backups:
```bash
cp data/dominion.duckdb backups/dominion_$(date +%Y%m%d).duckdb
cp ~/.dominion/agent_os.db backups/agent_os_$(date +%Y%m%d).db
```

**R2: Git Revert (T1.1)**  
If secrets leaked to git:
```bash
git reset --hard HEAD~1  # before push
git push --force  # after push (if not public repo)
# If public: rotate credentials immediately
```

**R3: Incident Response Plan**  
See [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) → "Incident Response" section

---

## Residual Risks

### R1: Supply Chain Attack (Accepted)

**Risk:** Compromised Python package steals credentials

**Justification:**
- Low likelihood (rare for established packages)
- Detection difficult (code obfuscation)
- Mitigation cost high (sandbox all imports, high overhead)

**Acceptance:** Monitor security advisories, pin dependencies, code review

---

### R2: Physical Attack (Accepted)

**Risk:** Physical access to dev machine

**Justification:**
- Very low likelihood (single-user dev machine at home)
- Detection impossible (attacker has full access)
- Mitigation cost moderate (disk encryption enabled)

**Acceptance:** Screen lock timeout (5 min), disk encryption (LUKS)

---

### R3: Insider Threat (Self) (Accepted)

**Risk:** Developer (self) accidentally destroys data or leaks secrets

**Justification:**
- Moderate likelihood (human error)
- Detection after-the-fact (git history, logs)
- Mitigation partial (safety filters, confirmation prompts, backups)

**Acceptance:** Backups (weekly), safety filters, `--dangerous` flag for destructive commands

---

## Security Assumptions

**A1:** Dev machine is trusted (no malware, no keyloggers)

**A2:** Network is semi-trusted (LAN may have other devices, but no active attackers)

**A3:** Physical environment is secure (home office, no unauthorized visitors)

**A4:** Dependencies are from official PyPI (no typosquatting)

**A5:** MT5 broker credentials are strong (12+ char password, 2FA on broker account)

---

## Out of Scope

**OS1:** Cloud deployment (not applicable, local-first system)

**OS2:** Multi-user access control (single-user system)

**OS3:** DoS prevention (localhost-only, no public exposure)

**OS4:** Regulatory compliance (PCI-DSS, SOC 2, GDPR) — not handling customer data

---

## Related

- [ATTACK_SURFACE_ANALYSIS.md](ATTACK_SURFACE_ANALYSIS.md) — Entry points + attack vectors
- [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md) — Security configuration checklist
- [AGENT_OS_ARCHITECTURE.md](../01_ARCHITECTURE/AGENT_OS_ARCHITECTURE.md) — Safety filters

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Threat model validated against codebase + deployment
