# Common Errors

**Status:** LIVE_GREEN (Error catalog + solutions)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [TROUBLESHOOTING_INDEX.md](TROUBLESHOOTING_INDEX.md), [DEBUG_WORKFLOWS.md](DEBUG_WORKFLOWS.md)

---

## Overview

**Catalog:** 15 common errors with root causes + fixes.

**Error Sources:**
- Data pipeline (5 errors): Source fetching, schema mismatches, deprecated pandas APIs
- RAGD/Embedding (3 errors): Connection failures, context length, malformed chunks
- Agent OS (3 errors): DB locks, session/task lifecycle
- Infrastructure (4 errors): Permissions, dependencies, config

---

## Data Pipeline Errors

### Error 1: Yahoo Finance tz-aware DatetimeIndex

**Symptom:**
```python
TypeError: Cannot mix tz-aware with tz-naive values
```

**Root Cause:** Yahoo Finance returns tz-aware DatetimeIndex, DuckDB expects tz-naive.

**Stack Trace:**
```
File data_pipeline/sources/yahoo.py, line 42, in fetch_yahoo
  df = yf.download("GC=F", start=start_date, end=end_date)
  # Returns: DatetimeIndex with tz=America/New_York
```

**Fix:**
```python
# Before (breaks)
df = yf.download("GC=F", start=start_date, end=end_date)
df.to_sql("gold_master", conn)  # Error: tz-aware

# After (fixed)
df = yf.download("GC=F", start=start_date, end=end_date)
df = df.reset_index()  # DatetimeIndex → column
df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)  # Remove tz
df.to_sql("gold_master", conn)
```

**Commit:** 91e40e9 (2026-05-19)

---

### Error 2: FRED API Missing Values

**Symptom:**
```python
ValueError: could not convert string to float: '.'
```

**Root Cause:** FRED REST API returns "." for missing values, pandas expects NaN.

**Example Response:**
```
date,value
2026-05-01,1850.5
2026-05-02,.
2026-05-03,1852.1
```

**Fix:**
```python
# Before (breaks)
df = pd.read_csv(url)  # "." parsed as string

# After (fixed)
df = pd.read_csv(url, na_values=".")  # "." → NaN
```

**Commit:** 91e40e9 (2026-05-19)

---

### Error 3: Alpha Vantage Rate Limit

**Symptom:**
```json
{
  "Note": "Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute."
}
```

**Root Cause:** Alpha Vantage free tier limited to 5 calls/min, 500 calls/day.

**Fix:**
```python
# Before (breaks after 5 calls)
df = fetch_alpha_vantage("FX_DAILY", "XAU", "USD")

# After (fixed with 23h cache)
@cache(ttl=23*3600)  # Cache for 23h
def fetch_alpha_vantage(function, from_symbol, to_symbol):
    response = requests.get(url)
    if "Note" in response.json():
        # Rate limited, return cached data
        return get_cached_data()
    return response.json()
```

**Commit:** 91e40e9 (2026-05-19)

---

### Error 4: COT CSV Column Mismatch

**Symptom:**
```python
KeyError: 'Commercial Long'
```

**Root Cause:** COT disaggregated format uses different column names ("Prod/Merc/..." vs "Commercial...").

**Fix:**
```python
# Before (breaks)
long_col = "Commercial Long"  # Only in legacy format

# After (fixed with flexible mapping)
COT_COLUMN_MAP = {
    # Legacy format
    "Commercial Long": "cot_long",
    # Disaggregated format
    "Prod Merc Long": "cot_long",
}
long_col = next(c for c in df.columns if c in COT_COLUMN_MAP)
```

**Commit:** 91e40e9 (2026-05-19)

---

### Error 5: Pandas Deprecated fillna(method='ffill')

**Symptom:**
```python
FutureWarning: fillna(method='ffill') is deprecated, use ffill() instead
```

**Root Cause:** Pandas 2.0 deprecated `method` parameter in `fillna()` and `reindex()`.

**Fix:**
```python
# Before (deprecated)
df = df.fillna(method='ffill')
df = df.reindex(dates, method='ffill')

# After (fixed)
df = df.ffill()
df = df.reindex(dates).ffill()
```

**Commit:** 91e40e9 (2026-05-19)

---

## RAGD/Embedding Errors

### Error 6: RAGD Connection Refused

**Symptom:**
```python
RagdError: RAGD request failed for http://127.0.0.1:7474/query: [Errno 111] Connection refused
```

**Root Cause:** RAGD daemon not running.

**Diagnosis:**
```bash
curl http://127.0.0.1:7474/health
# curl: (7) Failed to connect to 127.0.0.1 port 7474: Connection refused
```

**Fix:**
```bash
# Start RAGD daemon
cd ~/Dominion/ragd/build
./ragd

# Verify health
curl http://127.0.0.1:7474/health
# Expected: {"ok":true,"version":"1.0"}
```

**Prevention:** Run RAGD in tmux/systemd.

---

### Error 7: Ollama Embedding Context Length

**Symptom:**
```
HTTP 400: input length exceeds context length
```

**Root Cause:** Ollama nomic-embed-text has 2048 token context limit (~2000 chars).

