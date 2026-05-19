---
doc_type: strategy
system: Dominion
ragd_priority: 7
audience:
  - developer
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - testing
  - quality
  - strategy
---

# Test Pyramid Strategy

**Purpose:** Testing strategy for Dominion V2 following the test pyramid model.

**Status:** Active (Phase 5). 94/94 tests passing (100%).

---

## Test Pyramid Model

```
           /\
          /  \
         / E2E\          5-10% (10 tests)   — End-to-end
        /------\
       /        \
      /Integration\     20-30% (25 tests)  — Integration
     /------------\
    /              \
   /   Unit Tests   \   60-70% (59 tests)  — Unit
  /------------------\
```

**Distribution (Current):**
- Unit: 59 tests (63%)
- Integration: 25 tests (27%)
- End-to-end: 10 tests (10%)
- **Total: 94 tests**

**Target (Phase 10):**
- Unit: 120 tests (60%)
- Integration: 60 tests (30%)
- End-to-end: 20 tests (10%)
- **Total: 200 tests**

---

## 1. Unit Tests (60-70%)

**Purpose:**
Test individual functions, classes, methods in isolation.

**Characteristics:**
- Fast (<1ms per test)
- No external dependencies (mocks/stubs)
- High coverage (>90% line coverage target)
- Run on every commit

**Examples:**

**1.1 Feature Calculation**
```python
def test_compute_returns():
    prices = np.array([100, 102, 101, 103])
    returns = compute_returns(prices)
    expected = np.array([0.02, -0.0098, 0.0198])
    np.testing.assert_array_almost_equal(returns, expected, decimal=4)
```

**1.2 Kalman Filter Update**
```python
def test_kalman_update():
    kf = KalmanFilter(initial_state=100, initial_variance=1.0)
    updated_state = kf.update(observation=102, measurement_noise=0.5)
    assert 100 < updated_state < 102  # Updated toward observation
```

**1.3 Trust Score Computation**
```python
def test_trust_score():
    scorer = TrustScorer()
    scorer.add_error('yahoo', 0.5)
    scorer.add_error('yahoo', 0.3)
    trust = scorer.get_trust('yahoo')
    assert 0.7 < trust < 0.9  # High trust (low error)
```

**Current Unit Tests (59):**
- Data Pipeline: 16 tests (ingestion, fusion, trust)
- Features: 12 tests (returns, vol, OFI, VPIN)
- Kalman Filter: 8 tests (predict, update, covariance)
- Microstructure: 14 tests (LOB, spreads, toxicity)
- Regime Detection: 6 tests (HMM states, transitions)
- Agent OS: 3 tests (session, handoff)

**Coverage:**
- Target: >90% line coverage
- Current: ~85% (Phase 5)
- Gaps: Error handling, edge cases

---

## 2. Integration Tests (20-30%)

**Purpose:**
Test interactions between components, with real dependencies.

**Characteristics:**
- Slower (10-100ms per test)
- Real databases, file I/O
- Test component interfaces
- Run on pre-commit

**Examples:**

**2.1 Data Pipeline Integration**
```python
def test_pipeline_end_to_end(tmp_path):
    # Real DuckDB, real CSV
    db_path = tmp_path / "test.db"
    pipeline = Pipeline(db_path)
    
    # Ingest sample data
    pipeline.ingest_csv("test_data/sample_ticks.csv")
    
    # Verify stored
    con = duckdb.connect(str(db_path))
    count = con.execute("SELECT COUNT(*) FROM gold_master").fetchone()[0]
    assert count == 1000
```

**2.2 Feature Generation Pipeline**
```python
def test_feature_generation_integration():
    # Real data → real features
    pipeline = FeaturePipeline()
    features = pipeline.generate(symbol="GC=F", date="2026-01-01")
    
    # Verify 400+ features computed
    assert len(features.columns) >= 400
    assert 'returns_1m' in features.columns
    assert 'ofi_1m' in features.columns
```

**2.3 LOB → Toxicity Integration**
```python
def test_lob_toxicity_integration():
    lob = LOBEngine()
    toxicity = ToxicityMonitor()
    
    # Feed ticks → LOB → toxicity
    for tick in load_sample_ticks():
        lob.process_tick(tick)
        ofi = lob.get_ofi(window='1m')
        vpin = lob.get_vpin()
        score = toxicity.compute_score(ofi, vpin)
    
    # Verify toxicity computed
    assert 0 <= score <= 1
```

**Current Integration Tests (25):**
- Pipeline (CSV → DuckDB): 6 tests
- Feature generation: 5 tests
- Kalman fusion (multi-source): 4 tests
- Microstructure (LOB → Exec Sim → TCA): 6 tests
- Regime → Intelligence reports → RAGD: 4 tests

