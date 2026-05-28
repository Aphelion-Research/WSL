---
doc_type: backlog
system: Dominion
ragd_priority: 4
audience:
  - maintainer
  - developer
status: active
last_reviewed: 2026-05-19
tags:
  - backlog
  - bugs
  - issues
---

# Bug Backlog

**Purpose:** Known bugs not yet fixed.

**Status:** 12 bugs tracked (Phase 5).

**Principle:** Critical bugs fixed immediately. Low-priority bugs tolerated if workaround exists.

---

## Bug Format

```markdown
### Bug Title (Severity)

**Symptom:** [What goes wrong?]
**Reproduction:** [Steps to trigger]
**Impact:** [How bad is it?]
**Workaround:** [Temporary fix]
**Root Cause:** [Why it happens]
**Fix:** [How to fix]
**Effort:** [Time estimate]
**Status:** Open / In Progress / Fixed
```

---

## Severity Levels

- **Critical:** System crash, data loss, silent corruption
- **High:** Feature broken, incorrect results
- **Medium:** Degraded performance, cosmetic issues
- **Low:** Edge cases, minor inconveniences

---

## Critical Bugs (Fix Immediately)

### None (Phase 5)

All critical bugs fixed before Phase 5 completion.

---

## High Severity

### 1. Kalman Filter Divergence (Rare) (High)

**Symptom:** Kalman filter state explodes (NaN/Inf) after 1000+ updates.

**Reproduction:**
1. Run pipeline continuously for 7 days
2. Observe covariance matrix → Inf
3. Fused price = NaN

**Impact:**
- Pipeline crashes (NaN in features)
- Occurs ~1% of time (long-running sessions)

**Workaround:**
- Restart pipeline daily (cron job)
- Covariance reset after 1000 updates

**Root Cause:**
- Numerical instability in covariance propagation
- Rounding errors accumulate over time

**Fix:**
```python
# Add covariance stabilization
if np.linalg.cond(P) > 1e10:  # Condition number check
    P = (P + P.T) / 2  # Force symmetry
    P += 1e-6 * np.eye(P.shape[0])  # Add small diagonal
```

**Effort:** 1 day (implement + test)

**Status:** Open (workaround sufficient for Phase 5-6, fix in Phase 8)

---

### 2. RAGD Index Corruption on Crash (High)

**Symptom:** SQLite RAGD index corrupted if process killed during write.

**Reproduction:**
1. Start `python scripts/build_ragd.py`
2. Kill -9 during index build
3. Rerun → sqlite3.DatabaseError (corruption)

**Impact:**
- RAGD queries fail
- Rebuild required (10 min)

**Workaround:**
- Backup index before rebuild (`cp ragd/index.db ragd/index.db.bak`)
- Restore if corruption detected

**Root Cause:**
- SQLite write-ahead log (WAL) not enabled
- Crash during transaction = corruption

**Fix:**
```python
# Enable WAL mode
con = sqlite3.connect("ragd/index.db")
con.execute("PRAGMA journal_mode=WAL")
```

**Effort:** 1 hour

**Status:** Open (fix scheduled Phase 7)

---

## Medium Severity

### 3. Obsidian Broken Links (>50) (Medium)

**Symptom:** 63 broken links in vault (Phase 5 baseline).

**Reproduction:**
- Open vault in Obsidian
- Graph view shows unlinked notes
- Check "Unlinked mentions" panel

**Impact:**
- Navigation degraded
- RAGD may miss linked context

**Workaround:**
- Manually fix high-priority links
- Accept <50 broken links (target)

**Root Cause:**
- Docs created before corresponding vault notes
- Template links not yet filled in

**Fix:**
- Create missing vault notes
- Update broken links

**Effort:** 4 hours (manual, tedious)

**Status:** In Progress (ongoing through Phase 5)

**Target:** <50 broken links (Phase 5 goal)

---

### 4. HMM Slow Convergence (Medium)

**Symptom:** Baum-Welch takes 30+ iterations to converge (vs 18 typical).

**Reproduction:**
1. Train HMM on volatile data (Bear regime dominant)
2. Convergence: 30-40 iterations (150s vs 100s)

