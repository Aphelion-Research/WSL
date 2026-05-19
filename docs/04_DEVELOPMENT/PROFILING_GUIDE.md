---
doc_type: guide
system: Dominion
ragd_priority: 5
audience:
  - developer
status: active
last_reviewed: 2026-05-19
tags:
  - profiling
  - performance
  - optimization
---

# Profiling Guide

**Purpose:** Identify performance bottlenecks in Dominion V2.

**Principle:** Measure first, optimize second. Don't guess.

---

## When to Profile

1. **Pipeline slow** (>20 min for 12 assets)
2. **Query latency high** (>1s for analytics)
3. **Before scaling** (Phase 11, 100 assets)
4. **After major refactor** (verify no regression)

**Don't profile prematurely.** Working code > fast code.

---

## CPU Profiling

### cProfile (Standard Library)

**Usage:**
```bash
# Profile entire pipeline
python -m cProfile -o profile.stats -m data_pipeline.cli run

# Analyze
python -m pstats profile.stats
> sort cumtime  # Sort by cumulative time
> stats 20  # Show top 20 functions
```

**Output:**
```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      100    2.500    0.025   15.000    0.150 features/pipeline.py:45(compute_features)
     1200    5.000    0.004    5.000    0.004 features/price.py:12(compute_returns)
       50    3.000    0.060    3.000    0.060 kalman/filter.py:67(update)
```

**Interpretation:**
- `compute_features`: 15s total (bottleneck)
- `compute_returns`: 5s (called 1200×, 4ms each)
- `kalman.update`: 3s (50 calls, 60ms each)

**Action:** Optimize `compute_features` (biggest impact).

---

### py-spy (Sampling Profiler)

**Install:**
```bash
pip install py-spy
```

**Usage (running process):**
```bash
# Find PID
ps aux | grep python

# Profile (30s sampling)
sudo py-spy record -o profile.svg --pid 12345 --duration 30

# View (open SVG in browser)
firefox profile.svg
```

**Advantage:** Profile production (no code changes).

---

### line_profiler (Line-by-Line)

**Install:**
```bash
pip install line_profiler
```

**Usage:**
```python
# Add @profile decorator
@profile
def compute_features(data):
    returns = compute_returns(data)  # Line 1
    vol = compute_volatility(data)    # Line 2
    ...
```

```bash
# Profile
kernprof -l -v pipeline.py
```

**Output:**
```
Line      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
  45         1      500.0    500.0     10.0      returns = compute_returns(data)
  46         1     2000.0   2000.0     40.0      vol = compute_volatility(data)
  47         1     2500.0   2500.0     50.0      ofi = compute_ofi(data)
```

**Insight:** `compute_ofi` is bottleneck (50% of time).

---

## Memory Profiling

### memory_profiler

**Install:**
```bash
pip install memory_profiler
```

**Usage:**
```python
from memory_profiler import profile

@profile
def load_features():
    df = pd.read_csv('features.csv')  # Line 1
    df2 = df.copy()                   # Line 2
    return df2
```

```bash
python -m memory_profiler pipeline.py
```

**Output:**
```
Line    Mem usage    Increment   Line Contents
================================================
   1      50 MB         0 MB    df = pd.read_csv('features.csv')
   2     100 MB        50 MB    df2 = df.copy()  # Duplicate!
```

**Insight:** `df.copy()` doubles memory (remove if unnecessary).

---

### tracemalloc (Standard Library)

**Usage:**
```python
import tracemalloc

tracemalloc.start()

# Code to profile
df = pd.read_csv('features.csv')

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

for stat in top_stats[:10]:
    print(stat)
```

**Output:**
```
features.csv:45: size=50.0 MB, count=1, average=50.0 MB
pipeline.py:67: size=25.0 MB, count=10, average=2.5 MB
```

---

## I/O Profiling

### Disk I/O (iostat)

**Usage:**
```bash
# Monitor disk usage (5s intervals)
iostat -x 5
```

**Output:**
```
Device    r/s     w/s   rkB/s   wkB/s  await
sda      50.0    20.0  1000.0   500.0   15.0
```

