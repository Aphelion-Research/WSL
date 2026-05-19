---
doc_type: strategy
system: Dominion
ragd_priority: 6
audience:
  - developer
  - maintainer
status: active
last_reviewed: 2026-05-19
tags:
  - testing
  - coverage
  - quality
---

# Coverage Strategy

**Purpose:** Line and branch coverage targets for Dominion V2.

**Current:** 85% line coverage (Phase 5). Target: 90% (Phase 10).

---

## Coverage Targets by Module

| Module | Line % | Branch % | Priority | Rationale |
|---|---|---|---|---|
| data_pipeline/ | >90% | >85% | P1 | Critical path |
| microstructure/ | >85% | >80% | P1 | Alpha generation |
| features/ | >85% | >80% | P2 | Core logic |
| kalman/ | >90% | >85% | P2 | Complex math |
| regime/ | >80% | >75% | P3 | Stateful |
| agent/ | >70% | >60% | P4 | Agent-facing |
| scripts/ | >60% | >50% | P4 | Utilities |
| **Overall** | **>85%** | **>80%** | - | - |

---

## Current Coverage (Phase 5)

**By Module:**
```
data_pipeline/          92% (184/200 lines)
├─ ingestion.py         95%
├─ fusion.py            90%
├─ trust.py             88%
└─ cli.py               85%

microstructure/         88% (352/400 lines)
├─ lob.py               92%
├─ exec_sim.py          90%
├─ tca.py               85%
├─ toxicity.py          87%
└─ exec_features.py     84%

features/               85% (425/500 lines)
├─ price.py             90%
├─ volatility.py        88%
├─ volume.py            82%
└─ microstructure.py    80%

kalman/                 90% (180/200 lines)
├─ filter.py            92%
├─ bank.py              88%
└─ fusion.py            90%

regime/                 80% (160/200 lines)
├─ hmm.py               85%
├─ calendar.py          78%
└─ reports.py           75%

agent/                  65% (130/200 lines)
├─ session.py           70%
├─ handoff.py           68%
└─ safety.py            60%

scripts/                60% (180/300 lines)
├─ build_ragd.py        65%
├─ vault_sync.py        70%
└─ health_check.py      50%

**Total: 85% (1611/1900 lines)**
```

---

## Coverage Gaps (High Priority)

### 1. Error Handling Branches

**Problem:** Error paths untested (hard to trigger).

**Example (data_pipeline/ingestion.py):**
```python
# Uncovered: line 142-145 (exception handler)
try:
    data = fetch_yahoo(symbol)
except RequestException as e:
    logger.error(f"Fetch failed: {e}")  # Line 142 (not covered)
    retry_count += 1                     # Line 143 (not covered)
    if retry_count > 3:                  # Line 144 (not covered)
        raise                             # Line 145 (not covered)
```

**Solution:**
```python
@patch('yfinance.download')
def test_fetch_retry_logic(mock_download):
    # Force exception
    mock_download.side_effect = RequestException("Network error")
    
    # Verify retry + eventual raise
    with pytest.raises(RequestException):
        ingest_yahoo("GC=F")
```

**Affected Modules:**
- data_pipeline/ (8% uncovered = error handling)
- microstructure/ (12% uncovered = error paths)
- features/ (15% uncovered = edge cases + errors)

---

### 2. Edge Cases

**Problem:** Extreme inputs not tested.

**Example (features/volatility.py):**
```python
def compute_volatility(prices):
    if len(prices) < 2:
        return 0.0  # Uncovered: edge case
    returns = np.diff(prices) / prices[:-1]
    return np.std(returns)
```

**Solution:**
```python
@pytest.mark.parametrize("prices,expected", [
    ([100], 0.0),              # Edge: single price
    ([100, 100], 0.0),          # Edge: no volatility
    ([100, 102, 98], 0.0283),   # Normal case
])
def test_volatility_edge_cases(prices, expected):
    vol = compute_volatility(prices)
    assert abs(vol - expected) < 1e-3
```

