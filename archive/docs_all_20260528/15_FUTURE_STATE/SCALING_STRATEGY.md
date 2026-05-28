---
doc_type: strategy
system: Dominion
ragd_priority: 4
audience:
  - maintainer
  - owner
status: active
last_reviewed: 2026-05-19
tags:
  - future
  - scaling
  - infrastructure
---

# Scaling Strategy

**Purpose:** Technical strategy for scaling Dominion from 12 → 100+ assets.

**Horizon:** Phase 10 (2028) → Phase 14 (2030).

**Status:** Planning. Implementation Phase 11+.

---

## Current State (Phase 10, 2028)

**Capacity:**
- 12 assets (3 metals, 3 energy, 2 currencies, 2 indices, 2 bonds)
- 500 features/asset = 6,000 features/bar
- 17,280 bars/day (12 assets × 1,440 bars)
- Pipeline: 15 minutes (single-threaded, acceptable)

**Infrastructure:**
- Single server (16 core, 64GB RAM)
- DuckDB (columnar, 500MB/month)
- Local deployment

**Bottlenecks:**
- Feature generation: 80% of pipeline time
- DuckDB writes: 15% of pipeline time
- Network I/O (MT5): 5% of pipeline time

---

## Target State (Phase 14, 2030)

**Capacity:**
- 100+ assets (30 futures, 50 equities, 10 FX, 10 crypto)
- 500 features/asset = 50,000 features/bar
- 144,000 bars/day (100 assets × 1,440 bars)
- Pipeline: <15 minutes (8× data in same time)

**Infrastructure:**
- 10-20 servers (distributed)
- DuckDB partitioned + replicated
- Cloud deployment (AWS/GCP)

**Scale Factor:** 8× assets, 8× features, 1× time (8× throughput needed)

---

## Scaling Dimensions

### 1. Data Ingestion (8× throughput)

**Current (12 assets):**
- Serial ingestion (one source at a time)
- MT5: 200 ticks/min/asset = 2,400 ticks/min total
- Bottleneck: None (well below capacity)

**Future (100 assets):**
- Parallel ingestion (100 workers, 1 per asset)
- MT5: 200 ticks/min × 100 = 20,000 ticks/min total
- **Solution:** Ray/Dask for parallel workers

**Implementation:**
```python
import ray

@ray.remote
def ingest_asset(symbol):
    client = MT5Client()
    ticks = client.stream_ticks(symbol, duration='1d')
    pipeline.ingest_ticks(symbol, ticks)

# Spawn 100 workers
futures = [ingest_asset.remote(symbol) for symbol in symbols]
ray.get(futures)  # Wait for all
```

**Expected:** 15 min (serial) → 1 min (parallel, 100 workers)

---

### 2. Feature Generation (8× throughput)

**Current (12 assets):**
- Single-threaded numpy/pandas
- 12 assets × 500 features = 6,000 features/bar
- Time: 12 minutes (80% of pipeline)

**Future (100 assets):**
- 100 assets × 500 features = 50,000 features/bar
- Target: <10 minutes (requires 10× speedup)

**Optimization Strategies:**

**Strategy 1: Vectorization (2× speedup)**
- Replace loops with numpy operations
- Already done (Phase 2)
- Diminishing returns

**Strategy 2: Caching (2× speedup)**
- Cache intermediate features (TTL 60s)
- Redis: 50GB in-memory cache
```python
@cache(ttl=60)
def compute_volatility(symbol, window):
    # Expensive computation cached
    pass
```

**Strategy 3: Parallelization (5× speedup)**
- Ray/Dask: Distribute feature computation across 100 workers
```python
@ray.remote
def compute_features(symbol, bar):
    return feature_pipeline.generate(symbol, bar)

# Parallel compute
futures = [compute_features.remote(s, bar) for s in symbols]
results = ray.get(futures)
```

**Strategy 4: JIT Compilation (1.5× speedup)**
- Numba: Compile hot loops to machine code
```python
from numba import jit

@jit(nopython=True)
def compute_returns(prices):
    return np.diff(prices) / prices[:-1]
```

**Combined:** 2 × 2 × 5 × 1.5 = 30× speedup → 12 min → 0.4 min

**Target:** <10 min (conservative, 2× margin)

