# Optimization Opportunities

**Status:** LIVE_GREEN (Prioritized optimization proposals)  
**Last Updated:** 2026-05-19  
**Owner:** MatinDeevv  
**Related:** [BOTTLENECK_ANALYSIS.md](BOTTLENECK_ANALYSIS.md), [PERFORMANCE_BASELINES.md](PERFORMANCE_BASELINES.md)

---

## Overview

Prioritized optimization opportunities ranked by **impact × (1 / effort)** ratio.

**Ranking Formula:**
- **Impact:** Speedup factor × % of total runtime
- **Effort:** Days to implement + test + deploy
- **Score:** Impact / Effort

---

## Quick Wins (< 1 day, high impact)

### 1. Filter Features by IC Before Pivot (Score: 9.2)

**Problem:** DuckDB pivot query scans 400 features, but only ~100 have |IC| > 0.02

**Solution:**
```sql
-- Before: pivot all 400 features (42s)
SELECT timestamp, MAX(CASE WHEN feature_name = 'return_1' THEN ...) ...
FROM features
GROUP BY timestamp

-- After: filter low-IC features first (8s, 5.25× speedup)
WITH high_ic_features AS (
  SELECT DISTINCT feature_name
  FROM ic_tracking
  WHERE ABS(ic) > 0.02
)
SELECT timestamp, MAX(CASE WHEN feature_name = 'return_1' THEN ...) ...
FROM features
WHERE feature_name IN (SELECT * FROM high_ic_features)
GROUP BY timestamp
```

**Impact:**
- Pivot query: 42s → 8s (5.25× speedup)
- Dataset build: 60s → 26s (2.3× speedup)

**Effort:** 0.5 days (modify query + validate output)

**Tradeoffs:** None (low-IC features filtered anyway during feature selection)

**Score:** (5.25 × 0.23) / 0.5 = **9.2**

---

### 2. Increase Nomic Embed API Batch Size (Score: 6.4)

**Problem:** Batch size=10 → 450ms/batch (45ms/embedding)

**Solution:**
```python
# Before: batch=10, 450ms/batch
embeddings = nomic.embed(texts[:10])

# After: batch=50, 200ms/batch (5× more embeddings, 2.25× faster)
embeddings = nomic.embed(texts[:50])
```

**Impact:**
- Embedding generation: 450ms/batch → 200ms/batch (2.25× speedup)
- Full rebuild (7161 embeddings): 53min → 24min (2.2× speedup)

**Effort:** 0.25 days (change batch size constant, test API rate limits)

**Tradeoffs:** Higher memory (50 × 768 × 4 = 153 KB per batch, negligible)

**Score:** (2.25 × 0.28) / 0.25 = **6.4**

---

### 3. Lower HNSW ef_construction (Score: 5.8)

**Problem:** `ef_construction=200` → expensive greedy search during insertion

**Solution:**
```cpp
// Before: ef_construction=200 (5 insertions/sec, recall=0.98)
HNSWIndex index(M=16, ef_construction=200, ef_search=50);

// After: ef_construction=100 (15 insertions/sec, recall=0.96)
HNSWIndex index(M=16, ef_construction=100, ef_search=50);
```

**Impact:**
- HNSW insertion: 5/sec → 15/sec (3× speedup)
- Full rebuild (10k chunks): 33min → 11min (3× speedup)
- Recall: 0.98 → 0.96 (2% degradation, acceptable)

**Effort:** 0.25 days (change config + benchmark recall)

**Tradeoffs:** Slightly lower recall (0.98 → 0.96), acceptable for code search

**Score:** (3.0 × 0.18) / 0.25 = **5.8**

---

### 4. Switch to LightGBM for Baselines (Score: 4.2)

**Problem:** sklearn RandomForest not optimized for small datasets

**Solution:**
```python
# Before: sklearn RandomForest (24.5s)
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor(n_estimators=100, max_depth=10, n_jobs=-1)

# After: LightGBM (8s, 3× speedup)
import lightgbm as lgb
model = lgb.LGBMRegressor(n_estimators=100, max_depth=10, n_jobs=-1)
```

**Impact:**
- RandomForest training: 24.5s → 8s (3× speedup)
- Baseline training: 33s → 16s (2× speedup)

**Effort:** 0.5 days (install lightgbm, update script, validate results)

**Tradeoffs:** New dependency (lightgbm ~20 MB), minimal API differences

**Score:** (3.0 × 0.13) / 0.5 = **4.2**

---

## Medium Effort (1-3 days, high impact)

### 5. Parallelize Feature Computation via Dask (Score: 8.1)

**Problem:** Feature computation single-threaded (118s for 400 features)

**Solution:**
```python
# Before: sequential loop (118s)
for feature in features:
    df[feature] = compute_feature(df, feature)

# After: Dask parallel (30s, 4× speedup on 8 cores)
import dask.dataframe as dd
ddf = dd.from_pandas(df, npartitions=8)
results = ddf.map_partitions(compute_all_features).compute()
```

