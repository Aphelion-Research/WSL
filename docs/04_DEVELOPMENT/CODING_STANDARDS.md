---
doc_type: development
system: Dominion
ragd_priority: 9
audience:
  - ai_agent
  - maintainer
status: current
last_reviewed: 2026-05-19
tags:
  - coding
  - standards
  - style
---

# Coding Standards

**Mandatory for all code changes.**

---

## Python Style

**Base:** PEP 8

**Formatting:**
- Line length: 100 chars (not 79)
- Indentation: 4 spaces (never tabs)
- Blank lines: 2 between top-level, 1 between methods
- Imports: stdlib → third-party → local, sorted alphabetically

**Naming:**
```python
# Functions, variables, modules
def calculate_price():
    market_data = fetch_data()
    
# Classes
class DataPipeline:
    pass
    
# Constants
MAX_RETRIES = 3
DEFAULT_TIMEOUT = 30

# Private members
class Agent:
    def __init__(self):
        self._session_id = None
```

**Type Hints:**
```python
# Required for public functions
def query_ragd(text: str, top_k: int = 5) -> list[dict]:
    pass

# Optional for private functions, but encouraged
def _process_chunk(chunk: str) -> str:
    pass
```

**Docstrings:**
```python
def complex_function(arg1: str, arg2: int) -> dict:
    """Short description on one line.
    
    Longer description if needed. Explain non-obvious behavior.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Dictionary with keys: "result", "status"
        
    Raises:
        ValueError: If arg2 < 0
    """
    pass
```

**Imports:**
```python
# Standard library
import os
import sys
from pathlib import Path

# Third-party
import pytest
import pandas as pd

# Local
from dominion_loader import scan
from ragd.client import query
```

---

## C++ Style

**Base:** C++17 standard

**Formatting:**
- Line length: 100 chars
- Indentation: 2 spaces
- Braces: K&R style (opening brace on same line)
- Naming: snake_case for functions/variables, PascalCase for classes

**Example:**
```cpp
// File: ragd/src/native/query.cpp

#include "dominion_native/query.h"

namespace dominion {

QueryResult query_index(const std::string& text, int top_k) {
  // Implementation
  QueryResult result;
  result.status = "ok";
  return result;
}

class QueryEngine {
 public:
  QueryEngine() = default;
  
  QueryResult execute(const std::string& query) {
    // Implementation
    return {};
  }
  
 private:
  std::string db_path_;
};

}  // namespace dominion
```

**Headers:**
```cpp
// query.h
#pragma once

#include <string>
#include <vector>

namespace dominion {

struct QueryResult {
  std::string status;
  std::vector<std::string> chunks;
};

QueryResult query_index(const std::string& text, int top_k = 5);

}  // namespace dominion
```

---

## Error Handling

**Python:**
```python
# Use exceptions, not error codes
def load_config(path: str) -> dict:
    if not Path(path).exists():
        raise FileNotFoundError(f"Config not found: {path}")
    
    try:
        with open(path) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")

# Fail closed, not open
def fetch_data(url: str) -> dict:
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        # Don't return empty dict silently
        raise RuntimeError(f"Failed to fetch {url}: {e}")
```

**C++:**
```cpp
// Use exceptions or std::optional
std::optional<QueryResult> query_safe(const std::string& text) {
  try {
    return query_index(text, 5);
  } catch (const std::exception& e) {
    // Log error
    return std::nullopt;
  }
}
```

---

## Logging

**Python:**
```python
import logging

logger = logging.getLogger(__name__)

# Log levels
logger.debug("Detailed diagnostic")
logger.info("Normal operation")
logger.warning("Something unexpected but handled")
logger.error("Error occurred but recovering")
logger.critical("Fatal error")

# Include context
logger.error("Failed to process chunk", extra={
    "chunk_id": chunk_id,
    "error": str(e)
})
```

**Never:**
- `print()` for logging (use logger)
- Logging secrets (API keys, passwords)
- Logging full request/response bodies (may contain secrets)

---

## Testing

**File naming:**
```
module_name.py    → tests/test_module_name.py
feature.py        → tests/test_feature.py
```

**Test naming:**
```python
def test_feature_basic():
    """Test basic functionality."""
    pass

def test_feature_with_empty_input():
    """Test handling of empty input."""
    pass

def test_feature_raises_on_invalid():
    """Test error on invalid input."""
    pass
```

**Structure:**
```python
def test_kalman_filter_convergence():
    # Arrange
    filter = KalmanFilter(process_noise=0.1, observation_noise=0.5)
    measurements = [1.0, 1.1, 0.9, 1.0, 1.05]
    
    # Act
    results = [filter.update(m) for m in measurements]
    
    # Assert
    assert results[-1] == pytest.approx(1.0, abs=0.1)
```

**Mocking:**
```python
from unittest.mock import Mock, patch

def test_api_call(tmp_path):
    # Use tmp_path for file operations
    config_path = tmp_path / "config.json"
    config_path.write_text('{"key": "value"}')
    
    # Mock external APIs
    with patch('requests.get') as mock_get:
        mock_get.return_value.json.return_value = {"data": "test"}
        result = fetch_external_data()
        assert result == {"data": "test"}
```

---

## Code Complexity

**Keep functions small:**
- Target: <50 lines per function
- Max: 100 lines (with justification)

**Avoid deep nesting:**
```python
# Bad
def process(data):
    if data:
        if data.valid:
            if data.complete:
                if data.approved:
                    return compute(data)
    return None

# Good
def process(data):
    if not data or not data.valid or not data.complete or not data.approved:
        return None
    return compute(data)
```