**Affected Modules:**
- features/ (edge cases: empty data, NaN, Inf)
- kalman/ (edge cases: singular covariance, divergence)
- regime/ (edge cases: single-state data)

---

### 3. Concurrent Access

**Problem:** Thread safety not tested.

**Example (data_pipeline/fusion.py):**
```python
# Not covered: concurrent writes to self.state
class KalmanFilter:
    def update(self, observation):
        self.state = ...  # Race condition if multi-threaded
```

**Solution:**
```python
def test_kalman_thread_safety():
    kf = KalmanFilter()
    threads = [
        threading.Thread(target=lambda: kf.update(100 + i))
        for i in range(10)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Verify no corruption (order may vary)
    assert kf.state is not None
```

**Affected Modules:**
- data_pipeline/ (concurrent ingestion)
- agent/ (concurrent sessions)

---

## Exclusions

**Explicitly exclude from coverage:**

**1. Defensive Asserts**
```python
# coverage: exclude
assert isinstance(prices, np.ndarray), "prices must be numpy array"
```

**2. Debug Code**
```python
if DEBUG:  # pragma: no cover
    print(f"Debug: {state}")
```

**3. Abstract Methods**
```python
class BaseStrategy:
    def execute(self):
        raise NotImplementedError  # pragma: no cover
```

**4. Main Blocks**
```python
if __name__ == "__main__":  # pragma: no cover
    main()
```

**5. External Integrations (Mocked)**
```python
def _call_mt5_api():  # pragma: no cover (always mocked in tests)
    return mt5.symbol_info("GC=F")
```

---

## Measurement

**Tool:** pytest-cov

**Commands:**
```bash
# Run tests with coverage
pytest --cov=src --cov-report=term-missing

# HTML report (detailed)
pytest --cov=src --cov-report=html
open htmlcov/index.html

# XML report (CI)
pytest --cov=src --cov-report=xml
```