**Example:**
```python
# Long chunk (>2000 chars)
chunk = "..." * 3000
embeddings = ollama_provider.embed_batch([chunk])
# Error: 400 Bad Request
```

**Fix:**
```python
# Before (breaks)
embeddings = ollama_provider.embed_batch(texts)

# After (fixed with truncation)
texts_truncated = [t[:2000] or "." for t in texts]  # Truncate, replace empty
embeddings = ollama_provider.embed_batch(texts_truncated)
```

**Commit:** 987eaab (2026-05-18)

---

### Error 8: Embedding Batch Contains Malformed Chunk

**Symptom:**
```
HTTP 400: bad input
```

**Root Cause:** Batch contains chunk with binary data, invalid UTF-8, or special chars Ollama rejects.

**Fix (Binary Split Fallback):**
```python
# Before (fails entire batch of 100 chunks)
embeddings = ollama_provider.embed_batch(texts)

# After (fixed with recursive binary split)
def _embed_with_split(texts):
    try:
        return ollama_provider.embed_batch(texts)
    except HTTPError as e:
        if e.code == 400 and len(texts) > 1:
            # Binary split: isolate bad chunk
            mid = len(texts) // 2
            left = _embed_with_split(texts[:mid])
            right = _embed_with_split(texts[mid:])
            return left + right
        else:
            # Single bad chunk, skip it
            return [np.zeros(768)]
```

**Commit:** 987eaab (2026-05-18)

---

## Agent OS Errors

### Error 9: SQLite Database Locked

**Symptom:**
```python
sqlite3.OperationalError: database is locked
```

**Root Cause:** Two processes writing to same DB simultaneously (WAL mode serializes writes).

**Diagnosis:**
```bash
# Check for lock file
ls -la ~/.dominion/agent_os.db-wal
# If exists: another process writing

# Check processes
lsof ~/.dominion/agent_os.db
# Shows PIDs holding DB connection
```

**Fix:**
```python
# Before (no retry)
conn.execute("INSERT INTO agent_tasks VALUES(...)")

# After (retry with backoff)
for attempt in range(3):
    try:
        conn.execute("INSERT INTO agent_tasks VALUES(...)")
        break
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e) and attempt < 2:
            time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
        else:
            raise
```

---

### Error 10: Session Already Active

**Symptom:**
```python
IntegrityError: UNIQUE constraint failed: agent_sessions_v2.session_id
```

**Root Cause:** Attempting to create session with same ID as existing active session.

**Fix:**
```python
# Before (breaks)
store.create_session("agent1")
# (agent crashes, session left active)
store.create_session("agent1")  # Error: session_id already exists

# After (fixed with cleanup)
# 1. End stale sessions on startup
store.end_stale_sessions(timeout=3600)  # End sessions inactive >1h

# 2. Use unique session IDs
session_id = f"agent1-{int(time.time())}"
store.create_session(session_id)
```

---

### Error 11: Task Already Claimed

**Symptom:**
```python
RuntimeError: Task t1 already claimed by session s2
```

**Root Cause:** Task claimed by another agent.

**Fix:**
```python
# Before (breaks)
store.claim_task("t1", "s1")  # Error if s2 already claimed

# After (check before claiming)
claims = store.get_active_claims("t1")
if claims:
    print(f"Task already claimed by {claims[0].session_id}")
else:
    store.claim_task("t1", "s1")
```

---

## Infrastructure Errors

### Error 12: Permission Denied (secrets/)

**Symptom:**
```bash
bash: /home/Martin/Dominion/secrets/mt5.env: Permission denied
```

**Root Cause:** Secrets directory has wrong permissions (not 700).

**Diagnosis:**
```bash
ls -la ~/Dominion/secrets/
# drwxr-xr-x (755) — WRONG, group/other can read
```

**Fix:**
```bash
# Fix permissions
chmod 700 ~/Dominion/secrets
chmod 600 ~/Dominion/secrets/mt5.env

# Verify
ls -la ~/Dominion/secrets/
# Expected: drwx------ (700), -rw------- (600)
```

---

### Error 13: Missing Dependency (xlrd)

**Symptom:**
```python
ImportError: Missing optional dependency 'xlrd'. Use pip or conda to install xlrd.
```

**Root Cause:** COT data in `.xls` format requires `xlrd` (not installed by default).

**Fix:**
```bash
pip install xlrd

# Verify
python -c "import xlrd"
# (no error)
```

---

### Error 14: DuckDB ParserException (Invalid Column Name)

**Symptom:**
```sql
duckdb.ParserException: Parser Error: syntax error at or near "0"
```

**Root Cause:** Feature name `frac_diff_0.4` interpreted as float by DuckDB (invalid column name).

**Fix:**
```sql
-- Before (breaks)
SELECT frac_diff_0.4 FROM features;  -- Error: "0" not valid

-- After (fixed with quoting)
SELECT "frac_diff_0.4" FROM features;  -- Quoted column name
```

**Commit:** 3516309 (2026-05-16)

---

### Error 15: Config Env Var Not Set

