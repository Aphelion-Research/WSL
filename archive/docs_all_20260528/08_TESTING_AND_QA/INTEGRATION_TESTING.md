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
  - testing
  - integration
  - quality
---

# Integration Testing Guide

**Purpose:** Deep-dive on integration testing for Dominion V2.

**Status:** 25/25 integration tests passing (Phase 5).

---

## What is Integration Testing?

**Definition:** Test interactions between multiple components with real dependencies (databases, files, APIs).

**Contrast with Unit Tests:**
- Unit: Isolated, mocked dependencies, fast (<1ms)
- Integration: Real dependencies, component boundaries, slower (10-100ms)

**Contrast with E2E Tests:**
- Integration: 2-3 components, programmatic
- E2E: Full system, user workflows, slowest (1-10s)

---

## Integration Test Categories

### 1. Data Flow Integration (6 tests)

**Purpose:** Verify data flows correctly between components.

**Pattern:**
```
Source → Ingestion → Storage → Retrieval → Validation
```

**Example: CSV → DuckDB**
```python
def test_csv_to_duckdb_integration(tmp_path):
    # Setup: Create test CSV
    csv_path = tmp_path / "test_ticks.csv"
    df = pd.DataFrame({
        'timestamp': pd.date_range('2026-01-01', periods=100, freq='1min'),
        'symbol': ['GC=F'] * 100,
        'bid': np.random.uniform(2340, 2350, 100),
        'ask': np.random.uniform(2340, 2350, 100),
    })
    df.to_csv(csv_path, index=False)
    
    # Action: Ingest via pipeline
    db_path = tmp_path / "test.db"
    pipeline = Pipeline(db_path)
    pipeline.ingest_csv(str(csv_path))
    
    # Verify: Data in database
    con = duckdb.connect(str(db_path))
    result = con.execute("SELECT COUNT(*) FROM gold_master").fetchone()
    assert result[0] == 100
    
    # Verify: Data integrity
    stored_df = con.execute("SELECT * FROM gold_master ORDER BY timestamp").df()
    assert stored_df['symbol'].iloc[0] == 'GC=F'
    assert len(stored_df) == 100
```

**Tests:**
1. CSV → DuckDB (yahoo ingestion)
2. MT5 CSV → DuckDB (domdata)
3. FRED API → DuckDB (macro data)
4. DuckDB → Features table (feature generation)
5. Features → RAGD (intelligence reports)
6. RAGD → Query results (retrieval)

---

### 2. Multi-Component Workflows (5 tests)

**Purpose:** Test complete workflows spanning 3+ components.

**Example: Kalman Fusion Pipeline**
```python
def test_kalman_fusion_integration():
    # Setup: Multiple sources
    sources = {
        'yahoo': [2345.60, 2345.65, 2345.70],
        'mt5': [2345.61, 2345.66, 2345.71],
        'av': [2345.59, 2345.64, 2345.69],
    }
    
    # Component 1: Trust Scorer (assigns weights)
    trust_scorer = TrustScorer()
    for source in sources:
        trust_scorer.initialize(source, trust=0.9)
    
    # Component 2: Kalman Filter Bank (6 timescales)
    kalman_bank = KalmanFilterBank(timescales=['1m', '5m', '1h'])
    
    # Component 3: Fusion Engine
    fusion = FusionEngine(trust_scorer, kalman_bank)
    
    # Action: Fuse observations
    for i in range(3):
        observations = {src: prices[i] for src, prices in sources.items()}
        fused_price = fusion.fuse(observations, timestamp=f"2026-01-01 09:3{i}:00")
    
    # Verify: Fused price is weighted average (biased toward high-trust)
    assert 2345.59 < fused_price < 2345.71
    
    # Verify: Kalman state updated
    state = kalman_bank.get_state('1m')
    assert state is not None
```

**Tests:**
1. Multi-source fusion (Yahoo + MT5 + AV)
2. Feature generation pipeline (ticks → 400 features)
3. LOB → Toxicity (order flow → adverse selection)
4. Exec Sim → TCA (orders → cost attribution)
5. HMM → Intelligence Reports → RAGD (regime → markdown → index)

---

### 3. State Persistence (4 tests)

**Purpose:** Verify state persists across restarts.

**Example: Kalman Filter State**
```python
def test_kalman_state_persistence(tmp_path):
    state_path = tmp_path / "kalman_state.pkl"
    
    # Phase 1: Create filter, update, save
    kf = KalmanFilter(initial_state=100)
    kf.update(102)
    kf.update(101)
    kf.save(state_path)
    
    # Phase 2: Load filter, verify state
    kf2 = KalmanFilter.load(state_path)
    assert kf2.state == kf.state
    assert np.allclose(kf2.covariance, kf.covariance)
    
    # Phase 3: Continue updating
    kf2.update(103)
    prediction = kf2.predict()
    assert 101 < prediction < 104
```

**Tests:**
1. Kalman filter state (pickle)
2. HMM model state (pickle)
3. Trust scores (JSON)
4. Agent session (JSON)

---