---

### 3. Storage (8× data volume)

**Current (12 assets):**
- DuckDB: 500MB/month
- Single-file database
- No partitioning

**Future (100 assets):**
- DuckDB: 4GB/month (8× data)
- Partitioned by date + symbol
- Replicated (master + 2 replicas)

**Partitioning Strategy:**
```sql
CREATE TABLE gold_master (
    timestamp TIMESTAMP,
    symbol VARCHAR,
    source VARCHAR,
    bid DOUBLE,
    ask DOUBLE,
    ...
) PARTITION BY (DATE_TRUNC('day', timestamp), symbol);
```

**Benefits:**
- Queries filtered by date/symbol → scan 1 partition (not all)
- Parallel writes (different partitions)
- Drop old partitions (efficient deletion)

**Replication:**
- Master (writes)
- Replica 1 (reads for dashboard)
- Replica 2 (reads for backtesting)

**Streaming Replication:**
```bash
# Master → Replica (continuous sync)
duckdb_replicate --master master.db --replica replica1.db --lag 5s
```

---

### 4. Computation (10× CPU)

**Current (Phase 10):**
- 16 cores (Intel Xeon)
- CPU-bound (feature generation)

**Future (Phase 14):**
- 100-200 cores (distributed)
- Options:
  1. Single machine (128 cores, AMD EPYC)
  2. 10 machines (16 cores each, Ray cluster)
  3. Cloud (AWS EC2 auto-scaling)

**Recommendation:** Ray cluster (10 machines, 16 cores each)

**Cost:**
- AWS EC2: 10 × c5.4xlarge = $1,700/month
- Local: 10 × refurbished servers = $10K upfront + $200/month power

**Decision:** Cloud (flexibility, no capex)

---

### 5. Memory (8× features)

**Current (Phase 10):**
- 64GB RAM
- Feature matrix: 6,000 features × 1,440 bars × 8 bytes = 70MB (fits in RAM)

**Future (Phase 14):**
- 50,000 features × 1,440 bars × 8 bytes = 576MB (still fits)
- But: 100 workers × 576MB = 57GB (need distributed memory)

**Solution:** Ray object store (shared memory across workers)

```python
# Store feature matrix in Ray object store (shared)
feature_matrix_ref = ray.put(feature_matrix)

# Workers access shared memory (zero-copy)
@ray.remote
def compute_alpha(feature_matrix_ref):
    features = ray.get(feature_matrix_ref)  # Fast, shared memory
    return model.predict(features)
```

**Memory per node:** 64GB (sufficient, 10 nodes = 640GB total)

---

### 6. Network (Data Transfer)

**Current (Phase 10):**
- Local network (no latency)
- MT5 on same machine

**Future (Phase 14):**
- Distributed (10 machines)
- MT5 on separate machine(s)
- Ray cluster: Inter-node communication

**Bandwidth Requirements:**
- 100 assets × 200 ticks/min × 100 bytes/tick = 2MB/min = 30KB/s
- Negligible (1 Gbps LAN = 125MB/s capacity)

**Latency:**
- Intra-rack: <1ms (acceptable)
- Cross-AZ: 5-10ms (acceptable for daily pipeline)

**No bottleneck** (network not limiting factor)

---

## Scaling Phases

### Phase 11: 30 Assets (Q2 2028)

**Changes:**
- Add 18 assets (current 12 → 30)
- Parallel ingestion (Ray, 30 workers)
- Feature caching (Redis, 10GB)

**Infrastructure:**
- 2 machines (1 primary, 1 worker)
- 32 cores each, 128GB RAM each

**Cost:** $500/month (local) or $1,000/month (cloud)

**Validation:** Pipeline <15 min (same as current)

---

### Phase 12: 50 Assets (Q4 2028)

**Changes:**
- Add 20 assets (30 → 50)
- DuckDB partitioning (by date + symbol)
- Distributed Ray cluster (5 nodes)

**Infrastructure:**
- 5 machines (1 master + 4 workers)
- 16 cores each, 64GB RAM each

**Cost:** $1,200/month (local) or $2,000/month (cloud)

**Validation:** Pipeline <15 min

---

### Phase 13: 100 Assets (Q2 2029)