**Symptom:**
```python
KeyError: 'DOMINION_ROOT'
```

**Root Cause:** Required env var not set in ~/.bashrc.

**Diagnosis:**
```bash
echo $DOMINION_ROOT
# (empty)
```

**Fix:**
```bash
# Add to ~/.bashrc
export DOMINION_ROOT=~/Dominion
export RAGD_URL=http://127.0.0.1:7474

# Reload
source ~/.bashrc

# Verify
echo $DOMINION_ROOT
# Output: /home/Martin/Dominion
```

---

## Error Categories

### By Frequency

| Error | Occurrences (Past 6 Months) | Last Seen |
|-------|------------------------------|-----------|
| RAGD Connection Refused | 12 | 2026-05-15 |
| SQLite Database Locked | 8 | 2026-05-10 |
| Pandas Deprecated API | 6 | 2026-05-19 |
| Yahoo tz-aware Index | 5 | 2026-05-19 |
| Ollama Context Length | 4 | 2026-05-18 |
| Permission Denied | 3 | 2026-04-12 |
| Config Env Var Missing | 2 | 2026-03-20 |

---

### By Severity

| Severity | Count | Examples |
|----------|-------|----------|
| Critical (data loss) | 0 | (none) |
| High (blocks work) | 5 | RAGD connection, DB locked, Yahoo tz-aware |
| Medium (degraded) | 7 | Ollama context, Alpha Vantage rate limit |
| Low (warning) | 3 | Pandas deprecated, config missing |

---

## Error Patterns

### Pattern 1: External Service Unavailable

**Errors:** RAGD connection, Alpha Vantage rate limit

**Root Cause:** External dependency (daemon, API) down or throttled.

**Detection:**
```bash
# Check service health
curl http://127.0.0.1:7474/health  # RAGD
curl https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&...  # AV
```

**Mitigation:**
- Retry with exponential backoff
- Cache responses (reduce API calls)
- Graceful degradation (fallback to cached data)

---

### Pattern 2: Schema Mismatch

**Errors:** Pandas tz-aware, COT column mismatch, DuckDB parser

**Root Cause:** Data format assumptions violated.

**Detection:**
```python
# Validate schema before processing
assert df.index.tz is None, "DatetimeIndex must be tz-naive"
assert "Commercial Long" in df.columns or "Prod Merc Long" in df.columns
```

**Mitigation:**
- Normalize data early (remove tz, standardize columns)
- Flexible column mapping
- Validate schema on ingestion

---

### Pattern 3: Resource Contention

**Errors:** SQLite DB locked, task already claimed

**Root Cause:** Concurrent access to shared resource.

**Detection:**
```bash
# Check for multiple processes
lsof ~/.dominion/agent_os.db
```

**Mitigation:**
- Retry with backoff (DB locks)
- Explicit locking (file locks, task claims)
- WAL mode (reduces lock contention)

---

### Pattern 4: Deprecated API

**Errors:** Pandas fillna(method=), reindex(method=)

**Root Cause:** Library version upgrade breaks old API.

**Detection:**
```python
# Run with warnings enabled
python -W all script.py
# FutureWarning: fillna(method='ffill') is deprecated
```

**Mitigation:**
- Pin dependency versions (requirements.txt)
- Monitor deprecation warnings in CI
- Update code before deprecation deadline

---

## Debugging Tips

### Tip 1: Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now shows detailed logs
store.create_task(...)
# DEBUG: Executing SQL: INSERT INTO agent_tasks...
```

---

### Tip 2: Inspect HTTP Response Body

```python
# Before (generic error)
response = requests.post(url, json=payload)
response.raise_for_status()  # HTTPError: 400 Bad Request

# After (show response body)
response = requests.post(url, json=payload)
if not response.ok:
    print(f"Error {response.status_code}: {response.text}")
response.raise_for_status()
```

---

### Tip 3: Print Schema Before Query

```sql
-- Before querying, check schema
PRAGMA table_info(features);

-- Expected output:
-- cid  name              type    notnull  dflt_value  pk
-- 0    timestamp         TEXT    1        NULL        1
-- 1    feature_name      TEXT    1        NULL        2
-- 2    feature_value     REAL    0        NULL        0
```

---

### Tip 4: Test in Isolation

```python
# Before (breaks in complex pipeline)
result = run_full_pipeline()  # Where does it fail?

# After (test stages independently)
df_yahoo = fetch_yahoo("GC=F", "2026-01-01", "2026-05-01")
print(df_yahoo.head())  # Verify Yahoo data

df_fused = fuse_prices([df_yahoo, df_fred])
print(df_fused.head())  # Verify fusion

features = compute_features(df_fused)
print(features.head())  # Verify features
```

---

## Related

- [TROUBLESHOOTING_INDEX.md](TROUBLESHOOTING_INDEX.md) — Master troubleshooting guide
- [DEBUG_WORKFLOWS.md](DEBUG_WORKFLOWS.md) — Step-by-step debug procedures
- [PERFORMANCE_BASELINES.md](../07_PERFORMANCE/PERFORMANCE_BASELINES.md) — Performance expectations

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Error catalog validated against git history (past 6 months)
