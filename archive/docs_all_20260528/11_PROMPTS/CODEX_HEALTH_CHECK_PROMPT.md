---
doc_type: prompt
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - prompt
  - health
  - validation
---

# CODEX Health Check Prompt

**Use Case:** Platform health validation  
**Complexity:** Low  
**Duration:** 5-10 minutes

---

## Context

Validate Dominion platform health.

When: Before major changes, after edits, or scheduled check.

Repository: `/home/Martin/Dominion`

---

## Mission

Run full validation suite and report status.

---

## Workflow

### Step 1: Trading Safety (1 min) — CRITICAL

```bash
python domdata/check_no_trading.py
```

**Expected:** `PASS: no forbidden trading tokens outside allowlist`

**If FAIL:**
- STOP immediately
- Find trading code: `grep -r "order_send\|order_check\|TRADE_ACTION" .`
- Remove all trading code
- Re-run check
- Do NOT proceed until PASS

### Step 2: Python Tests (2 min)

```bash
python -m pytest -q
```

**Expected:** `XXX passed` (426+ passing as of 2026-05-19)

**If failures:**
```bash
# Verbose output
python -m pytest -v

# Single failed test
python -m pytest tests/[module]/test_[file].py::test_[name] -v
```

### Step 3: C++ Tests (2 min)

```bash
ctest --test-dir ragd/build --output-on-failure
```

**Expected:** `100% tests passed` (24/24 as of 2026-05-19)

**If failures:**
- Check build: `cmake --build ragd/build`
- Re-run failing test
- Check logs: `cat ragd/build/Testing/Temporary/LastTest.log`

### Step 4: Platform Health (1 min)

```bash
python scripts/dominion_cli.py doctor --offline --json
```

**Expected output:**
```json
{
  "overall": "ok" | "warn" | "error",
  "subsystems": {
    "ragd": "ok",
    "tests": "ok",
    "vault": "ok",
    ...
  }
}
```

**Status meanings:**
- `ok`: All healthy
- `warn`: Minor issues, system functional
- `error`: Critical issues, action needed

### Step 5: RAGD Daemon (1 min)

```bash
curl http://127.0.0.1:7474/health
```

**Expected:**
```json
{
  "status": "ok",
  "uptime_seconds": 3600,
  "active_chunks": 7159
}
```

**If unreachable:**
```bash
# Check process
ps aux | grep ragd

# Restart
pkill ragd
ragd/build/ragd --db data/ragd.db --host 127.0.0.1 --port 7474 --daemon
```

### Step 6: Vault Integrity (1 min)

```bash
python scripts/dominion_cli.py vault doctor --json | jq '.ok, .total_notes, (.broken_links | length)'
```

**Expected:**
- `ok`: true or false
- `total_notes`: 900+ (945 as of 2026-05-19)
- `broken_links`: <100 (many are template examples)

### Step 7: Quick Spot Check (1 min)

```bash
# Check critical files exist
ls /home/Martin/Dominion/AGENT_HANDOFF.md
ls data/dominion.duckdb
ls data/ragd.db

# Check git status
git status

# Check disk space
df -h | grep -E "/$|/home"
```

---

## Validation

Platform healthy when:
- [ ] Trading check: PASS
- [ ] Python tests: All passing
- [ ] C++ tests: All passing
- [ ] Platform health: ok or warn (not error)
- [ ] RAGD daemon: Running
- [ ] Vault: <100 broken links
- [ ] Critical files present

---

## Output

**Health report format:**

```markdown
# Platform Health Check

**Date:** 2026-05-19  
**Status:** HEALTHY | DEGRADED | CRITICAL

## Results

| Check | Status | Details |
|---|---|---|
| Trading Safety | ✓ PASS | No trading code |
| Python Tests | ✓ PASS | 426/426 passing |
| C++ Tests | ✓ PASS | 24/24 passing |
| Platform Health | ✓ OK | No errors |
| RAGD Daemon | ✓ Running | 7159 chunks |
| Vault | ✓ OK | 945 notes, 63 broken links |
| Disk Space | ✓ OK | 45% used |

## Summary

Platform status: HEALTHY

All checks passed. System operational.

## Recommended Actions

[None | List any follow-ups]
```

---

## Status Levels

### HEALTHY
- All checks pass
- No warnings
- System fully operational

### DEGRADED
- Core checks pass (trading, tests)
- Some warnings (broken links, stale data)
- System functional but needs attention

### CRITICAL
- Core checks fail (trading check or tests)
- System not safe to use
- Immediate action required

---

## Common Issues

**Trading check fails:**
- STOP everything
- Remove trading code
- Re-validate

**Tests fail:**
- Check recent changes: `git log -5 --oneline`
- Revert if needed: `git revert HEAD`
- Debug specific failures

**RAGD unreachable:**
- Check logs: `tail -100 logs/ragd.log`
- Restart daemon
- Rebuild if needed

**Vault broken links:**
- Most are template examples (acceptable)
- Real broken links: fix or document

---

## Scheduled Checks

**Daily:** Quick check (Steps 1-4)  
**Weekly:** Full check (all steps)  
**Before major changes:** Full check  
**After major changes:** Full check  
**Before PRs:** Full check

---

## Automation

**Add to cron:**
```bash
# Daily health check at 9am
0 9 * * * cd /home/Martin/Dominion && python scripts/health_check.py --json > logs/health-$(date +\%Y\%m\%d).json
```

---

## Related Prompts

- [[CODEX_REPO_AUDIT_PROMPT]] — Deep health assessment
- [[CODEX_BUGFIX_PROMPT]] — Fix issues found

---

## Retrieval Hints

- "health check"
- "platform validation"
- "system status"
- "health report"