**Extract helpers:**
```python
# Bad
def big_function(data):
    # 200 lines of logic
    pass

# Good
def big_function(data):
    validated = _validate_data(data)
    processed = _process_data(validated)
    return _format_result(processed)

def _validate_data(data):
    # 30 lines
    pass

def _process_data(data):
    # 50 lines
    pass

def _format_result(data):
    # 20 lines
    pass
```

---

## Security

**Never:**
```python
# Command injection
os.system(f"ls {user_input}")  # NO
subprocess.call(f"grep {pattern} {file}", shell=True)  # NO

# SQL injection
cursor.execute(f"SELECT * FROM users WHERE id={user_id}")  # NO

# Path traversal
open(f"data/{user_provided_path}")  # NO
```

**Instead:**
```python
# Safe command execution
subprocess.run(["ls", user_input], check=True)

# Parameterized queries
cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))

# Path validation
from pathlib import Path
safe_path = Path("data") / user_provided_path
if not safe_path.resolve().is_relative_to(Path("data").resolve()):
    raise ValueError("Invalid path")
```

**Secrets:**
```python
# Environment variables only
api_key = os.environ["API_KEY"]

# Never print
logger.info(f"API key: {api_key}")  # NO
logger.info("API key configured")  # YES
```

---

## Git Commits

**Format:**
```
type: short description (≤50 chars)

Longer explanation if needed (wrap at 72 chars). Explain WHY, not WHAT.

- Bullet points OK
- Reference issues: Fixes #123

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code restructure (no behavior change)
- `test`: Add/update tests
- `chore`: Maintenance (deps, config)

**Examples:**
```
feat: add Kalman fusion for multi-source data

Implements 6-timescale Kalman filter bank with dynamic trust scoring.
Handles Byzantine fault tolerance with 3+ source agreement.

- Added kalman.py with KalmanFilter class
- Added tests for convergence and trust updates
- Updated data pipeline to use fusion

Closes #45

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

## Comments

**Default: No comments.** Code should be self-documenting.

**When to comment:**

```python
# YES: Non-obvious WHY
# Brownian bridge respects OHLC constraints (can't violate high/low)
synthetic_ticks = generate_bridge(open, high, low, close, n_ticks)

# YES: Hidden constraint
# Rate limit: 25 req/day (Alpha Vantage free tier)
await asyncio.sleep(3600 / 25)

# YES: Workaround for bug
# TODO(matin): Remove after MT5 Wine bug #123 fixed
if platform.system() == "Linux":
    time.sleep(0.1)  # Prevent Wine race condition

# NO: Obvious WHAT
# Calculate the sum
total = a + b  # NO

# NO: Paraphrasing code
# Loop through items
for item in items:  # NO
```

---

## File Organization

**Python module:**
```
module_name/
├── __init__.py           # Public API exports
├── module_name.py        # Main implementation (or split below)
├── config.py             # Configuration
├── models.py             # Data models
├── utils.py              # Utilities
├── cli.py                # CLI entry point
└── tests/
    ├── __init__.py
    ├── test_module_name.py
    └── fixtures/
```

**Avoid:**
- `utils.py` with >500 lines (split by concern)
- Circular imports (redesign dependencies)
- Global state (pass dependencies explicitly)

---

## Performance

**Profile before optimizing:**
```python
# Use cProfile or line_profiler
python -m cProfile -o output.prof script.py
```

**Common optimizations:**
```python
# Use list comprehensions (faster than loops)
result = [x * 2 for x in data]

# Use generators for large data
def process_large_file(path):
    with open(path) as f:
        for line in f:
            yield process_line(line)

# Cache expensive operations
from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(x):
    return compute(x)
```

---

## Dependencies

**Adding new dependency:**
1. Check if already covered by existing deps
2. Verify license (MIT/BSD/Apache preferred)
3. Check maintenance status (recent commits)
4. Add to `requirements.txt` with version pin
5. Document why needed in commit message

**Prefer:**
- Standard library over third-party
- Well-maintained over cutting-edge
- Simple over feature-rich

---

## Code Review Checklist

Before claiming done:

- [ ] Follows naming conventions
- [ ] Type hints on public functions
- [ ] Docstrings on non-trivial functions
- [ ] Error handling (no bare except)
- [ ] No secrets in code
- [ ] No command/SQL injection risks
- [ ] Tests added for new code
- [ ] Tests pass: `python -m pytest -q`
- [ ] Trading check: `python domdata/check_no_trading.py`
- [ ] Commit message follows format
- [ ] Code is readable (someone else can understand)

---

## Enforcement

**Automated:**
- `pytest` for tests
- `domdata/check_no_trading.py` for trading safety
- `mypy` for type checking (if configured)
- `black` for formatting (if configured)

**Manual:**
- Code review by human or agent
- Adversary review (for agent-generated code)

**Violations:**
- P0: Security issues, trading code → fix immediately
- P1: Standard violations → fix before merge
- P2: Style issues → fix when touching file next

---

## Related Docs

- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- [TESTING_GUIDE.md](TESTING_GUIDE.md)
- [COMMIT_GUIDE.md](COMMIT_GUIDE.md)
- [ERROR_HANDLING_GUIDE.md](ERROR_HANDLING_GUIDE.md)

---

## Retrieval Hints

- "coding standards"
- "code style"
- "how to write code"
- "naming conventions"
- "python style guide"
- "commit format"