**Changes:**
- Add 50 assets (50 → 100)
- Numba JIT compilation (hot loops)
- DuckDB replication (master + 2 replicas)

**Infrastructure:**
- 10 machines (1 master + 9 workers)
- 16 cores each, 64GB RAM each

**Cost:** $2,500/month (local) or $4,000/month (cloud)

**Validation:** Pipeline <15 min

---

## Cost Analysis

| Phase | Assets | Machines | Cores | RAM | Cost/Month (Cloud) |
|---|---|---|---|---|---|
| Phase 10 (2028) | 12 | 1 | 16 | 64GB | $500 |
| Phase 11 (2028) | 30 | 2 | 64 | 256GB | $1,000 |
| Phase 12 (2028) | 50 | 5 | 80 | 320GB | $2,000 |
| Phase 13 (2029) | 100 | 10 | 160 | 640GB | $4,000 |
| Phase 14 (2030) | 100+ | 10-20 | 200+ | 1TB+ | $5,000-10,000 |

**Break-even:** $4K/month = $48K/year. Need $240K returns (at 20% net) = $1.2M AUM.

**Decision:** Scale only if AUM justifies cost.

---

## Technology Stack

### Current (Phase 10)
- **Compute:** Single machine (Linux)
- **Parallelism:** None (serial)
- **Database:** DuckDB (single-file)
- **Cache:** None
- **Orchestration:** Cron jobs

### Future (Phase 14)
- **Compute:** Ray cluster (10 nodes)
- **Parallelism:** Ray (100 workers)
- **Database:** DuckDB partitioned + replicated
- **Cache:** Redis (50GB in-memory)
- **Orchestration:** Airflow (DAG-based workflow)

---

## Monitoring & Observability

**Metrics (Phase 14):**
- Pipeline latency (target <15 min)
- Feature generation time/asset (target <6s)
- Database write throughput (target >10K rows/s)
- Cache hit rate (target >80%)
- Worker utilization (target >70%)

**Tools:**
- Prometheus (metrics collection)
- Grafana (dashboards)
- AlertManager (alerts)

**Alerts:**
- Pipeline latency >20 min (critical)
- Worker failure (warning)
- Cache hit rate <60% (warning)
- Disk >90% full (critical)

---

## Failure Modes & Resilience

### Failure 1: Worker Crash

**Impact:** 1/100 assets fails ingestion

**Detection:** Ray task timeout (5 min)

**Recovery:** Retry 3×, fallback to Yahoo Finance

**SLA:** <1% data loss

---

### Failure 2: Database Corruption

**Impact:** All data lost

**Detection:** Query failure

**Recovery:** Restore from hourly backup

**SLA:** <1 hour data loss (RPO <1h)

---

### Failure 3: Network Partition

**Impact:** 5/10 nodes unreachable

**Detection:** Ray cluster heartbeat loss

**Recovery:** Failover to available nodes (reduced throughput)

**SLA:** Degraded performance, no data loss

---

## Scaling Alternatives

### Alternative 1: Vertical Scaling (Single Large Machine)

**Pros:**
- Simpler (no distributed complexity)
- Lower latency (no network)

**Cons:**
- Limited (128 cores max)
- Single point of failure
- Expensive (high-end servers $20K+)

**Verdict:** Not viable for 100 assets

---

### Alternative 2: Serverless (AWS Lambda)

**Pros:**
- Auto-scaling
- Pay-per-use

**Cons:**
- Cold start latency (5-10s)
- 15-min timeout (pipeline may exceed)
- State management complex

**Verdict:** Not suitable for stateful pipeline

---

### Alternative 3: Kubernetes (Container Orchestration)

**Pros:**
- Industry standard
- Auto-scaling, load balancing

**Cons:**
- Complex (steep learning curve)
- Overkill for 10 nodes

**Verdict:** Revisit at 50+ nodes (Phase 14+)

---

## Related Documentation

- [[FUTURE_VISION]] — Long-term vision
- [[TECH_DEBT_MAP]] — Known scaling blockers
- [[PHASE_10]] — Production baseline
- [[PERFORMANCE_TUNING]] — Optimization guide (to be created)

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Annually (or when scaling to new phase)

**Next Review:** 2028 Q1 (before Phase 11 scaling)
