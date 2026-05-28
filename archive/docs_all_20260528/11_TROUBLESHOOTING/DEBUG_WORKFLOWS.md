# Debug Workflows

**Status:** LIVE_GREEN (Step-by-step debug procedures)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [TROUBLESHOOTING_INDEX.md](TROUBLESHOOTING_INDEX.md), [COMMON_ERRORS.md](COMMON_ERRORS.md)

---

## Overview

**Purpose:** Step-by-step debug procedures for common failure scenarios.

**Workflows:**
1. Data Pipeline Failure
2. RAGD Query Returns Empty
3. Agent OS Task Stuck
4. Embedding Generation Fails
5. DuckDB Query Slow

---

## Workflow 1: Data Pipeline Failure

### Symptom

```bash
python data_pipeline/cli.py run
# ERROR: Pipeline failed at feature computation
```

---

### Step 1: Identify Failed Stage

```bash
# Run pipeline with verbose logging
python data_pipeline/cli.py run --verbose

# Expected output shows stages:
# [INFO] Fetching Yahoo Finance...
# [INFO] Fetching FRED...
# [INFO] Fetching Alpha Vantage...
# [INFO] Fetching COT...
# [INFO] Fusing prices...
# [INFO] Computing features...
# [ERROR] Feature computation failed: KeyError 'return_1'

# Note which stage failed
```

---

### Step 2: Test Failed Stage in Isolation

**If Yahoo Finance failed:**
```python
from data_pipeline.sources.yahoo import fetch_yahoo

df = fetch_yahoo("GC=F", "2026-01-01", "2026-05-01")
print(df.head())
print(df.columns)
print(df.dtypes)
# Check for tz-aware DatetimeIndex, missing columns
```

**If feature computation failed:**
```python
from data_pipeline.features.store import compute_all_features
import duckdb

conn = duckdb.connect("data/dominion.duckdb")
df = conn.execute("SELECT * FROM gold_master ORDER BY timestamp LIMIT 100").df()

features = compute_all_features(df)
print(features.head())
# Check which feature function raises error
```

---

### Step 3: Check Data Integrity

```sql
-- Check gold_master populated
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM gold_master;"
-- Expected: 1256 rows

-- Check for NULL values
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM gold_master WHERE close IS NULL;"
-- Expected: 0

-- Check date range
duckdb ~/Dominion/data/dominion.duckdb "SELECT MIN(timestamp), MAX(timestamp) FROM gold_master;"
-- Expected: 2022-01-01 to 2026-05-19
```

---

### Step 4: Check Dependencies

```bash
# Verify source APIs reachable
curl "https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?interval=1d&range=5d"
# Expected: JSON response

curl "https://api.stlouisfed.org/fred/series/observations?series_id=GOLDPMGBD228NLBM&api_key=<key>&file_type=json"
# Expected: JSON response

# Check API keys set
echo $ALPHA_VANTAGE_API_KEY
echo $FRED_API_KEY
# Expected: (non-empty)
```

---

### Step 5: Common Fixes

**Fix 1: Yahoo tz-aware DatetimeIndex**
```python
# Add to yahoo.py:
df = df.reset_index()
df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
```

**Fix 2: FRED missing values**
```python
# Add to fred.py:
df = pd.read_csv(url, na_values=".")
```

**Fix 3: Alpha Vantage rate limit**
```python
# Add to alpha_vantage.py:
@cache(ttl=23*3600)
def fetch_alpha_vantage(...):
    ...
```

---

### Step 6: Rebuild from Scratch

```bash
# Backup DB
cp ~/Dominion/data/dominion.duckdb ~/Dominion/data/dominion_backup.duckdb

# Delete DB
rm ~/Dominion/data/dominion.duckdb

# Re-run pipeline
python data_pipeline/cli.py run

# Verify
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM gold_master;"
```

---

## Workflow 2: RAGD Query Returns Empty

### Symptom

```bash
curl -X POST http://127.0.0.1:7474/query -H "Content-Type: application/json" -d '{"q":"Kalman filter","top_k":5}'
# {"results": []}
```

---

### Step 1: Check RAGD Health

```bash
curl http://127.0.0.1:7474/health
# Expected: {"ok":true,"version":"1.0"}

# If connection refused → RAGD not running
cd ~/Dominion/ragd/build && ./ragd
```

---

### Step 2: Check Index Size

```bash
# Check if index exists
ls -lh ~/.ragd/ragd.hnsw ~/.ragd/ragd.db

# Check chunk count
sqlite3 ~/.ragd/ragd.db "SELECT COUNT(*) FROM documents;"
# Expected: >1000 (if index built)

# If 0 → index empty, rebuild
cd ~/Dominion/ragd/build
./ragd index rebuild
```

---

### Step 3: Test BM25 vs Vector

```bash
# Test BM25 (keyword search)
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q":"Kalman","mode":"bm25","top_k":5}'

# Test vector (semantic search)
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q":"Kalman","mode":"vector","top_k":5}'

# If BM25 returns results but vector empty → embedding issue
```

---

### Step 4: Check Embeddings

