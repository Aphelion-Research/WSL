# Troubleshooting Index

**Status:** LIVE_GREEN (Master troubleshooting guide)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [COMMON_ERRORS.md](COMMON_ERRORS.md), [DEBUG_WORKFLOWS.md](DEBUG_WORKFLOWS.md)

---

## Quick Reference

### Is it working?

**Health Checks:**
```bash
# RAGD
curl http://127.0.0.1:7474/health
# Expected: {"ok":true,"version":"1.0"}

# Agent OS
python -c "from dominion_agent.store import AgentStore; AgentStore().health()"
# Expected: (no error)

# Data Pipeline
python data_pipeline/cli.py health
# Expected: Health check passed (features fresh, IC tracked, gold_master populated)
```

---

### Where to start?

| Symptom | Go To |
|---------|-------|
| "Connection refused" | [RAGD Not Running](#ragd-not-running) |
| "Database is locked" | [SQLite Lock Contention](#sqlite-lock-contention) |
| "KeyError: ..." | [Missing Column/Env Var](#missing-columnsconfig) |
| "ImportError: ..." | [Missing Dependency](#missing-dependencies) |
| "Permission denied" | [File Permissions](#file-permissions) |
| Slow queries | [Performance Bottlenecks](#performance-issues) |
| Test failures | [Test Debugging](#test-failures) |
| Data mismatch | [Data Validation](#data-validation) |

---

## Common Problems

### RAGD Not Running

**Symptoms:**
```
RagdError: RAGD request failed for http://127.0.0.1:7474/query: [Errno 111] Connection refused
```

**Diagnosis:**
```bash
# Check if RAGD running
curl http://127.0.0.1:7474/health
# If connection refused → RAGD not running

# Check process
ps aux | grep ragd
# If empty → RAGD not started
```

**Fix:**
```bash
# Start RAGD
cd ~/Dominion/ragd/build
./ragd

# Verify
curl http://127.0.0.1:7474/health
```

**Autostart (systemd):**
```bash
# Create service file
cat > ~/.config/systemd/user/ragd.service <<EOF
[Unit]
Description=RAGD Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/Martin/Dominion/ragd/build
ExecStart=/home/Martin/Dominion/ragd/build/ragd
Restart=on-failure

[Install]
WantedBy=default.target
EOF

# Enable + start
systemctl --user enable ragd
systemctl --user start ragd
```

**See:** [COMMON_ERRORS.md#error-6-ragd-connection-refused](COMMON_ERRORS.md#error-6-ragd-connection-refused)

---

### SQLite Lock Contention

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Diagnosis:**
```bash
# Check for lock file
ls -la ~/.dominion/agent_os.db-wal
# If exists and >1MB → WAL checkpoint stuck

# Check processes
lsof ~/.dominion/agent_os.db
# Shows PIDs holding DB connection
```

**Fix (Immediate):**
```bash
# Kill processes holding lock
kill <PID>

# Force WAL checkpoint
sqlite3 ~/.dominion/agent_os.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

**Fix (Long-term):**
```python
# Add retry logic
import time
for attempt in range(3):
    try:
        conn.execute("INSERT INTO agent_tasks VALUES(...)")
        break
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e) and attempt < 2:
            time.sleep(0.1 * (2 ** attempt))
        else:
            raise
```

**See:** [COMMON_ERRORS.md#error-9-sqlite-database-locked](COMMON_ERRORS.md#error-9-sqlite-database-locked)

---

### Missing Columns/Config

**Symptoms:**
```python
KeyError: 'DOMINION_ROOT'
KeyError: 'Commercial Long'  # COT data
duckdb.CatalogException: Table "gold_master" does not exist
```

**Diagnosis:**
```bash
# Check env vars
echo $DOMINION_ROOT
echo $RAGD_URL
# If empty → not set

# Check DB schema
sqlite3 ~/.dominion/agent_os.db ".schema agent_tasks"
duckdb ~/Dominion/data/dominion.duckdb "PRAGMA table_info(gold_master);"
```

**Fix (Env Vars):**
```bash
# Add to ~/.bashrc
export DOMINION_ROOT=~/Dominion
export RAGD_URL=http://127.0.0.1:7474

# Reload
source ~/.bashrc
```

**Fix (DB Schema):**
```bash
# Re-run migrations
python -c "from dominion_agent.store import AgentStore; AgentStore()"

# Rebuild data pipeline
python data_pipeline/cli.py run
```

**See:** [COMMON_ERRORS.md#error-15-config-env-var-not-set](COMMON_ERRORS.md#error-15-config-env-var-not-set)

---

### Missing Dependencies

**Symptoms:**
```python
ImportError: Missing optional dependency 'xlrd'. Use pip or conda to install xlrd.
ModuleNotFoundError: No module named 'pytest'
```

**Diagnosis:**
```bash
# Check if in virtualenv
which python
# Expected: /home/Martin/Dominion/.venv/bin/python

# Check installed packages
pip list | grep <package>
```

**Fix:**
```bash
# Activate virtualenv
source ~/Dominion/.venv/bin/activate

# Install missing dependency
pip install xlrd pytest

# Verify
python -c "import xlrd; import pytest"
```

**See:** [COMMON_ERRORS.md#error-13-missing-dependency-xlrd](COMMON_ERRORS.md#error-13-missing-dependency-xlrd)

---

### File Permissions

**Symptoms:**
```bash
bash: /home/Martin/Dominion/secrets/mt5.env: Permission denied
sqlite3.OperationalError: unable to open database file
```

**Diagnosis:**
```bash
# Check permissions
ls -la ~/Dominion/secrets/
ls -la ~/.dominion/agent_os.db

# Expected:
# drwx------ (700) for secrets/
# -rw------- (600) for secrets/mt5.env
# -rw-r--r-- (644) for *.db
```

**Fix:**
```bash
# Fix secrets
chmod 700 ~/Dominion/secrets
chmod 600 ~/Dominion/secrets/mt5.env

# Fix databases
chmod 644 ~/.dominion/agent_os.db
chmod 644 ~/Dominion/data/dominion.duckdb
```

**See:** [SECURITY_CHECKLIST.md](../08_SECURITY/SECURITY_CHECKLIST.md#filesystem-permissions)

---

## Performance Issues

### Slow Data Pipeline

**Symptoms:**
- Pipeline takes >10 minutes (expected: <3 min)
- Feature computation >5 minutes (expected: <2 min)

**Diagnosis:**
```python
# Profile pipeline
python -m cProfile -o pipeline.prof data_pipeline/cli.py run
# View with snakeviz
```

**Common Causes:**
1. **Cold cache** — First run slower (no cached embeddings, features)
2. **Network timeout** — Alpha Vantage, Yahoo Finance slow
3. **DuckDB pivot** — >10M rows (expected: <2M)

**Fix:**
```bash
# Warm cache
python data_pipeline/cli.py run  # First run: 5 min
python data_pipeline/cli.py run  # Second run: 2 min (cached)

# Check row count
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM features;"
# If >10M → purge old data
```

**See:** [BOTTLENECK_ANALYSIS.md](../07_PERFORMANCE/BOTTLENECK_ANALYSIS.md)

---

### Slow RAGD Queries

**Symptoms:**
- Query takes >1s (expected: <50ms)
- Index build >1h (expected: <30 min)

**Diagnosis:**
```bash
# Check index size
du -sh ~/.ragd/ragd.hnsw
# If >1GB → rebuild with lower ef_construction

# Profile query
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q":"Kalman","top_k":5,"mode":"hybrid"}' \
  -w "\nTime: %{time_total}s\n"
```

**Fix:**
```bash
# Lower HNSW ef_construction (faster build, slightly lower recall)
# Edit ragd/config.h: ef_construction = 100 (was 200)

# Rebuild index
cd ~/Dominion/ragd/build
./ragd index rebuild
```

**See:** [OPTIMIZATION_OPPORTUNITIES.md](../07_PERFORMANCE/OPTIMIZATION_OPPORTUNITIES.md#3-lower-hnsw-ef_construction)

---

## Data Validation

### Data Pipeline Output Validation

**Check 1: gold_master populated**
```sql
-- Expected: 1256 rows (1256 days)
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM gold_master;"
```

**Check 2: Features computed**
```sql
-- Expected: 400 features × 1256 timestamps = 502,400 rows
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM features;"
```

**Check 3: IC tracked**
```sql
-- Expected: 400 features with IC values
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM ic_tracking WHERE ABS(ic) > 0.02;"
-- Expected: ~100 (high-IC features)
```

**Check 4: No NaN rows**
```sql
-- Expected: 0 (all NaN rows filtered)
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM features WHERE feature_value IS NULL;"
```

---

### Dataset Validation

**Check 1: Parquet files exist**
```bash
ls -lh ~/Dominion/data/train_v1.parquet ~/Dominion/data/val_v1.parquet ~/Dominion/data/test_v1.parquet
# Expected: 3 files, ~1-3 MB each
```

**Check 2: Temporal split**
```python
import pandas as pd
train = pd.read_parquet("data/train_v1.parquet")
val = pd.read_parquet("data/val_v1.parquet")
test = pd.read_parquet("data/test_v1.parquet")

# Check dates
print(f"Train: {train['timestamp'].min()} to {train['timestamp'].max()}")
print(f"Val: {val['timestamp'].min()} to {val['timestamp'].max()}")
print(f"Test: {test['timestamp'].min()} to {test['timestamp'].max()}")

# Expected: train < val < test (no overlap)
assert train['timestamp'].max() < val['timestamp'].min()
assert val['timestamp'].max() < test['timestamp'].min()
```

**Check 3: No leakage**
```python
# Check future data not in features
future_cols = [c for c in train.columns if 'forward' in c or 'future' in c]
print(f"Future columns: {future_cols}")
# Expected: [] (no forward-looking features)
```

---

## Test Failures

### Running Tests

```bash
# Run all tests
cd ~/Dominion
pytest

# Run specific module
pytest dominion_loader/tests/

# Run specific test
pytest dominion_loader/tests/test_cache.py::test_put_and_get

# Run with verbose output
pytest -v

# Run with print statements
pytest -s
```

---

### Common Test Failures

**Failure 1: doctor tests (expected)**
```
FAILED dominion_loader/tests/test_doctor.py::test_doctor_runs_without_crash
```
**Cause:** Doctor exits 1 when checks fail (test expects 0).  
**Fix:** See [TEST_COVERAGE_REPORT.md](../09_TESTING/TEST_COVERAGE_REPORT.md#issue-1-doctor-tests-failing).

**Failure 2: Import error**
```
ModuleNotFoundError: No module named 'dominion_loader'
```
**Cause:** Not in virtualenv or package not installed.  
**Fix:**
```bash
source ~/Dominion/.venv/bin/activate
pip install -e .
```

**Failure 3: Fixture not found**
```
fixture 'tmp_path' not found
```
**Cause:** Pytest version too old (<3.9).  
**Fix:**
```bash
pip install --upgrade pytest
```

---

## Debug Workflows

### Workflow 1: Data Pipeline Failure

**See:** [DEBUG_WORKFLOWS.md#workflow-1-data-pipeline-failure](DEBUG_WORKFLOWS.md#workflow-1-data-pipeline-failure)

---

### Workflow 2: RAGD Query Returns Empty

**See:** [DEBUG_WORKFLOWS.md#workflow-2-ragd-query-returns-empty](DEBUG_WORKFLOWS.md#workflow-2-ragd-query-returns-empty)

---

### Workflow 3: Agent OS Task Stuck

**See:** [DEBUG_WORKFLOWS.md#workflow-3-agent-os-task-stuck](DEBUG_WORKFLOWS.md#workflow-3-agent-os-task-stuck)

---

## Logs

### Log Locations

```bash
# RAGD
~/.ragd/ragd.log

# Agent OS
~/.dominion/agent_os.log (if exists)

# Data Pipeline
~/Dominion/data_pipeline/logs/pipeline.log (if exists)

# System logs
journalctl --user -u ragd  # If using systemd
```

---

### Log Analysis

**Search for errors:**
```bash
grep -i "error\|exception\|fail" ~/.ragd/ragd.log | tail -20
```

**Monitor live:**
```bash
tail -f ~/.ragd/ragd.log
```

**Count errors by type:**
```bash
grep "ERROR" ~/.ragd/ragd.log | awk '{print $5}' | sort | uniq -c | sort -rn
```

---

## Emergency Procedures

### Emergency 1: Restore from Backup

```bash
# Stop services
pkill ragd
pkill python  # Kill data pipeline

# Restore DBs
cp ~/Dominion/backups/dominion_20260518.duckdb ~/Dominion/data/dominion.duckdb
cp ~/Dominion/backups/agent_os_20260518.db ~/.dominion/agent_os.db

# Verify
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM gold_master;"
sqlite3 ~/.dominion/agent_os.db "SELECT COUNT(*) FROM agent_sessions_v2;"

# Restart services
cd ~/Dominion/ragd/build && ./ragd &
```

---

### Emergency 2: Rebuild RAGD Index

```bash
# Stop RAGD
pkill ragd

# Delete old index
rm ~/.ragd/ragd.hnsw ~/.ragd/ragd.db

# Rebuild
cd ~/Dominion/ragd/build
./ragd index rebuild

# Verify
curl http://127.0.0.1:7474/health
curl -X POST http://127.0.0.1:7474/query -H "Content-Type: application/json" -d '{"q":"test","top_k":1}'
```

---

### Emergency 3: Reset Agent OS

```bash
# WARNING: Destroys all sessions/tasks

# Backup first
cp ~/.dominion/agent_os.db ~/agent_os_backup.db

# Delete DB
rm ~/.dominion/agent_os.db

# Re-initialize
python -c "from dominion_agent.store import AgentStore; AgentStore()"

# Verify
sqlite3 ~/.dominion/agent_os.db "SELECT COUNT(*) FROM agent_os_migrations;"
# Expected: 2 (migrations 1 and 2)
```

---

## Getting Help

### Self-Service

1. Check [COMMON_ERRORS.md](COMMON_ERRORS.md) for error message
2. Run health checks (above)
3. Check logs (`~/.ragd/ragd.log`)
4. Search this troubleshooting index

---

### Documentation

- **Architecture:** [docs/01_ARCHITECTURE/](../01_ARCHITECTURE/)
- **API Reference:** [docs/05_API/](../05_API/)
- **Performance:** [docs/07_PERFORMANCE/](../07_PERFORMANCE/)
- **Security:** [docs/08_SECURITY/](../08_SECURITY/)
- **Testing:** [docs/09_TESTING/](../09_TESTING/)

---

### Reporting Bugs

**Template:**
```markdown
## Bug Report

**Symptom:** <error message or unexpected behavior>

**Steps to Reproduce:**
1. <step 1>
2. <step 2>
3. <step 3>

**Expected:** <what should happen>

**Actual:** <what actually happened>

**Environment:**
- Python version: `python --version`
- OS: `uname -a`
- Commit: `git rev-parse HEAD`

**Logs:**
```
<paste relevant log excerpt>
```

**Attempted Fixes:**
- <what you tried>
```

---

## Related

- [COMMON_ERRORS.md](COMMON_ERRORS.md) — Error catalog with fixes
- [DEBUG_WORKFLOWS.md](DEBUG_WORKFLOWS.md) — Step-by-step debug procedures
- [PERFORMANCE_BASELINES.md](../07_PERFORMANCE/PERFORMANCE_BASELINES.md) — Expected performance

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Troubleshooting procedures validated on production system