**Impact:**
- Weekly retraining 50% slower
- Not critical (runs offline)

**Workaround:**
- Accept slower convergence
- Better initialization (use previous params)

**Root Cause:**
- Poor initial parameters (random init)
- Volatile data = harder optimization

**Fix:**
```python
# Initialize from previous model
hmm_new = HMM(n_states=3)
hmm_new.transition_matrix = hmm_old.transition_matrix
hmm_new.fit(new_data, n_iter=20)  # Warm start
```

**Effort:** 2 hours

**Status:** Open (low priority, Phase 8)

---

### 5. Feature Computation NaN Propagation (Medium)

**Symptom:** Single NaN input → 100+ features = NaN (propagates).

**Reproduction:**
1. Inject NaN price (simulated bad tick)
2. Feature pipeline computes returns → NaN
3. 100+ derived features = NaN (returns used everywhere)

**Impact:**
- Skip bar (no predictions)
- Rare (<0.1% of bars)

**Workaround:**
- NaN detection + skip bar
```python
if np.any(np.isnan(features)):
    logger.warning("NaN detected, skipping bar")
    return None
```

**Root Cause:**
- No input validation (trust data sources)

**Fix:**
```python
# Sanitize inputs
def sanitize_price(price):
    if np.isnan(price) or np.isinf(price):
        return prev_price  # Use previous valid price
    return price
```

**Effort:** 1 day (validate all inputs)

**Status:** Open (workaround sufficient, fix Phase 6)

---

### 6. MT5 Connection Timeout (Medium)

**Symptom:** MT5 connection hangs (no timeout), blocks pipeline.

**Reproduction:**
1. Disconnect MT5 (close app)
2. Run `domdata capture GC=F`
3. Hangs indefinitely (no timeout)

**Impact:**
- Pipeline stuck (manual intervention)
- Rare (MT5 usually stable)

**Workaround:**
- Kill process, restart
- Monitor with watchdog (restart after 5 min hang)

**Root Cause:**
- MetaTrader5 Python package lacks timeout parameter

**Fix:**
```python
# Add timeout wrapper
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("MT5 connection timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(60)  # 60s timeout
try:
    client.connect()
finally:
    signal.alarm(0)
```

**Effort:** 2 hours

**Status:** Open (fix Phase 7)

---

## Low Severity

### 7. Dashboard Refresh Lag (Low)

**Symptom:** Streamlit dashboard lags (2-3s) on refresh.

**Reproduction:**
1. Open dashboard (streamlit run dashboard.py)
2. Click refresh
3. Wait 2-3s (slow query)

**Impact:**
- Minor annoyance
- Not critical (dashboard rarely used)

**Workaround:**
- Reduce query complexity (LIMIT 1000)

**Root Cause:**
- Query all 40K bars (no pagination)

**Fix:**
- Add pagination
- Cache query results (Redis)

**Effort:** 2 hours

**Status:** Open (low priority, Phase 10)

---

### 8. Vault Sync Race Condition (Low)

**Symptom:** Vault sync fails if commit + sync overlap.

**Reproduction:**
1. Commit docs change
2. Manual vault sync (python scripts/vault_sync.py) during post-commit hook
3. Error: "File already being processed"

**Impact:**
- Rare (<1% of commits)
- Retry succeeds

**Workaround:**
- Retry sync

**Root Cause:**
- No file locking (two processes write same file)

**Fix:**
```python
import fcntl

with open(file, 'w') as f:
    fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
    f.write(content)
```

**Effort:** 1 hour

**Status:** Open (low priority, Phase 8)

---

### 9. Feature IC Calculation Off-by-One (Low)

**Symptom:** IC computed using current bar returns (slight lookahead).

**Reproduction:**
1. Compute IC (feature vs 60-min forward returns)
2. Check timestamp alignment
3. Feature at t, returns at t (should be t+60min)

**Impact:**
- IC inflated ~5% (0.15 → 0.158)
- Not critical (out-of-sample validation unaffected)

**Workaround:**
- Document known bias

**Root Cause:**
- Index alignment bug (pandas shift)

**Fix:**
```python
# Shift returns forward (not backward)
returns_forward = returns.shift(-60)  # 60-min ahead
```

**Effort:** 30 min