```bash
# Check embedding cache
ls ~/.ragd/embeddings_cache/ | wc -l
# Expected: 7161 (one per chunk)

# Test embedding generation
curl -X POST http://127.0.0.1:7474/embed \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'
# Expected: {"embedding": [0.1, 0.2, ...]}

# If error → check Ollama running
curl http://localhost:11434/api/version
# Expected: {"version":"..."}
```

---

### Step 5: Inspect Indexed Documents

```sql
-- Check document types indexed
sqlite3 ~/.ragd/ragd.db "SELECT file_class, COUNT(*) FROM documents GROUP BY file_class;"
-- Expected: python: 150, markdown: 80, ...

-- Check if query term exists in documents
sqlite3 ~/.ragd/ragd.db "SELECT COUNT(*) FROM documents WHERE content LIKE '%Kalman%';"
-- Expected: >0 (if documents contain "Kalman")

-- If 0 → term not in index, expand query
```

---

### Step 6: Rebuild Index

```bash
# Backup old index
cp ~/.ragd/ragd.db ~/.ragd/ragd_backup.db
cp ~/.ragd/ragd.hnsw ~/.ragd/ragd_backup.hnsw

# Delete old index
rm ~/.ragd/ragd.db ~/.ragd/ragd.hnsw

# Rebuild
cd ~/Dominion/ragd/build
./ragd index rebuild

# Verify
curl -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q":"Kalman","top_k":5}'
# Expected: results array with >0 chunks
```

---

## Workflow 3: Agent OS Task Stuck

### Symptom

```bash
# Task created but never completed
sqlite3 ~/.dominion/agent_os.db "SELECT * FROM agent_tasks WHERE status='in_progress';"
# Shows task stuck for >1 hour
```

---

### Step 1: Check Task Claims

```sql
-- Check if task claimed
sqlite3 ~/.dominion/agent_os.db "SELECT * FROM agent_claims WHERE task_id='<task_id>' AND status='active';"

-- Check session status
sqlite3 ~/.dominion/agent_os.db "SELECT * FROM agent_sessions_v2 WHERE session_id='<session_id>';"

-- If session status='completed' but task still in_progress → orphaned task
```

---

### Step 2: Check for DB Locks

```bash
# Check for WAL file
ls -lh ~/.dominion/agent_os.db-wal

# If >10MB → checkpoint stuck
sqlite3 ~/.dominion/agent_os.db "PRAGMA wal_checkpoint(TRUNCATE);"

# Check for processes holding DB
lsof ~/.dominion/agent_os.db
# If multiple processes → lock contention
```

---

### Step 3: Check Agent Logs

```bash
# Check if agent process crashed
ps aux | grep python | grep dominion_agent

# Check system logs
journalctl --user | grep dominion_agent | tail -50

# Look for errors
grep -i "error\|exception" ~/.dominion/agent_os.log
```

---

### Step 4: Release Orphaned Claims

```sql
-- Release claim
sqlite3 ~/.dominion/agent_os.db "UPDATE agent_claims SET status='released', released_at=<now> WHERE task_id='<task_id>';"

-- Update task status
sqlite3 ~/.dominion/agent_os.db "UPDATE agent_tasks SET status='open', claimed_by_session='' WHERE task_id='<task_id>';"
```

---

### Step 5: End Stale Sessions

```python
from dominion_agent.store import AgentStore
store = AgentStore()

# End sessions inactive >1h
store.end_stale_sessions(timeout=3600)

# Verify
store.get_active_sessions()
# Expected: only currently active sessions
```

---

### Step 6: Re-claim Task

```python
from dominion_agent.store import AgentStore
store = AgentStore()

# Create new session
session_id = store.create_session("agent1")

# Claim task
store.claim_task("<task_id>", session_id)

# Work on task
# ...

# Complete task
store.update_task_status("<task_id>", "completed")
```

---

## Workflow 4: Embedding Generation Fails

### Symptom

```bash
python -c "from ragd_embed.pipeline import embed_texts; embed_texts(['test'])"
# ERROR: HTTP 400: input length exceeds context length
```

---

### Step 1: Check Ollama Running

```bash
# Check Ollama health
curl http://localhost:11434/api/version
# Expected: {"version":"..."}

# If connection refused → Ollama not running
ollama serve &

# Pull model if needed
ollama pull nomic-embed-text
```

---

### Step 2: Test Single Embedding

```python
from ragd_embed.providers.ollama import OllamaProvider

provider = OllamaProvider()
embedding = provider.embed(["short test text"])
print(f"Embedding dim: {len(embedding[0])}")
# Expected: 768
```

---

### Step 3: Check Text Length

```python
text = "..." * 5000  # Long text
print(f"Text length: {len(text)} chars")

# If >2000 chars → truncate
text_truncated = text[:2000] or "."
embedding = provider.embed([text_truncated])
```

---

### Step 4: Identify Bad Chunk