**Interpretation:**
- `r/s`: 50 reads/sec
- `await`: 15ms avg latency (acceptable)

**Bottleneck:** `await` >50ms = disk slow.

---

### Database Query Profiling (DuckDB)

**Usage:**
```sql
EXPLAIN ANALYZE SELECT * FROM features WHERE symbol='GC=F';
```

**Output:**
```
SEQ_SCAN (cost=0..1000, rows=43200)
  Filter: symbol='GC=F'
  Actual time: 500ms
```

**Insight:** Sequential scan (no index). Add index:
```sql
CREATE INDEX idx_symbol ON features(symbol);
```

**After:**
```
INDEX_SCAN (cost=0..50, rows=43200)
  Actual time: 20ms  (25× faster)
```

---

## Optimization Strategies

### 1. Vectorization (Numpy/Pandas)

**Before (slow, loops):**
```python
returns = []
for i in range(1, len(prices)):
    ret = (prices[i] - prices[i-1]) / prices[i-1]
    returns.append(ret)
```

**After (fast, vectorized):**
```python
returns = np.diff(prices) / prices[:-1]
```

**Speedup:** 10-100× (numpy C backend).

---

### 2. Caching (Redis/Memoization)

**Before:**
```python
def compute_volatility(symbol):
    # Recompute every time
    prices = load_prices(symbol)
    return np.std(prices)
```

**After:**
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def compute_volatility(symbol):
    prices = load_prices(symbol)
    return np.std(prices)
```

**Speedup:** Infinite (cache hits).

---

### 3. Parallelization (Ray/Dask)

**Before (serial):**
```python
features = []
for symbol in symbols:
    features.append(compute_features(symbol))
```

**After (parallel):**
```python
import ray

@ray.remote
def compute_features(symbol):
    ...

features = ray.get([compute_features.remote(s) for s in symbols])
```

**Speedup:** N× (N cores).

---

### 4. JIT Compilation (Numba)

**Before:**
```python
def compute_returns(prices):
    return np.diff(prices) / prices[:-1]
```

**After:**
```python
from numba import jit

@jit(nopython=True)
def compute_returns(prices):
    return np.diff(prices) / prices[:-1]
```

**Speedup:** 2-5× (compiled to machine code).

---

### 5. Database Indexing

**Before:**
```sql
SELECT * FROM features WHERE symbol='GC=F' AND timestamp > '2026-01-01';
-- Seq scan: 500ms
```

**After:**
```sql
CREATE INDEX idx_symbol_timestamp ON features(symbol, timestamp);
-- Index scan: 20ms
```

**Speedup:** 25×.

---

## Profiling Checklist

**Before optimization:**
- [ ] Profile (cProfile, py-spy)
- [ ] Identify bottleneck (top 3 functions by time)
- [ ] Measure baseline (e.g., 15 min pipeline)

**After optimization:**
- [ ] Re-profile (verify improvement)
- [ ] Measure speedup (e.g., 15 min → 5 min, 3× faster)
- [ ] Test correctness (ensure same results)
- [ ] Commit with benchmark (document speedup)

---

## Performance Targets

| Component | Target | Current (Phase 5) | Status |
|---|---|---|---|
| Pipeline (12 assets) | <15 min | 15 min | ✓ |
| Feature generation | <10 min | 12 min | ⚠ (optimize Phase 10) |
| RAGD query | <100 ms | 50 ms | ✓ |
| Kalman update | <5 ms | 1.2 ms | ✓ |
| HMM training | <120 s | 100 s | ✓ |

---

## Related Documentation

- [[TECH_DEBT_MAP]] — Known performance debt
- [[SCALING_STRATEGY]] — Phase 11 optimization plan
- [[DEBUGGING_GUIDE]] — Debug slow code
- [[ENHANCEMENT_BACKLOG]] — Performance enhancements

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After major optimizations

**How to Add:**
1. Profile bottleneck
2. Optimize
3. Measure speedup
4. Document technique here
