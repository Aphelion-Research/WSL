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
  - qa
---

# Testing Guide

## Test Philosophy

- Tests are first-class code
- Write tests before implementation (TDD)
- Tests must be fast, reliable, isolated
- Tests document expected behavior
- All tests must pass before merge

## Test Structure

```
<module>/
├── __init__.py
├── <module>.py
└── tests/
    ├── __init__.py
    ├── test_<feature_1>.py
    ├── test_<feature_2>.py
    └── fixtures/
```

## Running Tests

```bash
# All tests
python -m pytest -q

# Specific module
python -m pytest -q data_pipeline/tests/

# Specific test file
python -m pytest -q data_pipeline/tests/test_fusion.py

# Specific test
python -m pytest -q data_pipeline/tests/test_fusion.py::test_kalman_convergence

# With output
python -m pytest -v

# C++ tests
ctest --test-dir ragd/build --output-on-failure
```

## Test Types

### Unit Tests
- Test single function/class
- No external dependencies (mock if needed)
- Fast (<1ms per test)

### Integration Tests
- Test multiple components together
- May use real databases/files
- Slower (marked with `@pytest.mark.integration`)

### End-to-End Tests
- Test full workflows
- Use real systems
- Slowest (marked with `@pytest.mark.e2e`)

## Test Organization

```python
import pytest

def test_feature_basic():
    """Test basic functionality."""
    result = my_function(simple_input)
    assert result == expected

def test_feature_edge_case():
    """Test edge case handling."""
    result = my_function(edge_case_input)
    assert result == expected

def test_feature_error():
    """Test error handling."""
    with pytest.raises(ValueError):
        my_function(invalid_input)
```

## Fixtures

```python
@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    assert sample_data["key"] == "value"
```

## Mocking

```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_api = Mock()
    mock_api.fetch.return_value = {"data": "test"}
    result = process_api(mock_api)
    assert result == "test"
```

## Test Coverage

Target: >80% coverage for critical modules.

```bash
# Run with coverage
python -m pytest --cov=data_pipeline --cov-report=term-missing
```

## Test Naming

- `test_<feature>_<scenario>`
- Be specific: `test_kalman_filter_convergence` not `test_filter`
- Use underscores, not camelCase

## Assertions

- Use specific assertions: `assert x == 5` not `assert x`
- Add messages: `assert x == 5, f"Expected 5, got {x}"`
- Use pytest helpers: `pytest.approx()` for floats

## Test Data

- Store in `tests/fixtures/`
- Keep small (<1 KB)
- Use synthetic data, not real secrets
- Commit test data to git

## Testing Guidelines

**Do:**
- Write tests first (TDD)
- Test one thing per test
- Use descriptive names
- Clean up after tests (temp files, connections)
- Run tests frequently

**Don't:**
- Skip failing tests
- Disable tests without justification
- Test implementation details
- Make tests depend on each other
- Commit commented-out tests

## CI/CD

Tests run:
- Before every commit (pre-commit hook)
- On every push (GitHub Actions, if configured)
- Before claiming task complete

## Test Metrics

Current (2026-05-19):
- Python tests: 426/426 passing
- C++ tests: 24/24 passing
- Coverage: >80% for critical modules
- Runtime: ~10 seconds for Python, ~2 seconds for C++

## Related Docs

- [TESTING_STRATEGY.md](../08_TESTING_AND_QA/TESTING_STRATEGY.md)
- [QA_CHECKLIST.md](../08_TESTING_AND_QA/QA_CHECKLIST.md)
- [REGRESSION_PLAN.md](../08_TESTING_AND_QA/REGRESSION_PLAN.md)

## Retrieval Hints

- "testing"
- "how to test"
- "write tests"
- "test guide"