### 4. Error Propagation (6 tests)

**Purpose:** Verify errors handled gracefully across components.

**Example: Source Failure Fallback**
```python
def test_source_failure_graceful_degradation():
    # Setup: 3 sources, 1 will fail
    trust_scorer = TrustScorer()
    trust_scorer.initialize('yahoo', trust=0.9)
    trust_scorer.initialize('mt5', trust=0.9)
    trust_scorer.initialize('av', trust=0.9)
    
    fusion = FusionEngine(trust_scorer)
    
    # Observation 1: All sources OK
    obs1 = {'yahoo': 2345.60, 'mt5': 2345.61, 'av': 2345.59}
    fused1 = fusion.fuse(obs1)
    assert fused1 is not None
    
    # Observation 2: MT5 fails (None)
    obs2 = {'yahoo': 2345.65, 'mt5': None, 'av': 2345.64}
    fused2 = fusion.fuse(obs2)
    assert fused2 is not None  # Should still fuse (2 sources OK)
    
    # Observation 3: MT5 + AV fail (only Yahoo)
    obs3 = {'yahoo': 2345.70, 'mt5': None, 'av': None}
    fused3 = fusion.fuse(obs3)
    assert fused3 == 2345.70  # Fallback to single source
    
    # Verify: Trust scores updated (MT5, AV downweighted)
    assert trust_scorer.get_trust('mt5') < 0.9
    assert trust_scorer.get_trust('av') < 0.9
    assert trust_scorer.get_trust('yahoo') >= 0.9
```

**Tests:**
1. Source failure (fusion with missing sources)
2. Database lock (retry logic)
3. RAGD index corruption (rebuild)
4. Feature computation error (skip bar, log error)
5. HMM convergence failure (fallback to last state)
6. MT5 connection loss (retry 10×, fallback Yahoo)

---

### 5. Concurrent Access (4 tests)

**Purpose:** Test thread safety and race conditions.

**Example: Concurrent Feature Generation**
```python
def test_concurrent_feature_generation():
    feature_pipeline = FeaturePipeline()
    symbols = ['GC=F', 'SI=F', 'HG=F']
    
    # Spawn 3 threads (one per symbol)
    results = {}
    def compute(symbol):
        results[symbol] = feature_pipeline.generate(symbol, date='2026-01-01')
    
    threads = [threading.Thread(target=compute, args=(s,)) for s in symbols]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Verify: All completed without corruption
    assert len(results) == 3
    for symbol in symbols:
        assert symbol in results
        assert len(results[symbol].columns) >= 400
```

**Tests:**
1. Concurrent feature generation (3 symbols, parallel)
2. Concurrent DuckDB writes (transaction isolation)
3. Concurrent trust score updates (lock contention)
4. Concurrent agent sessions (session state isolation)

---

## Test Organization

**Directory:**
```
tests/integration/
├── test_pipeline_integration.py       (6 tests: data flow)
├── test_features_integration.py       (5 tests: multi-component)
├── test_kalman_integration.py         (4 tests: state persistence)
├── test_microstructure_integration.py (6 tests: error propagation)
└── test_regime_integration.py         (4 tests: concurrent access)
```

---

## Writing Integration Tests

### Pattern 1: Temporary Filesystem

**Use `tmp_path` fixture (pytest):**
```python
def test_feature(tmp_path):
    # tmp_path is unique per test, auto-cleaned
    db_path = tmp_path / "test.db"
    csv_path = tmp_path / "data.csv"
    
    # Test code...
    
    # No manual cleanup needed
```

### Pattern 2: Test Fixtures

**Reusable setup via conftest.py:**
```python
# tests/integration/conftest.py

@pytest.fixture
def sample_db(tmp_path):
    """Database with 1000 sample ticks"""
    db_path = tmp_path / "sample.db"
    con = duckdb.connect(str(db_path))
    con.execute("""
        CREATE TABLE gold_master (
            timestamp TIMESTAMP,
            symbol VARCHAR,
            bid DOUBLE,
            ask DOUBLE
        )
    """)
    # Insert 1000 rows...
    return db_path

def test_feature_with_db(sample_db):
    # Use pre-populated database
    con = duckdb.connect(str(sample_db))
    count = con.execute("SELECT COUNT(*) FROM gold_master").fetchone()[0]
    assert count == 1000
```

### Pattern 3: Transaction Rollback

**For database tests:**
```python
@pytest.fixture
def db_transaction(sample_db):
    con = duckdb.connect(str(sample_db))
    con.begin()
    yield con
    con.rollback()  # Undo changes after test

def test_with_rollback(db_transaction):
    db_transaction.execute("INSERT INTO gold_master VALUES (...)")
    # Changes rolled back after test
```

### Pattern 4: Mocking External APIs

