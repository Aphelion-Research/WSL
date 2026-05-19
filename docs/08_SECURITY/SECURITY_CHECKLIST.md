# Security Checklist

**Status:** LIVE_GREEN  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Purpose:** Pre-deployment + routine security verification

---

## Initial Setup

### ✓ Filesystem Permissions

```bash
# Secrets directory
chmod 700 ~/Dominion/secrets
chmod 600 ~/Dominion/secrets/mt5.env

# Database files
chmod 644 ~/Dominion/data/dominion.duckdb
chmod 644 ~/.dominion/agent_os.db
chmod 644 ~/.ragd/ragd.db

# RAGD binary
chmod 755 ~/Dominion/ragd/build/ragd
```

**Verify:**
```bash
ls -la ~/Dominion/secrets/
# Expected: drwx------ (700) for directory, -rw------- (600) for mt5.env
```

---

### ✓ Git Configuration

**`.gitignore` entries:**
```gitignore
secrets/
*.env
*.key
*.pem
*.p12
*.pfx
.venv/
__pycache__/
*.pyc
*.db-wal
*.db-shm
```

**Pre-commit hook:**
```bash
# .git/hooks/pre-commit (executable)
#!/bin/bash
git diff --cached --name-only | grep -E "secrets/|\.env$|\.key$" && {
  echo "ERROR: Attempting to commit secrets"
  exit 1
}
python domdata/check_no_trading.py || {
  echo "ERROR: Trading code detected"
  exit 1
}
exit 0
```

**Enable hook:**
```bash
chmod +x .git/hooks/pre-commit
```

**Verify:**
```bash
echo "password=secret" > secrets/test.env
git add secrets/test.env
git commit -m "test"
# Expected: ERROR: Attempting to commit secrets
rm secrets/test.env
```

---

### ✓ Network Binding

**RAGD config** (`ragd/config.h` or CLI args):
```cpp
// Correct: localhost-only
config.host = "127.0.0.1";

// WRONG: binds to all interfaces
// config.host = "0.0.0.0";
```

**Verify:**
```bash
ss -tuln | grep 7474
# Expected: tcp LISTEN 127.0.0.1:7474 0.0.0.0:*
# NOT:      tcp LISTEN 0.0.0.0:7474 0.0.0.0:*
```

---

### ✓ Dependency Pinning

**`requirements.txt` with hashes:**
```
pandas==2.1.0 --hash=sha256:abc123...
numpy==1.25.2 --hash=sha256:def456...
scipy==1.11.1 --hash=sha256:ghi789...
```

**Generate hashes:**
```bash
pip hash pandas==2.1.0
# Expected: sha256:abc123...
```

**Install with verification:**
```bash
pip install -r requirements.txt --require-hashes
```

**Verify:**
```bash
pip freeze | grep pandas
# Expected: pandas==2.1.0 (exact version, no "==latest")
```

---

### ✓ Environment Variables

**Do NOT persist API keys to shell RC files:**
```bash
# WRONG (persisted to ~/.bashrc, leaks to shell history)
echo 'export NOMIC_API_KEY=abc123' >> ~/.bashrc

# Correct: one-time export (lost on shell exit)
export NOMIC_API_KEY=abc123
```

**Secure alternative (keyring):**
```bash
# Store in system keyring
secret-tool store --label="Nomic API Key" service nomic key api

# Retrieve when needed
export NOMIC_API_KEY=$(secret-tool lookup service nomic key api)
```

**Verify not logged:**
```bash
history | grep NOMIC_API_KEY
# Expected: (empty, or shows lookup command only, not actual key)
```

---

## Routine Checks (Monthly)

### ✓ Scan for Secrets in Git History

```bash
git log -p | grep -E "password|api_key|secret|token" --color=always | head -50
# Expected: no matches (or only references in docs, not actual secrets)
```

**Deep scan (slow):**
```bash
git log --all --pretty=format: --name-only | sort -u | xargs grep -E "password|api_key" 2>/dev/null
```

---

### ✓ Run domdata Scanner

```bash
python domdata/check_no_trading.py
# Expected: PASS (no trading code found)
```

**If fails:**
1. Review reported violations
2. Remove trading code or add to whitelist (if false positive)
3. Re-run scanner

---

### ✓ Check Filesystem Permissions

```bash
find ~/Dominion/secrets -type f ! -perm 600
# Expected: (empty, all files have 600 permissions)

find ~/.dominion -type f -name "*.db" ! -perm 644
# Expected: (empty, all DB files have 644 permissions)
```

---

### ✓ Review RAGD Query Log

```bash
tail -100 ~/.ragd/ragd.log | grep -E "POST /query" | awk '{print $1,$2,$NF}' | sort | uniq -c | sort -rn
# Expected: query patterns match expected usage (no unusual spikes)
```

**Red flags:**
- 1000+ queries in 1 minute (DoS attack)
- Queries for sensitive terms (`password`, `secret`)

---

### ✓ Review Agent OS Audit Log