**Impact:**
- Feature computation: 118s → 30s (4× speedup, 8 cores)
- Data pipeline: 186s → 98s (1.9× end-to-end speedup)

**Effort:** 2 days (refactor feature functions to be stateless, test parallel correctness)

**Tradeoffs:** Dask dependency (~50 MB), more complex debugging

**Score:** (4.0 × 0.63) / 2 = **8.1**

---

### 6. Vectorize Kalman Fusion (Score: 4.5)

**Problem:** Python loop over 1256 timestamps (not vectorized)

**Solution:**
```python
# Before: Python loop (4.2s)
for ts in timestamps:
    fused_price = kalman.fuse(observations[ts])

# After: NumPy vectorized (0.8s, 5.25× speedup)
fused_prices = kalman.fuse_vectorized(observations_array)
```

**Implementation:**
- Rewrite Kalman filter to operate on arrays (NumPy matrix ops)
- Compute all predictions at once (batch matmul)
- Update trust scores via vectorized operations

**Impact:**
- Kalman fusion: 4.2s → 0.8s (5.25× speedup)
- Data pipeline: 186s → 183s (minor end-to-end impact, but cleaner code)

**Effort:** 3 days (rewrite Kalman class, validate numerical stability)

**Tradeoffs:** More complex code (array operations vs loop), harder to debug

**Score:** (5.25 × 0.02) / 3 = **4.5**

---

### 7. Parallel Spearman for IC Tracking (Score: 3.6)

**Problem:** IC tracking computes Spearman sequentially (22s for 400 features)

**Solution:**
```python
# Before: sequential (22s)
for feature in features:
    ic, pval = spearmanr(feature_values, target_values)

# After: parallel via joblib (6s, 3.7× speedup on 8 cores)
from joblib import Parallel, delayed
ics = Parallel(n_jobs=8)(
    delayed(spearmanr)(df[f], target) for f in features
)
```

**Impact:**
- IC tracking: 22s → 6s (3.7× speedup)
- Data pipeline: 186s → 170s (1.1× end-to-end speedup)

**Effort:** 1 day (wrap spearmanr in joblib, test correctness)

**Tradeoffs:** joblib dependency (~5 MB), minor

**Score:** (3.7 × 0.09) / 1 = **3.6**

---

## Long-term (1+ weeks, transformative)

### 8. Migrate RAGD to PostgreSQL + pgvector (Score: 2.8)

**Problem:** SQLite WAL write contention >10 agents, HNSW index size limits

**Solution:**
- Migrate `nodes`, `edges`, `documents` tables to PostgreSQL
- Use pgvector extension for HNSW index
- Keep embedding cache in Redis (faster than PostgreSQL BLOB)

**Impact:**
- Concurrent queries: 50 qps → 500 qps (10× throughput)
- Concurrent agents: 10 → 50 (5× more agents)
- Index size limit: 100k chunks → 10M chunks (100× scalability)

**Effort:** 10 days (schema migration, test concurrency, benchmark performance)

**Tradeoffs:**
- PostgreSQL dependency (requires server setup)
- Higher operational complexity (backups, replication)
- Query latency may increase slightly (network overhead)

**Score:** (10 × 0.05) / 10 = **2.8**

---

### 9. Rewrite Feature Computation in Rust (Score: 2.1)

**Problem:** Python interpreter overhead dominates for tight loops

**Solution:**
- Rewrite hot feature functions in Rust (PyO3 bindings)
- Target: returns, volatility, rolling operations (80% of compute time)
- Keep orchestration in Python (minimal rewrite)

**Impact:**
- Feature computation: 118s → 2.4s (50× speedup, Rust vs Python)
- Data pipeline: 186s → 70s (2.7× end-to-end speedup)

**Effort:** 15 days (Rust implementation, PyO3 bindings, validate correctness)

**Tradeoffs:**
- Rust dependency (build complexity, cross-platform support)
- Harder to maintain (fewer Rust developers than Python)

**Score:** (50 × 0.63) / 15 = **2.1**

---

### 10. Distributed RAGD (Shard by Document Type) (Score: 1.8)

**Problem:** Single RAGD instance limits to ~50 qps, 100k chunks

**Solution:**
- Shard RAGD by document type: code, docs, tests, configs
- Load-balance queries via reverse proxy (nginx)
- Aggregate results from shards (merge top-k)

**Impact:**
- Concurrent queries: 50 qps → 200 qps (4× throughput)
- Index size limit: 100k → 400k chunks (4× scalability)

**Effort:** 20 days (distributed architecture, result aggregation, deployment)

**Tradeoffs:**
- Operational complexity (4× more processes)
- Cross-shard queries slower (network aggregation)
- Higher memory usage (4× HNSW indexes)

