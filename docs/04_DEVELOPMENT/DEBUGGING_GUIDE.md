---
doc_type: guide
system: Dominion
ragd_priority: 6
audience:
  - developer
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - debugging
  - development
  - troubleshooting
---

# Debugging Guide

**Purpose:** Systematic approach to debugging Dominion V2.

**Audience:** Developers, maintainers, future self.

---

## General Debugging Process

1. **Reproduce** — Trigger bug reliably
2. **Isolate** — Narrow scope (which component?)
3. **Hypothesize** — What could cause this?
4. **Test** — Validate hypothesis
5. **Fix** — Implement solution
6. **Verify** — Confirm fix works

---

## Common Issues

### 1. Pipeline Hangs (No Progress)

**Symptoms:**
- `python -m data_pipeline.cli run` hangs
- No log output for 5+ minutes

**Diagnosis:**
```bash
# Check process status
ps aux | grep python

# Check logs (last 50 lines)
tail -50 logs/dominion.log

# Check for deadlock (CPU usage 0%)
top
```

**Common Causes:**

**A. MT5 Connection Timeout**
- MT5 offline or connection hung
- **Fix:** Kill process, restart MT5, rerun
- **Prevention:** Add timeout (see [[BUG_BACKLOG]] #6)

**B. Database Lock**
- Another process has DuckDB lock
- **Fix:** `lsof data/dominion.db` (find process), kill it
- **Prevention:** Ensure single-writer

**C. Infinite Loop**
- Bug in feature calculation
- **Debug:** Attach debugger (pdb), find loop

---

### 2. Feature Computation Errors (NaN/Inf)

**Symptoms:**
- Features contain NaN or Inf
- Pipeline logs: "NaN detected, skipping bar"

**Diagnosis:**
```python
# Check feature matrix
import pandas as pd
df = pd.read_csv('features.csv')
print(df.isnull().sum())  # Count NaN per column
print((df == np.inf).sum())  # Count Inf per column
```

**Common Causes:**

**A. Division by Zero**
```python
# Bad
returns = (price - prev_price) / prev_price  # prev_price=0 → Inf

# Fix
if prev_price == 0:
    returns = 0.0
else:
    returns = (price - prev_price) / prev_price
```

**B. Log of Negative/Zero**
```python
# Bad
log_returns = np.log(price / prev_price)  # price=0 → -Inf

# Fix
if price <= 0 or prev_price <= 0:
    log_returns = 0.0
else:
    log_returns = np.log(price / prev_price)
```

**C. Invalid Input (Bad Tick)**
- Corrupted tick (price=0, price=NaN)
- **Fix:** Sanitize inputs (see [[TECH_DEBT_MAP]] #5)

---

### 3. Kalman Filter Divergence

**Symptoms:**
- Fused price = NaN or Inf
- Covariance matrix explodes (values >1e10)

**Diagnosis:**
```python
# Check covariance condition number
import numpy as np
P = kalman_filter.covariance
cond = np.linalg.cond(P)
print(f"Condition number: {cond}")  # >1e10 = ill-conditioned
```

**Fix:**
```python
# Stabilize covariance
if np.linalg.cond(P) > 1e10:
    P = (P + P.T) / 2  # Force symmetry
    P += 1e-6 * np.eye(P.shape[0])  # Add small diagonal
```

**See:** [[BUG_BACKLOG]] #1 (scheduled fix Phase 8)

---

### 4. HMM Not Converging

**Symptoms:**
- Baum-Welch runs 100+ iterations (vs 18 typical)
- Log-likelihood oscillates (not converging)

**Diagnosis:**
```python
# Monitor log-likelihood
hmm.fit(data, verbose=True)
# Output:
# Iteration 1: LL = -150
# Iteration 2: LL = -145
# ...
# Iteration 30: LL = -88  # Should converge by now
```

**Common Causes:**

**A. Poor Initialization**
- Random init lands in bad local minimum
- **Fix:** Use previous model params (warm start)

**B. Volatile Data**
- Bear regime dominant (high vol)
- **Fix:** Normalize features (StandardScaler)

**C. Too Many Features**
- 10 features → overfitting
- **Fix:** Reduce to 4 features (current config)

---

### 5. RAGD Queries Return Nothing

**Symptoms:**
- `ragd_query("Kalman fusion")` returns []
- Expected 5 results, got 0

**Diagnosis:**
```bash
# Check index exists
ls -lh ragd/index.db  # Should be ~10MB

# Check chunk count
sqlite3 ragd/index.db "SELECT COUNT(*) FROM chunks;"  # Should be ~7500
```

**Common Causes:**

**A. Index Not Built**
- Fresh install, no index
- **Fix:** `python scripts/build_ragd.py`

**B. Query Mismatch**
- Query "kalman" vs docs say "Kalman Filter"
- **Fix:** Use fuzzy search (already enabled)

**C. Index Corrupted**
- Crash during rebuild (see [[BUG_BACKLOG]] #2)
- **Fix:** Rebuild index

---

### 6. Tests Failing (Flaky)

**Symptoms:**
- `pytest tests/` fails randomly
- Passes locally, fails in CI

**Diagnosis:**
```bash
# Run 10× to detect flakiness
for i in {1..10}; do pytest tests/integration/test_pipeline.py; done
```

**Common Causes:**

**A. Race Condition**
- Threading bug (concurrent access)
- **Fix:** Add locks, use thread-safe data structures

**B. Timing Assumption**
- Test assumes operation completes in 1s
- **Fix:** Use event-driven wait (not sleep)

**C. Shared State**
- Test modifies global state, affects next test
- **Fix:** Use fixtures (tmp_path, isolated DB)

---

## Debugging Tools

### 1. pdb (Python Debugger)

**Usage:**
```python
import pdb

def compute_returns(prices):
    pdb.set_trace()  # Breakpoint
    returns = np.diff(prices) / prices[:-1]
    return returns
```

**Commands:**
- `n` — Next line
- `s` — Step into function
- `c` — Continue
- `p variable` — Print variable
- `l` — List code

---

### 2. Logging (Strategic)

**Principle:** Log inputs, outputs, key decisions.

```python
import logging
logger = logging.getLogger(__name__)

def fuse_sources(sources):
    logger.info(f"Fusing {len(sources)} sources")
    for source, value in sources.items():
        logger.debug(f"Source {source}: {value}")
    
    fused = kalman_fusion(sources)
    logger.info(f"Fused value: {fused}")
    return fused
```

**Levels:**
- DEBUG: Verbose (every source value)
- INFO: Key events (fusing X sources)
- WARNING: Anomalies (NaN detected)
- ERROR: Failures (source unavailable)

---

### 3. Profiling (Performance Debug)

**cProfile (CPU):**
```bash
python -m cProfile -o profile.stats -m data_pipeline.cli run
python -m pstats profile.stats
# > sort cumtime
# > stats 10  # Top 10 functions by time
```

**memory_profiler (Memory):**
```bash
pip install memory_profiler

# Add @profile decorator
from memory_profiler import profile

@profile
def compute_features(data):
    ...

# Run
python -m memory_profiler pipeline.py
```

---

### 4. Assert Statements (Sanity Checks)

**Use liberally:**
```python
def compute_returns(prices):
    assert len(prices) > 1, "Need at least 2 prices"
    returns = np.diff(prices) / prices[:-1]
    assert not np.any(np.isnan(returns)), "Returns contain NaN"
    assert not np.any(np.isinf(returns)), "Returns contain Inf"
    return returns
```

**Disable in production:** `python -O script.py` (disables asserts)

---

### 5. Git Bisect (Find Regression)

**When:** Feature worked, now broken (which commit?)

**Usage:**
```bash
git bisect start
git bisect bad HEAD  # Current commit is bad
git bisect good abc123  # Commit abc123 was good

# Git checks out midpoint, test
pytest tests/test_feature.py
git bisect good  # or bad

# Repeat until git finds first bad commit
```

---

## Debugging by Component

### Data Pipeline

**Log file:** `logs/pipeline.log`

**Key files:** `data_pipeline/cli.py`, `data_pipeline/ingestion.py`

**Common issues:**
- MT5 timeout (see #1)
- Database lock (see #1)
- Bad tick data (see #2)

**Debug commands:**
```bash
# Test ingestion only
python -m data_pipeline.cli ingest --symbol GC=F --date 2026-01-01

# Test fusion only (skip ingestion)
python -m data_pipeline.cli fuse --date 2026-01-01

# Test features only
python -m data_pipeline.cli features --date 2026-01-01
```

---

### Kalman Filter

**Log file:** `logs/kalman.log`

**Key files:** `kalman/filter.py`, `kalman/fusion.py`

**Common issues:**
- Divergence (see #3)
- Numerical instability

**Debug:**
```python
# Print state + covariance
print(f"State: {kf.state}")
print(f"Covariance:\n{kf.covariance}")
print(f"Condition number: {np.linalg.cond(kf.covariance)}")
```

---

### HMM Regime Detection

**Log file:** `logs/regime.log`

**Key files:** `regime/hmm.py`

**Common issues:**
- Slow convergence (see #4)
- Poor classification

**Debug:**
```python
# Print log-likelihood per iteration
hmm.fit(data, verbose=True)

# Print transition matrix
print(hmm.transmat_)
```

---

### RAGD

**Log file:** `logs/ragd.log`

**Key files:** `ragd/index.py`, `ragd/server.py`

**Common issues:**
- No results (see #5)
- Slow queries (>100ms)

**Debug:**
```bash
# Test query directly
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Kalman", "top_k": 5}'

# Check index size
sqlite3 ragd/index.db "SELECT COUNT(*) FROM chunks;"
```

---

## Emergency Procedures

### System Completely Broken

**Recovery:**
1. Git checkout last known good commit
2. Restore database from backup (`cp data/dominion.db.bak data/dominion.db`)
3. Rebuild RAGD (`python scripts/build_ragd.py`)
4. Verify system works (`pytest tests/unit/`)
5. Bisect to find bad commit (`git bisect`)

---

### Data Corruption

**Detection:**
```sql
-- Check for NaN/Inf in database
SELECT COUNT(*) FROM features WHERE bid IS NULL;
SELECT COUNT(*) FROM features WHERE returns_1m = 'Inf';
```

**Recovery:**
1. Identify corrupted date range
2. Drop corrupted data (`DELETE FROM features WHERE timestamp BETWEEN ...`)
3. Re-run pipeline for that date range
4. Verify (`SELECT COUNT(*) ...`)

---

## Related Documentation

- [[BUG_BACKLOG]] — Known bugs + workarounds
- [[TESTING_STRATEGY]] — Debugging via tests
- [[PROFILING_GUIDE]] — Performance debugging
- [[CODING_STANDARDS]] — Defensive programming

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** As new debug patterns discovered

**How to Add:**
1. Encounter bug
2. Document symptoms + diagnosis + fix
3. Add to appropriate section
4. Update [[BUG_BACKLOG]] if recurring