```bash
sqlite3 ~/.dominion/agent_os.db "SELECT session_id, agent_name, status FROM agent_sessions_v2 ORDER BY started_at DESC LIMIT 10;"
# Expected: all sessions from expected agents (claude, self)

sqlite3 ~/.dominion/agent_os.db "SELECT filepath FROM agent_file_touches WHERE filepath LIKE '%secrets%';"
# Expected: (empty, no secret file touches)
```

---

### ✓ Dependency Security Audit

```bash
pip list --outdated
# Expected: check for known vulnerabilities in outdated packages

# Use safety tool (optional)
pip install safety
safety check
# Expected: no known vulnerabilities
```

**Update vulnerable packages:**
```bash
pip install --upgrade <package>
pip freeze > requirements.txt
# Regenerate hashes
```

---

### ✓ Backup Verification

```bash
ls -lh ~/Dominion/backups/
# Expected: weekly backups present (dominion_YYYYMMDD.duckdb, agent_os_YYYYMMDD.db)

# Test restore
cp ~/Dominion/backups/dominion_20260512.duckdb /tmp/test.duckdb
duckdb /tmp/test.duckdb "SELECT COUNT(*) FROM gold_master;"
# Expected: (no errors, count matches expected row count)
```

---

## Incident Response

### ✓ Secret Leak Response

**If secret leaked to git (not pushed):**
```bash
# 1. Remove commit
git reset --hard HEAD~1

# 2. Verify removed
git log -1 --pretty=format:"%H %s"

# 3. Rotate credential
# (Manual: change MT5 password, Nomic API key)
```

**If secret leaked to git (already pushed):**
```bash
# 1. Rotate credential immediately (FIRST PRIORITY)

# 2. Rewrite history (if private repo)
git filter-repo --path secrets/ --invert-paths
git push --force

# 3. If public repo: consider repo toxic, rotate all credentials
```

---

### ✓ Unauthorized Trading Response

**Detection:** MT5 broker alert, unexpected order

**Response:**
```bash
# 1. Close all positions immediately (via MT5 terminal)

# 2. Run scanner
python domdata/check_no_trading.py
# Review violations

# 3. Check git history for trading code
git log -p | grep -E "order_send|Position_Open" --color=always

# 4. Remove trading code
# (Manual: delete functions, revert commit)

# 5. Rotate credentials
# (Manual: change MT5 password)

# 6. Verify clean
python domdata/check_no_trading.py
# Expected: PASS
```

---

### ✓ Data Corruption Response

**Detection:** Integrity check fails

**Response:**
```bash
# 1. Verify corruption
duckdb ~/Dominion/data/dominion.duckdb "PRAGMA integrity_check;"
# Expected: (if corrupt, errors appear)

# 2. Stop data pipeline
# (Manual: kill pipeline process)

# 3. Restore from backup
cp ~/Dominion/backups/dominion_20260512.duckdb ~/Dominion/data/dominion.duckdb

# 4. Verify restored
duckdb ~/Dominion/data/dominion.duckdb "PRAGMA integrity_check;"
# Expected: ok

# 5. Investigate root cause
# (Review logs, identify corruption source)
```

---

## Pre-Deployment Checklist

### ✓ Before Pushing to Remote

- [ ] Run `python domdata/check_no_trading.py` (expected: PASS)
- [ ] Run `git diff --cached | grep -E "password|api_key|secret"` (expected: empty)
- [ ] Verify `.gitignore` excludes secrets (expected: `secrets/` entry present)
- [ ] Run test suite (expected: all pass)
- [ ] Review commit message (expected: no secrets mentioned)

---

### ✓ Before Running Data Pipeline

- [ ] Verify MT5 credentials exist (expected: `secrets/mt5.env` present, 600 permissions)
- [ ] Check RAGD health (expected: `curl http://127.0.0.1:7474/health` returns `"ok":true`)
- [ ] Verify disk space (expected: >10 GB free)
- [ ] Check last pipeline run (expected: <48h ago, or intentionally stale)

---

### ✓ Before Training Models

- [ ] Verify dataset exists (expected: `train_v1.parquet`, `val_v1.parquet`, `test_v1.parquet` present)
- [ ] Check dataset hashes (expected: match `dataset_v1_manifest.json`)
- [ ] Verify temporal split (expected: train < val < test timestamps, no overlap)
- [ ] Check feature count (expected: 347 features after leakage exclusion)

---

## Automated Checks (CI/CD)

**`.github/workflows/security.yml` (if using GitHub Actions):**
```yaml
name: Security Checks

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Check for secrets
        run: |
          git diff origin/main...HEAD --name-only | grep -E "secrets/|\.env$|\.key$" && exit 1 || exit 0
      - name: Run domdata scanner
        run: python domdata/check_no_trading.py
      - name: Dependency audit
        run: |
          pip install safety
          safety check
```

---

## Emergency Contacts

**MT5 Broker Support:** (Insert broker support contact)  
**Nomic API Support:** support@nomic.ai  
**Security Incidents:** (Insert internal escalation contact)

---

## Related

- [THREAT_MODEL.md](THREAT_MODEL.md) — Threat actors, attack trees
- [ATTACK_SURFACE_ANALYSIS.md](ATTACK_SURFACE_ANALYSIS.md) — Entry points, mitigations

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All checks validated on production system
