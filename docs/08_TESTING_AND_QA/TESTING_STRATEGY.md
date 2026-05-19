---
doc_type: testing
system: Dominion
ragd_priority: 7
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - testing
  - strategy
  - qa
---

# Testing Strategy

## Testing Pyramid

```
      ╱╲
     ╱  ╲      E2E Tests (5%)
    ╱────╲     Integration Tests (15%)
   ╱──────╲    Unit Tests (80%)
  ╱────────╲
```

## Test Layers

### Unit Tests (80%)
- Test individual functions/classes
- Fast (<1ms per test)
- No external dependencies
- Mock when needed
- Target: >90% coverage

### Integration Tests (15%)
- Test module interactions
- Use real databases (SQLite, DuckDB)
- Slower (~100ms per test)
- Marked with `@pytest.mark.integration`
- Target: >80% coverage of integration paths

### E2E Tests (5%)
- Test full workflows
- Use real systems (RAGD, domdata)
- Slowest (>1s per test)
- Marked with `@pytest.mark.e2e`
- Target: Cover critical user journeys

## Test Categories

### 1. **Safety Tests**
- Trading execution blocked
- Secrets not leaked
- Forbidden tokens detected
- Destructive ops require confirmation

**Critical:** Must pass before ANY commit.

```bash
python domdata/check_no_trading.py  # MUST PASS
```

### 2. **Correctness Tests**
- Functions return correct results
- Data transformations accurate
- Edge cases handled
- Errors raised appropriately

**Critical:** All must pass before merge.

### 3. **Performance Tests**
- Operations complete within timeout
- Memory usage within bounds
- No performance regressions

**Important:** Monitor trends, fail on >2x regression.

### 4. **Integration Tests**
- Modules work together
- Data flows correctly
- APIs compatible

**Important:** Must pass for full system validation.

### 5. **Smoke Tests**
- System starts correctly
- Basic operations work
- No crashes on simple inputs

**Critical:** Must pass before deployment.

## Test Execution Strategy

### Development Time
```bash
# Fast feedback (unit tests only)
python -m pytest -q -m "not integration and not e2e"

# Full validation
python -m pytest -q
```

### Pre-Commit
```bash
# All tests must pass
python -m pytest -q
python domdata/check_no_trading.py
```

### CI/CD (if configured)
```bash
# Full test suite + coverage
python -m pytest --cov=. --cov-report=term-missing
ctest --test-dir ragd/build --output-on-failure
```

## Test Quality Bar

Good test:
- ✓ Tests one thing clearly
- ✓ Fast (<10ms for unit, <100ms for integration)
- ✓ Isolated (no dependencies on other tests)
- ✓ Repeatable (same input → same output)
- ✓ Descriptive name
- ✓ Clear assertions

Bad test:
- ✗ Tests multiple unrelated things
- ✗ Slow without justification
- ✗ Depends on test execution order
- ✗ Flaky (sometimes passes, sometimes fails)
- ✗ Generic name like `test_1`
- ✗ Vague assertions

## Coverage Targets

| Module | Target Coverage | Current | Status |
|---|---:|---:|---|
| domdata | >95% | High | ✓ |
| data_pipeline | >90% | High | ✓ |
| dominion_agent | >90% | High | ✓ |
| dominion_ai | >85% | High | ✓ |
| dominion_loader | >85% | High | ✓ |
| RAGD (C++) | >90% | High | ✓ |
| Microstructure | >80% | High | ✓ |
| Research OS | >70% | Medium | ⚠ |

## Test Maintenance

- Review flaky tests monthly
- Remove obsolete tests
- Update tests when behavior changes
- Add tests for reported bugs
- Refactor tests with code

## Test Documentation

Every test should be self-documenting:
- Clear name: `test_kalman_filter_converges_with_valid_input`
- Docstring explaining what is tested
- Clear assertions with context

## Anti-Patterns

**Avoid:**
- Testing implementation details (test behavior, not internals)
- Brittle tests (break on minor changes)
- Slow tests without justification
- Tests that depend on external services
- Tests with hardcoded timestamps/paths
- Commented-out tests
- Tests that "sometimes" fail

## Test Failures

**If tests fail:**
1. Don't skip or disable tests
2. Don't commit with failing tests
3. Fix the underlying issue
4. If test is wrong, fix the test (with justification)
5. Re-run tests to confirm

## Test Metrics

Current (2026-05-19):
- **Total tests:** 450 (426 Python + 24 C++)
- **Passing:** 450/450 (100%)
- **Coverage:** >80% for critical modules
- **Runtime:** ~12 seconds total
- **Flaky tests:** 0

## Future Enhancements

- Property-based testing (Hypothesis)
- Mutation testing
- Visual regression testing (for future UI)
- Load testing
- Chaos engineering tests

## Related Docs

- [TESTING_GUIDE.md](../04_DEVELOPMENT/TESTING_GUIDE.md)
- [QA_CHECKLIST.md](QA_CHECKLIST.md)
- [REGRESSION_PLAN.md](REGRESSION_PLAN.md)
- [QUALITY_SCORE_RUBRIC.md](QUALITY_SCORE_RUBRIC.md)

## Retrieval Hints

- "testing strategy"
- "test approach"
- "how to test the system"
- "test coverage"
- "test quality"