```python
# Binary split to isolate bad chunk
def find_bad_chunk(texts):
    try:
        provider.embed_batch(texts)
        return None  # All good
    except Exception as e:
        if len(texts) == 1:
            print(f"Bad chunk: {texts[0][:100]}...")
            return texts[0]
        mid = len(texts) // 2
        left_bad = find_bad_chunk(texts[:mid])
        if left_bad:
            return left_bad
        return find_bad_chunk(texts[mid:])

texts = ["chunk1", "chunk2", ..., "chunk100"]
bad = find_bad_chunk(texts)
print(f"Bad chunk: {bad}")
```

---

### Step 5: Handle Bad Chunks

```python
# Skip bad chunks, embed good ones
embeddings = []
for text in texts:
    try:
        emb = provider.embed([text[:2000] or "."])
        embeddings.append(emb[0])
    except Exception as e:
        print(f"Skipping bad chunk: {text[:50]}...")
        embeddings.append(np.zeros(768))  # Zero embedding
```

---

## Workflow 5: DuckDB Query Slow

### Symptom

```sql
-- Query takes >10s (expected: <1s)
duckdb ~/Dominion/data/dominion.duckdb "SELECT * FROM features WHERE feature_name='return_1';"
```

---

### Step 1: Check Table Size

```sql
-- Check row count
duckdb ~/Dominion/data/dominion.duckdb "SELECT COUNT(*) FROM features;"
-- If >10M rows → purge old data

-- Check DB file size
du -sh ~/Dominion/data/dominion.duckdb
-- If >10GB → purge or vacuum
```

---

### Step 2: Explain Query Plan

```sql
-- Check query plan
duckdb ~/Dominion/data/dominion.duckdb "EXPLAIN SELECT * FROM features WHERE feature_name='return_1';"

-- Expected output:
-- SEQ_SCAN (features)  -- Sequential scan (slow)
--   FILTER (feature_name = 'return_1')

-- If SEQ_SCAN → add index
```

---

### Step 3: Add Index

```sql
-- Create index on feature_name
duckdb ~/Dominion/data/dominion.duckdb "CREATE INDEX IF NOT EXISTS idx_features_name ON features(feature_name);"

-- Re-run query
duckdb ~/Dominion/data/dominion.duckdb "SELECT * FROM features WHERE feature_name='return_1';"
-- Expected: <1s
```

---

### Step 4: Vacuum Database

```sql
-- Reclaim space
duckdb ~/Dominion/data/dominion.duckdb "VACUUM;"

-- Check new size
du -sh ~/Dominion/data/dominion.duckdb
```

---

### Step 5: Purge Old Data

```sql
-- Delete data older than 3 years
duckdb ~/Dominion/data/dominion.duckdb "DELETE FROM features WHERE timestamp < '2023-01-01';"

-- Vacuum
duckdb ~/Dominion/data/dominion.duckdb "VACUUM;"
```

---

## Debug Tools

### Tool 1: cProfile (Python Profiling)

```bash
# Profile script
python -m cProfile -o output.prof script.py

# View with snakeviz
pip install snakeviz
snakeviz output.prof
```

---

### Tool 2: strace (System Call Tracing)

```bash
# Trace file I/O
strace -e open,read,write python script.py

# Trace network calls
strace -e socket,connect,sendto,recvfrom python script.py
```

---

### Tool 3: lsof (Open Files)

```bash
# Check which process has DB open
lsof ~/.dominion/agent_os.db

# Check network connections
lsof -i :7474  # RAGD port
```

---

### Tool 4: SQLite EXPLAIN

```sql
-- Check query plan
sqlite3 ~/.dominion/agent_os.db "EXPLAIN QUERY PLAN SELECT * FROM agent_tasks WHERE status='open';"

-- Expected: SEARCH (uses index) not SCAN (full table scan)
```

---

### Tool 5: curl (HTTP Debugging)

```bash
# Verbose HTTP request
curl -v -X POST http://127.0.0.1:7474/query \
  -H "Content-Type: application/json" \
  -d '{"q":"test","top_k":5}'

# Time request
curl -w "\nTime: %{time_total}s\n" http://127.0.0.1:7474/health
```

---

## General Debug Checklist

**Before Debugging:**
- [ ] Reproduce error reliably
- [ ] Check recent changes (git log)
- [ ] Check logs (~/.ragd/ragd.log)
- [ ] Verify environment (virtualenv active, env vars set)

**During Debugging:**
- [ ] Isolate failing component
- [ ] Test in isolation (not full pipeline)
- [ ] Add verbose logging
- [ ] Print intermediate values

**After Fix:**
- [ ] Verify fix works
- [ ] Add regression test
- [ ] Document root cause
- [ ] Update [COMMON_ERRORS.md](COMMON_ERRORS.md) if new error

---

## Related

- [TROUBLESHOOTING_INDEX.md](TROUBLESHOOTING_INDEX.md) — Master troubleshooting guide
- [COMMON_ERRORS.md](COMMON_ERRORS.md) — Error catalog with fixes
- [PERFORMANCE_BASELINES.md](../07_PERFORMANCE/PERFORMANCE_BASELINES.md) — Expected performance

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ Debug workflows validated on production issues