**Coverage:**
- Target: All inter-component boundaries
- Current: ~70% of boundaries
- Gaps: Error propagation, concurrent access

---

## 3. End-to-End Tests (5-10%)

**Purpose:**
Test complete workflows from user perspective.

**Characteristics:**
- Slowest (1-10s per test)
- Full system (all components)
- User-facing workflows
- Run on pre-push / CI

**Examples:**

**3.1 Daily Pipeline Run**
```python
def test_daily_pipeline_run_e2e():
    # Simulate: Ingest → Fuse → Features → RAGD
    result = subprocess.run([
        'python', '-m', 'data_pipeline.cli', 'run',
        '--date', '2026-01-01'
    ], capture_output=True)
    
    # Verify success
    assert result.returncode == 0
    assert "Pipeline complete" in result.stdout.decode()
    
    # Verify outputs
    assert Path("data/dominion.db").exists()
    assert Path("ragd/index.db").exists()
```

**3.2 Alpha Signal Generation**
```python
def test_alpha_signal_generation_e2e():
    # Load model → load data → generate signal
    model = load_alpha_model("models/ensemble_v1.pkl")
    features = load_features(symbol="GC=F", timestamp="2026-01-01 09:30:00")
    signal = model.predict(features)
    
    # Verify signal in valid range
    assert -1 <= signal <= 1
```

**3.3 RAGD Query Workflow**
```python
def test_ragd_query_e2e():
    # Query RAGD API
    response = requests.post("http://127.0.0.1:7474/query", json={
        "query": "How does Kalman fusion work?",
        "top_k": 5
    })
    
    # Verify results
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 5
    assert any("kalman" in r['text'].lower() for r in results)
```

**Current End-to-End Tests (10):**
- Daily pipeline run: 2 tests
- Feature generation (full 400+): 2 tests
- Regime detection (90-day train): 2 tests
- RAGD rebuild + query: 2 tests
- Intelligence report generation: 2 tests

**Coverage:**
- Target: All user-facing workflows
- Current: ~60% of workflows
- Gaps: Multi-day runs, error recovery, failover

---

## Test Organization

**Directory Structure:**
```
tests/
├── unit/
│   ├── test_data_pipeline.py      (16 tests)
│   ├── test_features.py            (12 tests)
│   ├── test_kalman.py              (8 tests)
│   ├── test_microstructure.py      (14 tests)
│   ├── test_regime.py              (6 tests)
│   └── test_agent.py               (3 tests)
├── integration/
│   ├── test_pipeline_integration.py  (6 tests)
│   ├── test_features_integration.py  (5 tests)
│   ├── test_kalman_integration.py    (4 tests)
│   ├── test_microstructure_integration.py (6 tests)
│   └── test_regime_integration.py    (4 tests)
├── e2e/
│   ├── test_pipeline_e2e.py        (2 tests)
│   ├── test_features_e2e.py        (2 tests)
│   ├── test_regime_e2e.py          (2 tests)
│   ├── test_ragd_e2e.py            (2 tests)
│   └── test_reports_e2e.py         (2 tests)
├── fixtures/
│   ├── sample_ticks.csv            (1000 rows)
│   ├── sample_features.csv         (100 rows)
│   └── mock_ragd_index.db
└── conftest.py                     (pytest fixtures)
```

---

## Test Execution

**Local Development:**
```bash
# Run all unit tests (fast, <1s)
pytest tests/unit/ -v

# Run all integration tests (slower, ~10s)
pytest tests/integration/ -v

# Run all e2e tests (slowest, ~60s)
pytest tests/e2e/ -v

# Run all tests
pytest tests/ -v
```

**Pre-Commit Hook:**
```bash
# .git/hooks/pre-commit
#!/bin/bash
pytest tests/unit/ --tb=short
if [ $? -ne 0 ]; then
    echo "Unit tests failed. Fix before committing."
    exit 1
fi
```

**CI Pipeline (GitHub Actions):**
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src --cov-report=xml
      - name: Run integration tests
        run: pytest tests/integration/ -v
      - name: Run e2e tests
        run: pytest tests/e2e/ -v
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## Coverage Strategy

**Target Coverage:**
- Overall: >85% line coverage
- Critical paths: >95% (data pipeline, risk checks)
- Utilities: >70% (logging, formatting)

**Current Coverage (Phase 5):**
- Overall: ~85%
- Data Pipeline: 92%
- Microstructure: 88%
- Regime Detection: 80%
- Agent OS: 65% (low priority, agent-facing)

**Coverage Gaps:**
- Error handling branches (hard to trigger)
- Edge cases (extreme market conditions)
- Concurrent access (threading, race conditions)

**How to Improve:**
```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View report (open htmlcov/index.html)
# Identify uncovered lines
# Add tests for high-value paths
```

---

## Testing Best Practices

