---
doc_type: prompt
system: Dominion
ragd_priority: 6
audience:
  - ai_agent
status: current
last_reviewed: 2026-05-19
tags:
  - prompt
  - testing
  - qa
---

# CODEX Testing Prompt

**Use Case:** Add/fix tests  
**Complexity:** Medium  
**Duration:** 1-2 hours

---

## Context

Tests needed for [MODULE_NAME] module.

Reason: [New feature | Bug fix | Coverage gap | Flaky tests]

Repository: `/home/Martin/Dominion`

---

## Mission

Write comprehensive tests achieving 80%+ coverage.

---

## Workflow

### Step 1: Understand Module (15 min)

```bash
# Module structure
ls [module]/

# Public API
grep -n "^def\|^class" [module]/__init__.py
grep -n "^def\|^class" [module]/*.py

# Existing tests
ls tests/[module]/
python -m pytest tests/[module]/ -v
```

Read:
- Module implementation
- Existing tests (patterns)
- [[CODING_STANDARDS]] (testing section)

### Step 2: Identify Test Cases (10 min)

For each public function/class:
- **Happy path:** Valid inputs → expected outputs
- **Error cases:** Invalid inputs → exceptions/errors
- **Edge cases:** Boundary values, empty inputs, None
- **Integration:** How function interacts with dependencies

### Step 3: Write Unit Tests (30-60 min)

**Test structure:**
```python
import pytest
from [module].[file] import [Function]

class Test[Function]:
    def test_happy_path(self):
        """Test normal operation."""
        result = [Function](valid_input)
        assert result.status == "ok"
        assert result.value == expected_value
    
    def test_invalid_input(self):
        """Test error handling."""
        with pytest.raises(ValueError, match="expected error message"):
            [Function](invalid_input)
    
    def test_edge_case_empty(self):
        """Test empty input."""
        result = [Function]([])
        assert result.value is None
    
    def test_edge_case_boundary(self):
        """Test boundary values."""
        result = [Function](sys.maxsize)
        assert result.handled_correctly
```

**Use fixtures for common setup:**
```python
@pytest.fixture
def sample_data():
    """Provide test data."""
    return {"key": "value"}

def test_with_fixture(sample_data):
    result = process(sample_data)
    assert result.ok
```

### Step 4: Write Integration Tests (20-30 min)

If module has external dependencies:

```python
def test_integration_with_duckdb(tmp_path):
    """Test DuckDB integration."""
    db_path = tmp_path / "test.duckdb"
    conn = duckdb.connect(str(db_path))
    
    # Setup
    conn.execute("CREATE TABLE test (id INT)")
    
    # Test module with real DB
    result = module_function(conn)
    
    # Verify
    assert result.rows > 0
    
    # Cleanup
    conn.close()
```

**Mock external APIs:**
```python
from unittest.mock import Mock, patch

@patch('[module].requests.get')
def test_api_call(mock_get):
    """Test external API call."""
    mock_get.return_value.json.return_value = {"data": "value"}
    
    result = fetch_data()
    
    assert result["data"] == "value"
    mock_get.assert_called_once()
```

### Step 5: Run Tests (5 min)

```bash
# Run module tests
python -m pytest tests/[module]/ -v

# Check coverage
python -m pytest tests/[module]/ --cov=[module] --cov-report=term-missing

# Run all tests
python -m pytest -q
```

Target: 80%+ coverage for new code.

### Step 6: Fix Flaky Tests (if needed) (15 min)

**Common flaky patterns:**
- Time-dependent (use freezegun)
- Race conditions (add synchronization)
- Non-deterministic order (sort results)
- External dependencies (mock or use fixtures)

### Step 7: Update Test Docs (5 min)

Update `docs/08_TESTING_AND_QA/TESTING_STRATEGY.md` if:
- New test patterns introduced
- New fixtures added
- Integration test setup changed

---

## Validation

Tests complete when:
- [ ] All new tests pass
- [ ] Coverage ≥80% for new code
- [ ] No flaky tests (run 10 times: `pytest --count=10`)
- [ ] All existing tests still pass
- [ ] Test names descriptive
- [ ] Docstrings explain what's tested

---

## Output

1. **Tests:** New test files in `tests/[module]/`
2. **Coverage:** Report showing ≥80%
3. **Summary:** Test count, coverage %, any gaps

---

## Common Pitfalls

**Don't:**
- Test implementation details (test behavior, not internals)
- Write brittle tests (avoid hardcoded paths, timestamps)
- Skip edge cases (empty, None, boundary values)
- Leave print statements (use logging or remove)
- Mock everything (integration tests need real dependencies)

**Do:**
- Test public API only (not private functions)
- Use descriptive test names (`test_returns_none_when_input_empty`)
- Arrange-Act-Assert pattern (setup, execute, verify)
- One assertion per test (easier to debug)
- Clean up resources (use fixtures, context managers)

---

## Test Categories

**Unit tests** (fast, isolated):
- Single function/class
- Mocked dependencies
- <10ms per test

**Integration tests** (medium speed):
- Multiple components
- Real dependencies (DB, filesystem)
- <1s per test

**End-to-end tests** (slow):
- Full workflow
- Real system state
- <10s per test

---

## Related Prompts

- [[CODEX_FEATURE_IMPLEMENTATION_PROMPT]] — Includes testing phase
- [[CODEX_BUGFIX_PROMPT]] — Add regression test

---

## Retrieval Hints

- "write tests"
- "testing strategy"
- "test coverage"
- "pytest guide"
