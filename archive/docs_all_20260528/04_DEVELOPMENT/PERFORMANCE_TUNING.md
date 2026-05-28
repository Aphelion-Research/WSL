---
doc_type: guide
system: Dominion
ragd_priority: 5
audience:
  - developer
status: active
last_reviewed: 2026-05-19
tags:
  - performance
  - optimization
  - tuning
---

# Performance Tuning Guide

**Purpose:** Proven optimization techniques for Dominion V2.

**Status:** Phase 5 baseline. Phase 10 optimizations planned.

---

## Current Performance (Phase 5)

**Pipeline (12 assets, 1 day):**
- Total: 15 min
- Breakdown:
  - Ingestion: 1 min (7%)
  - Kalman fusion: 2 min (13%)
  - Feature generation: 12 min (80%)
  - RAGD: <1 min (<1%)

**Bottleneck:** Feature generation (80% of time).

---

## Target Performance (Phase 10)

**Pipeline (12 assets, 1 day):**
- Target: <10 min (1.5× speedup)
- Strategy: Optimize feature generation (numba, caching)

**Pipeline (100 assets, 1 day):** (Phase 13)
- Target: <15 min (parallel, 10× throughput)
- Strategy: Ray parallelization (100 workers)

---

## Optimization Techniques

### 1. Vectorization (Applied Phase 2)

**Before (Phase 1, loops):**
```python
returns = []
for i in range(1, len(prices)):
    ret = (prices[i] - prices[i-1]) / prices[i-1]
    returns.append(ret)
# Time: 5s
```

**After (Phase 2, numpy):**
```python
returns = np.diff(prices) / prices[:-1]
# Time: 0.05s (100× faster)
```

**Status:** Complete. All features vectorized.

---

### 2. Database Indexing (Planned Phase 9)

**Current (no index):**
```sql
SELECT * FROM features WHERE symbol='GC=F' AND timestamp > '2026-01-01';
-- Seq scan: 500ms
```

**Optimized (indexed):**
```sql
CREATE INDEX idx_symbol_timestamp ON features(symbol, timestamp);
SELECT * FROM features WHERE symbol='GC=F' AND timestamp > '2026-01-01';
-- Index scan: 20ms (25× faster)
```

**Status:** Planned Phase 9.

---

### 3. Feature Caching (Planned Phase 11)

**Problem:** Returns computed 10× (used in 10 features).

**Solution (Redis cache):**
```python
import redis
cache = redis.Redis()

def compute_returns(symbol, timestamp):
    key = f"returns:{symbol}:{timestamp}"
    cached = cache.get(key)
    if cached:
        return pickle.loads(cached)
    
    # Compute
    returns = np.diff(prices) / prices[:-1]
    
    # Cache (TTL 60s)
    cache.setex(key, 60, pickle.dumps(returns))
    return returns
```

**Expected:** 30% speedup (avoid recomputation).

**Status:** Planned Phase 11.

---

### 4. Numba JIT Compilation (Planned Phase 10)

**Current:**
```python
def compute_volatility(returns):
    return np.std(returns)
# Time: 10ms
```

**Optimized:**
```python
from numba import jit

@jit(nopython=True)
def compute_volatility(returns):
    return np.std(returns)
# Time: 2ms (5× faster)
```

**Expected:** 2-5× speedup (hot loops).