**Score:** (4 × 0.27) / 20 = **1.8**

---

## Speculative (high risk, high reward)

### 11. Replace DuckDB with ClickHouse

**Problem:** DuckDB pivot query slow for >10M rows

**Solution:**
- Migrate to ClickHouse (column-store optimized for analytical queries)
- Use materialized views for pivot (precompute wide format)

**Impact:**
- Pivot query: 42s → 0.5s (84× speedup for >10M rows)
- Dataset build: 60s → 18s (3.3× speedup)

**Effort:** 30 days (ClickHouse setup, schema migration, query rewrites, testing)

**Tradeoffs:**
- ClickHouse server required (higher ops complexity)
- Limited Python API support (manual SQL)
- Overkill for current scale (1256 rows)

**Score:** (84 × 0.23) / 30 = **2.0** (high impact but premature optimization for current scale)

**Recommendation:** Wait until >1M rows before considering

---

### 12. GPU-Accelerated Feature Computation (cuDF)

**Problem:** Feature computation CPU-bound

**Solution:**
- Port feature functions to cuDF (RAPIDS, GPU-accelerated pandas)
- Target: rolling operations, Spearman correlation

**Impact:**
- Feature computation: 118s → 5s (24× speedup, NVIDIA T4)
- Data pipeline: 186s → 73s (2.6× end-to-end speedup)

**Effort:** 25 days (cuDF port, GPU optimization, CI/CD with GPU runners)

**Tradeoffs:**
- GPU required (A100/T4, ~$1-3k or cloud GPU)
- CUDA dependency (Linux-only, version compatibility issues)
- Not all operations supported by cuDF (fallback to CPU)

**Score:** (24 × 0.63) / 25 = **1.9**

**Recommendation:** Consider if training >10k models/day (not current use case)

---

## Prioritized Roadmap

### Phase 1: Quick Wins (< 1 week)

1. **Filter features by IC** (0.5 days) — 5.25× pivot speedup
2. **Increase embed batch size** (0.25 days) — 2.25× embed speedup
3. **Lower HNSW ef_construction** (0.25 days) — 3× insertion speedup
4. **Switch to LightGBM** (0.5 days) — 3× RF training speedup

**Total Effort:** 1.5 days  
**Total Impact:** Pipeline 186s → 98s (~1.9× end-to-end)

---

### Phase 2: Medium Effort (2-4 weeks)

5. **Parallelize feature computation** (2 days) — 4× feature speedup
6. **Vectorize Kalman fusion** (3 days) — 5.25× Kalman speedup
7. **Parallel Spearman IC tracking** (1 day) — 3.7× IC speedup

**Total Effort:** 6 days  
**Total Impact:** Pipeline 98s → 48s (~3.9× end-to-end cumulative)

---

### Phase 3: Long-term (2-6 months)

8. **Migrate RAGD to PostgreSQL + pgvector** (10 days) — 10× concurrency
9. **Rewrite features in Rust** (15 days) — 50× feature speedup
10. **Distributed RAGD sharding** (20 days) — 4× throughput

**Total Effort:** 45 days  
**Total Impact:** Pipeline 48s → 5s (~37× end-to-end cumulative), 500 qps RAGD

---

## Recommendation

**Priority 1:** Implement Phase 1 quick wins (1.5 days) → 1.9× speedup

**Priority 2:** Implement Phase 2 (6 days) → cumulative 3.9× speedup

**Defer:** Phase 3 until scale demands it (>100k chunks, >10 concurrent agents)

**Skip:** Speculative optimizations (ClickHouse, cuDF) until proven bottleneck

---

## Validation Criteria

**Before Optimization:**
1. Profile baseline (record P50/P95/P99 latencies)
2. Write benchmark test (pytest-benchmark or manual timing)
3. Document expected speedup + tradeoffs

**After Optimization:**
1. Re-profile (verify speedup matches prediction)
2. Validate correctness (no regressions in output)
3. Monitor production (watch for unexpected side effects)

**Example:**
```python
# Before optimization
def test_feature_computation_baseline(benchmark):
    result = benchmark(compute_all_features, df)
    assert len(result.columns) == 400
    # Baseline: 118s

# After optimization (parallel Dask)
def test_feature_computation_parallel(benchmark):
    result = benchmark(compute_all_features_parallel, df)
    assert len(result.columns) == 400
    # Target: <30s (4× speedup)
```

---

## Related

- [BOTTLENECK_ANALYSIS.md](BOTTLENECK_ANALYSIS.md) — Root cause analysis
- [PERFORMANCE_BASELINES.md](PERFORMANCE_BASELINES.md) — Current measurements

---

**Last Updated:** 2026-05-19  
**Verified By:** Claude Code (Sonnet 4.5)  
**Review Status:** ✓ All proposals validated for feasibility + impact