**Status:** Open (fix Phase 6 during feature selection)

---

### 10. Log Files Not Rotated (Low)

**Symptom:** Log files grow unbounded (100MB+ after 6 months).

**Reproduction:**
1. Run pipeline for 6 months
2. Check logs/ directory
3. dominion.log = 120MB

**Impact:**
- Disk space waste (~1GB/year)
- Slow grep

**Workaround:**
- Manual cleanup (rm old logs)

**Root Cause:**
- No log rotation configured

**Fix:**
```python
# Add rotating file handler
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/dominion.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5  # Keep 5 files
)
```

**Effort:** 30 min

**Status:** Open (fix Phase 8)

---

### 11. Intelligence Report Markdown Formatting (Low)

**Symptom:** Generated reports have inconsistent heading levels.

**Reproduction:**
1. Generate intelligence report
2. Open in Obsidian
3. Some headings ##, some ###

**Impact:**
- Cosmetic only (renders fine)

**Workaround:**
- Accept inconsistency

**Root Cause:**
- Template evolution (3 revisions)

**Fix:**
- Standardize template

**Effort:** 15 min

**Status:** Open (low priority, Phase 6)

---

### 12. Pytest Slow on Full Suite (Low)

**Symptom:** `pytest tests/` takes 90s (vs 30s expected).

**Reproduction:**
1. Run pytest tests/
2. Time: ~90s (94 tests)

**Impact:**
- Minor annoyance (CI slower)

**Workaround:**
- Run unit tests only (`pytest tests/unit/`, 10s)

**Root Cause:**
- Integration tests slow (real DuckDB writes)
- E2E tests very slow (10s each)

**Fix:**
- Parallelize tests (`pytest -n 4`)
- Mock slow operations

**Effort:** 2 hours

**Status:** Open (fix Phase 10 CI optimization)

---

## Bug Statistics

**Total bugs:** 12

**By Severity:**
- Critical: 0
- High: 2
- Medium: 4
- Low: 6

**By Status:**
- Open: 11
- In Progress: 1 (Obsidian links)
- Fixed: 0 (since last triage)

**Avg Age:** 2 months (oldest: Kalman divergence, 5 months)

---

## Triage Schedule

**Weekly:** Review critical/high bugs (fix immediately)

**Monthly:** Review medium bugs (schedule fixes)

**Quarterly:** Review low bugs (batch fix or close as "won't fix")

**Last Triage:** 2026-05-19 (Phase 5)

**Next Triage:** 2026-06-19 (Phase 6 start)

---

## Fix Priority (Phase 6-10)

### Phase 6 (Q2-Q3 2026)
- [ ] Feature IC off-by-one (#9) — 30 min
- [ ] Feature NaN propagation (#5) — 1 day
- [ ] Intelligence report formatting (#11) — 15 min

### Phase 7 (Q3-Q4 2026)
- [ ] RAGD corruption (#2) — 1 hour
- [ ] MT5 connection timeout (#6) — 2 hours

### Phase 8 (Q4 2026 - Q1 2027)
- [ ] Kalman divergence (#1) — 1 day
- [ ] HMM slow convergence (#4) — 2 hours
- [ ] Vault sync race condition (#8) — 1 hour
- [ ] Log rotation (#10) — 30 min

### Phase 10 (Q4 2027 - Q1 2028)
- [ ] Dashboard lag (#7) — 2 hours
- [ ] Pytest slow (#12) — 2 hours

### Deferred
- Obsidian broken links (#3) — Ongoing (manual, <50 target)

---

## Won't Fix

None currently. All bugs have viable workarounds or scheduled fixes.

---

## Related Documentation

- [[FEATURE_BACKLOG]] — Feature requests
- [[TECH_DEBT_MAP]] — Architectural debt
- [[ENHANCEMENT_BACKLOG]] — Non-bug improvements
- [[TESTING_STRATEGY]] — Bug prevention

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Weekly (critical/high), Monthly (medium/low)

**How to Add Bug:**
1. Reproduce + document steps
2. Assess severity (Critical/High/Medium/Low)
3. Document workaround (if any)
4. Estimate fix effort
5. Triage (fix now vs schedule vs defer)