**1. Arrange-Act-Assert (AAA) Pattern**
```python
def test_feature():
    # Arrange: Set up test data
    prices = [100, 102, 101]
    
    # Act: Execute function
    returns = compute_returns(prices)
    
    # Assert: Verify result
    assert len(returns) == 2
```

**2. One Assert Per Test (Prefer)**
```python
# Good: Focused, clear failure message
def test_returns_length():
    returns = compute_returns([100, 102, 101])
    assert len(returns) == 2

def test_returns_values():
    returns = compute_returns([100, 102, 101])
    assert abs(returns[0] - 0.02) < 1e-6

# Avoid: Multiple asserts (hard to debug)
def test_returns():
    returns = compute_returns([100, 102, 101])
    assert len(returns) == 2
    assert abs(returns[0] - 0.02) < 1e-6
    assert abs(returns[1] + 0.0098) < 1e-6
```

**3. Use Fixtures for Setup**
```python
@pytest.fixture
def sample_ticks():
    return pd.read_csv("tests/fixtures/sample_ticks.csv")

def test_lob(sample_ticks):
    lob = LOBEngine()
    lob.process_ticks(sample_ticks)
    assert lob.get_depth() > 0
```

**4. Parametrize for Multiple Cases**
```python
@pytest.mark.parametrize("prices,expected", [
    ([100, 102], [0.02]),
    ([100, 102, 101], [0.02, -0.0098]),
    ([100], []),
])
def test_returns(prices, expected):
    returns = compute_returns(prices)
    np.testing.assert_array_almost_equal(returns, expected, decimal=4)
```

**5. Mock External Dependencies**
```python
from unittest.mock import patch, MagicMock

@patch('requests.get')
def test_yahoo_fetch(mock_get):
    # Mock HTTP response
    mock_get.return_value = MagicMock(status_code=200, json=lambda: {...})
    
    # Test function
    data = fetch_yahoo_data("GC=F")
    assert data is not None
```

---

## Anti-Patterns to Avoid

**1. Testing Implementation Details**
```python
# Bad: Tests internal state
def test_kalman_internal():
    kf = KalmanFilter()
    kf.update(100)
    assert kf._state == 100  # Internal detail

# Good: Tests observable behavior
def test_kalman_prediction():
    kf = KalmanFilter()
    kf.update(100)
    prediction = kf.predict()
    assert 95 < prediction < 105
```

**2. Brittle Tests (Over-Mocking)**
```python
# Bad: Mocks everything, tests nothing
@patch('module.function_a')
@patch('module.function_b')
@patch('module.function_c')
def test_feature(mock_a, mock_b, mock_c):
    # If implementation changes, test breaks
    pass

# Good: Mock only external dependencies
@patch('requests.get')
def test_fetch(mock_get):
    # Real code tested, only HTTP mocked
    pass
```

**3. Slow Tests in Unit Suite**
```python
# Bad: Unit test that takes 10s
def test_slow_feature():
    time.sleep(10)  # Simulate slow operation
    assert True

# Good: Move to integration or use mocks
```

**4. Non-Deterministic Tests**
```python
# Bad: Random behavior
def test_random():
    assert random.choice([True, False])  # Flaky

# Good: Seed random generator
def test_random():
    random.seed(42)
    assert random.choice([True, False]) == True
```

---

## Future Enhancements (Phase 6-10)

### Phase 6: Alpha Research
- **Unit:** Test feature selection (50 tests)
- **Integration:** Test model training (10 tests)
- **E2E:** Test walk-forward validation (5 tests)

### Phase 7: Paper Trading
- **Unit:** Test order matching (20 tests)
- **Integration:** Test paper executor (10 tests)
- **E2E:** Test 30-day paper trading run (2 tests)

### Phase 8: Risk Management
- **Unit:** Test VaR computation (15 tests)
- **Integration:** Test circuit breakers (8 tests)
- **E2E:** Test risk limit enforcement (3 tests)

### Phase 10: Production
- **Unit:** Test HA failover logic (10 tests)
- **Integration:** Test disaster recovery (5 tests)
- **E2E:** Test production deployment (2 tests)

**Target (Phase 10): 200 tests (120 unit + 60 integration + 20 e2e)**

---

## Related Documentation

- [[TESTING_STRATEGY]] — Overall QA strategy
- [[QA_CHECKLIST]] — Pre-release checklist
- [[VERIFICATION_PROCEDURES]] — Manual verification
- [[COVERAGE_STRATEGY]] — Detailed coverage targets
- [[INTEGRATION_TESTING]] — Integration test deep-dive

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** After each phase

**How to Contribute:**
1. Write tests following pyramid (60/30/10 split)
2. Use AAA pattern, parametrize, fixtures
3. Aim for >85% coverage
4. Run tests before commit (`pytest tests/unit/`)
5. Update this doc if adding new test categories