**Status:** Planned Phase 10 ([[TECH_DEBT_MAP]] #6).

---

### 5. Parallelization (Planned Phase 11)

**Current (serial):**
```python
features = []
for symbol in symbols:
    features.append(compute_features(symbol))
# Time: 12 min (12 assets)
```

**Optimized (Ray):**
```python
import ray

@ray.remote
def compute_features(symbol):
    ...

features = ray.get([compute_features.remote(s) for s in symbols])
# Time: 1 min (12 workers, 12× faster)
```

**Expected:** N× speedup (N assets → N workers).

**Status:** Planned Phase 11 ([[TECH_DEBT_MAP]] #2).

---

### 6. Pandas dtype Optimization (Planned Phase 11)

**Current:**
```python
df['symbol'] = df['symbol'].astype('object')  # 8 bytes/row
# Memory: 100 MB
```

**Optimized:**
```python
df['symbol'] = df['symbol'].astype('category')  # 1 byte/row
# Memory: 50 MB (50% reduction)
```

**Status:** Planned Phase 11 ([[ENHANCEMENT_BACKLOG]] #14).

---

### 7. Lazy Loading (Planned Phase 11)

**Current (eager):**
```python
# Compute all 400 features upfront
features = compute_all_features(data)
# Time: 12 min
```

**Optimized (lazy):**
```python
# Compute only used features (50)
features = compute_selected_features(data, selected=['ofi_1m', 'returns_15m', ...])
# Time: 2 min (6× faster)
```

**Status:** Planned Phase 11 ([[ENHANCEMENT_BACKLOG]] #15).

---

## Benchmarking

**Tool:** pytest-benchmark

**Usage:**
```python
def test_compute_returns_benchmark(benchmark):
    prices = np.random.random(1000)
    result = benchmark(compute_returns, prices)
    assert len(result) == 999
```

```bash
pytest tests/benchmarks/ --benchmark-only
```

**Output:**
```
Name                      Min      Max     Mean   Median
compute_returns         0.05ms   0.10ms  0.06ms   0.06ms
compute_volatility      2.00ms   5.00ms  2.50ms   2.30ms
```

**Track over time:** Detect regressions.

---

## Performance Regression Testing

**CI Job (Phase 10):**
```yaml
name: Performance Tests
on: [push]
jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - run: pytest tests/benchmarks/ --benchmark-only
      - run: |
          # Fail if >10% slower than baseline
          python scripts/compare_benchmarks.py baseline.json current.json --threshold 1.1
```

---

## Tuning Parameters

**DuckDB:**
```sql
-- Increase threads (use all cores)
SET threads=16;

-- Increase memory limit
SET memory_limit='8GB';
```

**Kalman Filter:**
```python
# Process noise tuning (Phase 2)
Q = [[0.05**2, 0],
     [0, 0.01**2]]
# Lower Q = smoother (but slower adaptation)
# Higher Q = noisier (but faster adaptation)
# Current: Tuned empirically (0.05, 0.01)
```

**HMM:**
```python
# Convergence threshold (Phase 4)
hmm.fit(data, n_iter=50, tol=0.01)
# Lower tol = more iterations (slower, more accurate)
# Higher tol = fewer iterations (faster, less accurate)
# Current: 0.01 (balance)
```

---

## Performance Monitoring

**Metrics (Phase 10):**
- Pipeline latency (target <10 min)
- Feature generation time/asset (target <1 min)
- Database query latency (target <100ms)
- Memory usage (target <16GB)

**Dashboards (Grafana, Phase 10):**
- Pipeline latency (time series)
- Bottleneck breakdown (pie chart)
- Resource usage (CPU, memory, disk)

---

## Scaling Targets

| Phase | Assets | Pipeline Time | Optimization |
|---|---|---|---|
| Phase 5 (current) | 12 | 15 min | Baseline |
| Phase 10 (2028) | 12 | 10 min | Numba, caching |
| Phase 11 (2028) | 30 | 15 min | Parallelization |
| Phase 13 (2029) | 100 | 15 min | Ray cluster |

**Key:** Maintain <15 min latency as assets scale.

---

## Related Documentation

- [[PROFILING_GUIDE]] — Identify bottlenecks
- [[SCALING_STRATEGY]] — Phase 11+ scaling plan
- [[TECH_DEBT_MAP]] — Performance debt items
- [[ENHANCEMENT_BACKLOG]] — Performance enhancements

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After major optimizations

**Next Review:** Phase 10 (before production launch)