**CI Integration (GitHub Actions):**
```yaml
- name: Run tests with coverage
  run: pytest --cov=src --cov-report=xml

- name: Upload to Codecov
  uses: codecov/codecov-action@v2
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

**Coverage Badge (README.md):**
```markdown
[![Coverage](https://codecov.io/gh/USER/dominion/branch/main/graph/badge.svg)](https://codecov.io/gh/USER/dominion)
```

---

## Coverage Gates

**Pre-Commit:**
- No gate (unit tests must pass, coverage informational)

**Pull Request:**
- Coverage must not decrease >2%
- New code must have >80% coverage

**Main Branch:**
- Overall coverage >85%
- Critical modules (data_pipeline, microstructure) >90%

**Release:**
- Overall coverage >90% (Phase 10 target)
- All P1 modules >95%

---

## Improving Coverage

**Priority Order:**

**Phase 1 (Quick Wins):**
1. Add edge case tests (empty inputs, NaN, Inf)
2. Test error handling (mock exceptions)
3. Parametrize existing tests (multiple cases)

**Phase 2 (Medium Effort):**
4. Integration tests (concurrent access)
5. Test state transitions (regime changes)
6. Test configuration variations

**Phase 3 (High Effort):**
7. Property-based testing (Hypothesis)
8. Mutation testing (validate test quality)
9. Fuzz testing (random inputs)

---

## Property-Based Testing (Hypothesis)

**Purpose:** Generate random inputs, verify properties hold.

**Example:**
```python
from hypothesis import given, strategies as st

@given(st.lists(st.floats(min_value=1, max_value=1000), min_size=2, max_size=100))
def test_returns_properties(prices):
    returns = compute_returns(prices)
    
    # Property 1: Length correct
    assert len(returns) == len(prices) - 1
    
    # Property 2: No NaN/Inf
    assert not np.any(np.isnan(returns))
    assert not np.any(np.isinf(returns))
    
    # Property 3: Bounded (±100% per bar max)
    assert np.all(np.abs(returns) <= 1.0)
```

**Benefits:**
- Finds edge cases automatically
- Tests properties, not specific values
- Higher confidence than example-based tests

**Planned (Phase 6):**
- Hypothesis tests for features/ (20 tests)
- Hypothesis tests for kalman/ (10 tests)
- Hypothesis tests for microstructure/ (15 tests)

---

## Mutation Testing (mutmut)

**Purpose:** Mutate code, verify tests catch mutations.

**Example:**
```bash
# Install mutmut
pip install mutmut

# Run mutation testing
mutmut run --paths-to-mutate=src/features/

# View survivors (mutations tests didn't catch)
mutmut show
```

**Mutation Types:**
- Replace `+` with `-`
- Replace `<` with `<=`
- Replace constants (100 → 101)
- Remove statements

**Goal:** 100% mutation score (all mutants killed by tests).

**Current:** Not measured (Phase 5). Planned: Phase 8.

---

## Coverage Metrics

**Line Coverage:**
- % of executable lines run by tests
- Easy to measure
- Doesn't guarantee quality (can run line without asserting)

**Branch Coverage:**
- % of decision branches taken (if/else, try/except)
- Harder to achieve (need both branches)
- Better quality signal

**Path Coverage:**
- % of execution paths tested
- Exponential in number of branches (infeasible)
- Not tracked

**Mutation Score:**
- % of mutations killed by tests
- Best quality signal
- Expensive to compute

**Priority:**
1. Line coverage (primary metric)
2. Branch coverage (secondary)
3. Mutation score (Phase 8+)

---

## Anti-Patterns

**1. Coverage Theater**
```python
# Bad: Runs code but asserts nothing
def test_feature():
    compute_returns([100, 102, 101])
    # No assertion!
```

**2. Testing Implementation**
```python
# Bad: Tests internal state
def test_kalman():
    kf = KalmanFilter()
    kf.update(100)
    assert kf._state == 100  # Internal detail
```

**3. Gaming the Metric**
```python
# Bad: Dead code to boost coverage
if False:  # pragma: no cover
    unused_function()
```

---

## Coverage vs Quality

**Coverage ≠ Quality:**
- 100% coverage doesn't mean bug-free
- Tests must assert correct behavior
- Edge cases, error handling matter more than raw %

**Balance:**
- Aim for >85% line coverage (diminishing returns beyond)
- Focus on high-value paths (data pipeline, risk checks)
- Don't obsess over 100% (maintenance burden)

**When to Skip Coverage:**
- Debugging code (if DEBUG: ...)
- Abstract base classes
- External integrations (mocked in tests)
- UI code (hard to test, low risk)

---

## Roadmap

**Phase 5 (Current):**
- 85% line coverage
- Coverage CI gate (no decrease >2%)

**Phase 6 (Alpha Research):**
- Add Hypothesis tests (50 tests)
- 87% line coverage

**Phase 7 (Paper Trading):**
- Test paper executor (integration)
- 88% line coverage

**Phase 8 (Risk Management):**
- Mutation testing (mutmut)
- 90% line coverage

**Phase 10 (Production):**
- 95% coverage (P1 modules)
- 90% overall
- Mutation score >95%

---

## Related Documentation

- [[TEST_PYRAMID]] — Test strategy (60/30/10 split)
- [[INTEGRATION_TESTING]] — Integration test guide
- [[TESTING_STRATEGY]] — Overall QA strategy
- [[QA_CHECKLIST]] — Pre-release checklist

---

## Maintenance Notes

**Last Updated:** 2026-05-19 (Phase 5)

**Update Frequency:** Quarterly (or after major coverage improvements)

**How to Improve:**
1. Run `pytest --cov=src --cov-report=html`
2. Open `htmlcov/index.html`
3. Find red/yellow lines (uncovered/partially covered)
4. Add tests for high-value gaps (error handling, edge cases)
5. Re-run, verify coverage increase
6. Update this doc with new numbers