**Mock HTTP but use real components:**
```python
@patch('requests.get')
def test_fred_integration(mock_get, tmp_path):
    # Mock FRED API response
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {'observations': [{'value': '3.5'}]}
    )
    
    # Real pipeline ingestion (DuckDB, trust scoring)
    db_path = tmp_path / "test.db"
    pipeline = Pipeline(db_path)
    pipeline.ingest_fred('GDP')
    
    # Verify stored
    con = duckdb.connect(str(db_path))
    result = con.execute("SELECT COUNT(*) FROM fred_data").fetchone()
    assert result[0] > 0
```

---

## Performance Considerations

**Integration tests slower than unit:**
- Unit: <1ms (in-memory, mocked)
- Integration: 10-100ms (real I/O)
- E2E: 1-10s (full workflows)

**Keep integration tests fast:**
1. Use temporary databases (avoid network)
2. Small datasets (1000 rows, not 1M)
3. Mock slow external APIs (HTTP, cloud)
4. Parallelize where possible (pytest-xdist)

**Parallelization:**
```bash
# Run tests in parallel (4 workers)
pytest tests/integration/ -n 4
```

---

## Common Pitfalls

### 1. Flaky Tests (Non-Deterministic)

**Problem:** Test passes/fails randomly.

**Causes:**
- Race conditions (threading)
- Timing assumptions (sleep)
- External state (shared databases)

**Solution:**
```python
# Bad: Assumes order
def test_flaky():
    threads = [Thread(target=func) for _ in range(10)]
    for t in threads:
        t.start()
    time.sleep(0.1)  # Assumes threads finish in 100ms
    assert result == expected  # May fail if threads slow

# Good: Wait for completion
def test_stable():
    threads = [Thread(target=func) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()  # Wait for all threads
    assert result == expected
```

### 2. Shared State Contamination

**Problem:** Tests affect each other.

**Causes:**
- Shared databases
- Global variables
- Cached state

**Solution:**
```python
# Bad: Shared database
DB_PATH = "shared.db"

def test_a():
    con = duckdb.connect(DB_PATH)
    con.execute("INSERT INTO table VALUES (1)")

def test_b():
    con = duckdb.connect(DB_PATH)
    count = con.execute("SELECT COUNT(*) FROM table").fetchone()[0]
    assert count == 0  # Fails if test_a ran first!

# Good: Isolated databases
def test_a(tmp_path):
    db = tmp_path / "a.db"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE table (id INT)")
    con.execute("INSERT INTO table VALUES (1)")

def test_b(tmp_path):
    db = tmp_path / "b.db"
    con = duckdb.connect(str(db))
    con.execute("CREATE TABLE table (id INT)")
    count = con.execute("SELECT COUNT(*) FROM table").fetchone()[0]
    assert count == 0  # Always passes
```

### 3. Test Data Realism

**Problem:** Synthetic data doesn't match production.

**Example:**
```python
# Bad: Perfect data (never happens in production)
def test_with_perfect_data():
    prices = [100.0, 101.0, 102.0, 103.0]  # Monotonic, no gaps
    features = compute_features(prices)
    assert features is not None

# Good: Realistic data (volatility, gaps, NaN)
def test_with_realistic_data():
    prices = [100.0, 101.5, 100.8, np.nan, 102.3, 101.1]  # Real-world messiness
    features = compute_features(prices)
    assert features is not None
    assert not np.any(np.isnan(features))  # Verify NaN handling
```

---

## Integration Test Checklist

**Before merging:**
- [ ] All integration tests pass
- [ ] No flaky tests (run 10× locally)
- [ ] Test isolation verified (can run in any order)
- [ ] Temporary files cleaned up (pytest handles tmp_path)
- [ ] Performance acceptable (<100ms per test)
- [ ] Error cases tested (not just happy path)

---

## CI Configuration

**GitHub Actions:**
```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run integration tests
        run: pytest tests/integration/ -v --tb=short
      
      - name: Check for flaky tests
        run: pytest tests/integration/ --count=3  # Run 3× to catch flakes
```

---

## Future Enhancements

### Phase 7: Paper Trading
- Integration: Real-time tick → features → signal (5 tests)
- Integration: Paper executor → P&L tracking (3 tests)

### Phase 8: Risk Management
- Integration: VaR computation → circuit breakers (4 tests)
- Integration: Pre-trade checks → order rejection (3 tests)

### Phase 9: Multi-Asset
- Integration: 12-asset pipeline (parallel ingestion, 6 tests)
- Integration: Cross-asset correlation → portfolio opt (4 tests)

### Phase 10: Production
- Integration: HA failover (primary → standby, 3 tests)
- Integration: Disaster recovery (backup → restore, 2 tests)

**Target (Phase 10): 60 integration tests (vs 25 current)**

---

## Related Documentation

- [[TEST_PYRAMID]] — Test strategy overview
- [[COVERAGE_STRATEGY]] — Coverage targets
- [[TESTING_STRATEGY]] — Overall QA approach
- [[QA_CHECKLIST]] — Pre-release checklist

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After each phase

**How to Contribute:**
1. Write integration tests following patterns above
2. Use `tmp_path` for isolation
3. Keep tests fast (<100ms)
4. Test error paths (not just happy path)
5. Run 10× locally to check for flakes
6. Update this doc if adding new patterns
